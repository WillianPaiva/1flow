# -*- coding: utf-8 -*-
"""


    .. note:: as of Celery 3.0.20, there are many unsolved problems related
        to tasks-as-methods. Just to name a few:
        - https://github.com/celery/celery/issues/1458
        - https://github.com/celery/celery/issues/1459
        - https://github.com/celery/celery/issues/1478

        As I have no time to dive into celery celery and fix them myself,
        I just turned tasks-as-methods into standard tasks calling the "old"
        method inside the task.

        This has the side-effect-benefit of avoiding any `.reload()` call
        inside the tasks methods themselves, but forces us to write extraneous
        functions only for the tasks, which is duplicate work for me.

        But in the meantime, this allows tests to work correctly, which is
        a much bigger benefit.

    .. warning:: **convention** says tasks that call `Class.method()` must
        be named `class_method()` (``class`` as lowercase). Lookups rely on
        this.

        And special post-create tasks must be
        named ``def class_post_create_task()``, not
        just ``class_article_post_create``. This is because these special
        methods are not meant to be called in the app normal life, only at a
        special moment (after database record creation, exactly).
        BUT, I prefer the ``name=`` of the celery task to stay without
        the ``_task`` for shortyness and readability in celery flower.
"""

import os
import re
import gc
import ast
import sys
import uuid
import errno
import difflib
import logging
import requests
import strainer
import html2text
import feedparser

from statsd import statsd
from random import randint, randrange
from constance import config
from markdown_deux import markdown

from bs4 import BeautifulSoup
#from xml.sax import SAXParseException

from celery import task, chain as tasks_chain

from celery.exceptions import SoftTimeLimitExceeded

from pymongo.errors import DuplicateKeyError

from mongoengine import (Document, EmbeddedDocument, Q,
                         ValidationError, NULLIFY, PULL, CASCADE)
from mongoengine.errors import NotUniqueError
from mongoengine.fields import (IntField, FloatField, BooleanField,
                                DateTimeField,
                                ListField, StringField,
                                URLField,
                                ReferenceField, GenericReferenceField,
                                EmbeddedDocumentField)

from django.http import Http404
from django.conf import settings
from django.utils.translation import ugettext_lazy as _, pgettext_lazy as _p
from django.utils.text import slugify
from django.contrib.auth import get_user_model

from ...base.utils import (connect_mongoengine_signals,
                           detect_encoding_from_requests_response,
                           RedisExpiringLock,  # AlreadyLockedException,
                           RedisSemaphore,  # NoResourceAvailableException,
                           HttpResponseLogProcessor, StopProcessingException)

from ...base.utils.http import clean_url
from ...base.utils.dateutils import (now, timedelta, today,
                                     datetime, time, combine)
from ...base.fields import IntRedisDescriptor, DatetimeRedisDescriptor

from .keyval import FeedbackDocument

# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••• constants and setup

LOGGER     = logging.getLogger(__name__)
DjangoUser = get_user_model()

BASE_1FLOW_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:21.0) Gecko/20100101 Firefox/21.0' # NOQA
feedparser.USER_AGENT = BASE_1FLOW_USER_AGENT
REQUEST_BASE_HEADERS  = {'User-agent': BASE_1FLOW_USER_AGENT}

# Lower the default, we know good websites just work well.
requests.adapters.DEFAULT_RETRIES = 1

# Don't use any lang-dependant values (eg. _(u'NO CONTENT'))
CONTENT_NOT_PARSED       = None
CONTENT_TYPE_NONE        = 0
CONTENT_TYPE_HTML        = 1
# Since Hotfix 0.20.11.5, we process markdown differently,
# And need to know about the "old" processing method to be
# able to fix it afterwards in the production database.
CONTENT_TYPE_MARKDOWN_V1 = 2
CONTENT_TYPE_MARKDOWN    = 3
CONTENT_TYPE_IMAGE       = 100
CONTENT_TYPE_VIDEO       = 200
CONTENT_TYPES_FINAL      = (CONTENT_TYPE_MARKDOWN,
                            CONTENT_TYPE_MARKDOWN_V1,
                            CONTENT_TYPE_IMAGE,
                            CONTENT_TYPE_VIDEO,
                            )

CONTENT_PREPARSING_NEEDS_GHOST = 1
CONTENT_FETCH_LIKELY_MULTIPAGE = 2

# MORE CONTENT_PREPARSING_NEEDS_* TO COME

ORIGIN_TYPE_NONE          = 0
ORIGIN_TYPE_GOOGLE_READER = 1
ORIGIN_TYPE_FEEDPARSER    = 2
ORIGIN_TYPE_STANDALONE    = 3
ORIGIN_TYPE_TWITTER       = 4

ARTICLE_ORPHANED_BASE = u'http://{0}/orphaned/article/'.format(
                        settings.SITE_DOMAIN)

if config.FEED_FETCH_GHOST_ENABLED:
    try:
        import ghost
    except:
        ghost = None # NOQA
    else:
        GHOST_BROWSER = ghost.Ghost()


else:
    ghost = None # NOQA


# ••••••••••••• issue https://code.google.com/p/feedparser/issues/detail?id=404

import dateutil


def dateutilDateHandler(aDateString):
    return dateutil.parser.parse(aDateString).utctimetuple()

feedparser.registerDateHandler(dateutilDateHandler)

# ••••••••• end issue •••••••••••••••••••••••••••••••••••••••••••••••••••••••••


# Until we patch Ghost to use more than one Xvfb at the same time,
# we are tied to ensure there is only one running at a time.
global_ghost_lock = RedisExpiringLock('__ghost.py__')


class NotTextHtmlException(Exception):
    """ Raised when the content of an article is not text/html, to switch to
        other parsers, without re-requesting the actual content. """
    def __init__(self, message, response):
        # Call the base class constructor with the parameters it needs
        Exception.__init__(self, message)
        self.response = response


class DocumentHelperMixin(object):
    """ Because, as of MongoEngine 0.8.3,
        subclassing `Document` is not possible o_O

        […]
          File "/Users/olive/sources/1flow/oneflow/core/models/nonrel.py", line 141, in <module> # NOQA
            class Source(Document):
          File "/Users/olive/.virtualenvs/1flow/lib/python2.7/site-packages/mongoengine/base/metaclasses.py", line 332, in __new__ # NOQA
            new_class = super_new(cls, name, bases, attrs)
          File "/Users/olive/.virtualenvs/1flow/lib/python2.7/site-packages/mongoengine/base/metaclasses.py", line 120, in __new__ # NOQA
            base.__name__)
        ValueError: Document Document may not be subclassed

    """

    @property
    def _db_name(self):
        return self._get_db().name

    @classmethod
    def get_or_404(cls, oid):
        """ Rough equivalent of Django's get_object_or_404() shortcut.
            Not as powerful, though.

            .. versionadded:: 0.21.7
        """

        try:
            return cls.objects.get(id=oid)

        except cls.DoesNotExist:
            raise Http404(_(u'{0} #{1} not found').format(cls.__name__, oid))

        except:
            LOGGER.exception(u'Exception while getting %s #%s',
                             cls.__name__, oid)
            raise

    def register_duplicate(self, duplicate, force=False):

        # be sure this helper method is called
        # on a document that has the atribute.
        assert hasattr(duplicate, 'duplicate_of')

        _cls_name_ = self.__class__.__name__

        # TODO: get this from a class attribute?
        # I'm not sure for MongoEngine models.
        lower_plural = _cls_name_.lower() + u's'

        if duplicate.duplicate_of:
            if duplicate.duplicate_of != self:
                # NOTE: for Article, this situation can't happen IRL
                # (demonstrated with Willian 20130718).
                #
                # Any "second" duplicate *will* resolve to the master via the
                # redirect chain. It will *never* resolve to an intermediate
                # URL in the chain.
                #
                # For other objects it should happen too, because the
                # `get_or_create()` methods should return the `.duplicate_of`
                # attribute if it is not None.

                LOGGER.warning(u'%s %s is already a duplicate of '
                               u'another instance, not %s. Aborting.',
                               _cls_name_, duplicate, duplicate.duplicate_of)
                return

        LOGGER.info(u'Registering %s %s as duplicate of %s…',
                    _cls_name_, duplicate, self)

        # Register the duplication immediately, for other
        # background operations to use ourselves as value.
        duplicate.duplicate_of = self
        duplicate.save()

        statsd.gauge('%s.counts.duplicates' % lower_plural, 1, delta=True)

        try:
            # Having tasks not as methods because of Celery bugs forces
            # us to do strange things. We have to "guess" and lookup the
            # task name in the current module. OK, not *that* big deal.
            globals()[self.__class__.__name__.lower()
                      + '_replace_duplicate_everywhere'].delay(self.id,
                                                               duplicate.id)

        except KeyError:
            LOGGER.warning(u'Object %s does not have a '
                           u'`replace_duplicate_everywhere()` task.', self)

    def offload_attribute(self, attribute_name, remove=False):
        """ NOTE: this method is not used as of 20130816, but I keep it because
            it contains the base for the idea of a global on-disk unique path
            for each document.

            The unique path can also eventually be used for statistics, to
            avoid unbrowsable too big folders in Graphite.
        """

        # TODO: factorize this sometwhere common to all classes.
        object_path = os.path.join(self.__class__.__name__,
                                   self.id[-1] + self.id[-2],
                                   self.id[-3] + self.id[-4],
                                   self.id[-5] + self.id[-6],
                                   self.id[-7] + self.id[-8],
                                   self.id)

        offload_directory = config.ARTICLE_OFFLOAD_DIRECTORY.format(
            object_path=object_path)

        if not os.path.exists(offload_directory):
            try:
                os.makedirs(offload_directory)

            except (OSError, IOError), e:
                if e.errno != errno.EEXIST:
                    raise

        with open(os.path.join(offload_directory, attribute_name), 'w') as f:
            f.write(getattr(self, attribute_name))

        if remove:
            delattr(self, attribute_name)

    def safe_reload(self):
        try:
            self.reload()

        except:
            pass


# •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• User preferences


class SnapPreferences(Document, DocumentHelperMixin):
    select_paragraph = BooleanField(verbose_name=_(u'Select whole paragraph '
                                    u'on click'), default=False)
    default_public = BooleanField(verbose_name=_(u'Grows public by default'),
                                  default=True)


class NotificationPreferences(EmbeddedDocument):
    """ Email and other web notifications preferences. """
    pass


AUTO_MARK_READ_DELAY_CHOICES = (
    (150, _(u'Immediately')),
    (1000, _(u'After one second')),
    (2000, _(u'After two seconds')),
    (4500, _(u'After 4.5 seconds (default)')),
    (10000, _(u'After 10 seconds')),
    (30000, _(u'After 30 seconds')),
    (-1, _(u'Never (do not auto mark as read)')),
)


class ReadPreferences(EmbeddedDocument):
    """ Reading list preferences. """

    starred_marks_read = BooleanField(
        verbose_name=_(u'Star marks read'),
        help_text=_(u'When you mark an article starred, this will '
                    u'automatically mark it as read (default: true).'),
        default=True)

    starred_removes_bookmarked = BooleanField(
        verbose_name=_(u'Star unmarks “read later”'),
        help_text=_(u'When you mark an article starred, this will '
                    u'automatically remove it from the “read later” '
                    u'list. (default: true).'), default=True)

    bookmarked_marks_unread = BooleanField(
        verbose_name=_(u'Reading later marks unread'),
        help_text=_(u'Marking an article to read later marks it as unread '
                    u'(default: true).'), default=True)

    auto_mark_read_delay = IntField(
        verbose_name=_(u'Auto mark-read delay'),
        help_text=_(u'The delay after which an open article in any reading '
                    u'list will be automatically marked as read if it is not.'),
                    default=4500, choices=AUTO_MARK_READ_DELAY_CHOICES)

    read_switches_to_fullscreen = BooleanField(
        verbose_name=_(u'Switch to full-screen while reading'),
        help_text=_(u'Automatically hide navigation bars when opening an '
                    u'article for reading (default: true).'), default=True)


class SelectorPreferences(EmbeddedDocument):
    """ Source selector preferences. """

    titles_show_unread_count = BooleanField(
        verbose_name=_(u'Feed names show unread count'),
        help_text=_(u'Activate this if you want to see the articles '
                    u'unread count in parenthesis near the feed titles.'),
        default=False)

    folders_show_unread_count = BooleanField(
        verbose_name=_(u'Folders show unread count'),
        help_text=_(u'Each folder is appended the sum of unread articles '
                    u'of each of its subfolders and subscriptions.'),
        default=False)

    show_closed_streams = BooleanField(
        verbose_name=_(u'Show closed streams'),
        help_text=_(u'Display streams that have been closed by the system '
                    u'but to which you are still subscribed. As there will '
                    u'never be new content in them, it is safe to hide them '
                    u'in the selector. Unread articles from closed streams '
                    u'still show in the unread list.'),
                    # TODO: use reverse_lazy('read') and make a link.
                    # 20131004: it just crashes because of a circular
                    # import loop in mongoadmin, to change.
        default=False)


HOME_STYLE_CHOICES = (
    (u'RL', _(u'Reading list')),
    (u'TL', _(u'Tiled News')),
    (u'T1', _(u'Tiled experiment #1')),
    (u'DB', _(u'Dashboard')),
)


class HomePreferences(EmbeddedDocument):
    """ Various HOME settings. """

    style_templates = {
        u'RL': 'snippets/read/read-list-item.html',
        u'TL': 'snippets/read/read-tiles-tile.html',
        u'T1': 'snippets/read/read-tiles-experimental-tile.html',
    }
    style = StringField(verbose_name=_(u'How the user wants his 1flow '
                        u'home to appear'), max_length=2,
                        choices=HOME_STYLE_CHOICES, default=u'RL')

    def get_template(self):
        return HomePreferences.style_templates.get(self.style)


class HelpWizards(EmbeddedDocument):
    """ Stores if the user viewed the wizards / assistants or not.
        Special attribute is :attr:`show_all` via which the user
        can avoid them to be showed complely or not.
    """
    show_all     = BooleanField(default=True)
    welcome_beta = BooleanField(default=False)


class Preferences(Document, DocumentHelperMixin):
    snap         = EmbeddedDocumentField(u'SnapPreferences',
                                         default=SnapPreferences)
    notification = EmbeddedDocumentField(u'NotificationPreferences',
                                         default=NotificationPreferences)
    home         = EmbeddedDocumentField(u'HomePreferences',
                                         default=HomePreferences)
    read         = EmbeddedDocumentField(u'ReadPreferences',
                                         default=ReadPreferences)
    selector     = EmbeddedDocumentField(u'SelectorPreferences',
                                         default=SelectorPreferences)
    wizards      = EmbeddedDocumentField(u'HelpWizards',
                                         default=HelpWizards)

    def __unicode__(self):
        return u'Preferences #%s' % self.id

# •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• User & Group


def user_django_user_random_default():
    """ 20130731: unused function but I keep this code for random()-related
        and future use. """

    count = 1

    while count:
        random_int = randint(-sys.maxint - 1, -1)

        try:
            User.objects.get(django_user=random_int)

        except User.DoesNotExist:
            return random_int

        else:
            count += 1
            if count == 10:
                LOGGER.warning(u'user_django_user_random_default() is starting '
                               u'to slow down things (more than 10 cycles to '
                               u' generate a not-taken random ID)…')


@task(name='User.post_create', queue='high')
def user_post_create_task(user_id, *args, **kwargs):

    user = User.objects.get(id=user_id)
    return user.post_create_task(*args, **kwargs)


def new_user_preferences():

    return Preferences().save()


def user_has_content(user, *args, **kwargs):

    return Read.objects(user=user).count()


class User(Document, DocumentHelperMixin):
    django_user = IntField(unique=True)
    username    = StringField()
    first_name  = StringField()
    last_name   = StringField()
    avatar_url  = URLField()
    preferences_data = ReferenceField('Preferences',
                                      reverse_delete_rule=NULLIFY)

    @property
    def preferences(self):
        if self.preferences_data is None:
            self.preferences_data = Preferences().save()
            self.save()

        return self.preferences_data

    def __unicode__(self):
        return u'%s #%s (Django ID: %s)' % (self.username or u'<UNKNOWN>',
                                            self.id, self.django_user)

    def get_full_name(self):
        return '%s %s' % (self.first_name, self.last_name)

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        user = document

        if created:
            if user._db_name != settings.MONGODB_NAME_ARCHIVE:
                user_post_create_task.delay(user.id)
                pass

    @classmethod
    def signal_pre_save_post_validation_handler(cls, sender,
                                                document, **kwargs):

        if document.preferences is None:
            document.preferences = Preferences().save()

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        django_user = DjangoUser.objects.get(id=self.django_user)
        self.username = django_user.username
        self.last_name = django_user.last_name
        self.first_name = django_user.first_name
        self.save()

    has_content = IntRedisDescriptor(
        attr_name='u.h_c', default=user_has_content, set_default=True)

    @property
    def subscriptions(self):
        return Subscription.objects(user=self)


def mongo_user(self):
    try:
        return self.__mongo_user_cache__

    except:
        try:
            self.__mongo_user_cache__ = User.objects.get(django_user=self.id)

        except User.DoesNotExist:
            try:
                self.__mongo_user_cache__ = User(django_user=self.id).save()

            except (NotUniqueError, DuplicateKeyError):
                # Woops. Race condition? On a user?? Weird.

                self.__mongo_user_cache__ = User.objects.get(
                                                django_user=self.id)

        return self.__mongo_user_cache__

# Auto-link the DjangoUser to the mongo one
DjangoUser.mongo = property(mongo_user)


class Group(Document, DocumentHelperMixin):
    name = StringField(unique_with='creator')
    creator = ReferenceField('User', reverse_delete_rule=CASCADE)
    administrators = ListField(ReferenceField('User',
                               reverse_delete_rule=PULL))
    members = ListField(ReferenceField('User',
                        reverse_delete_rule=PULL))
    guests = ListField(ReferenceField('User',
                       reverse_delete_rule=PULL))


# •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Websites

@task(name='WebSite.post_create', queue='high')
def website_post_create_task(website_id):

    website = WebSite.objects.get(id=website_id)
    website.post_create_task()


class WebSite(Document, DocumentHelperMixin):
    """ Simple representation of a web site. Holds options for it.


    .. todo::
        - replace Feed.site_url by Feed.website
        - set_fetch_limit goes into website (can be common to many feeds)
    """

    name = StringField()
    slug = StringField(verbose_name=_(u'slug'))
    url  = URLField(unique=True)
    duplicate_of = ReferenceField('WebSite',
                                  reverse_delete_rule=NULLIFY)

    def __unicode__(self):
        return u'%s #%s (%s)%s' % (self.name or u'<UNSET>', self.id, self.url,
                                   (_(u'(dupe of #%s)') % self.duplicate_of.id)
                                   if self.duplicate_of else u'')

    @staticmethod
    def split_url(url, split_port=False):

        proto, remaining = url.split('://', 1)

        try:
            host_and_port, remaining = remaining.split('/', 1)

        except ValueError:
            host_and_port = remaining
            remaining     = u''

        if split_port:
            try:
                hostname, port = host_and_port.split(':')

            except ValueError:
                hostname = host_and_port
                port = '80' if proto == 'http' else '443'

            return proto, hostname, int(port), remaining

        return proto, host_and_port, remaining

    @classmethod
    def get_from_url(cls, url):
        """ Will get you the ``WebSite`` object from an :param:`url`, after
            having striped down the path part
            (eg. ``http://test.com/my-article`` gives you the web
             site ``http://test.com``, without the trailing slash).

            .. note:: unlike :meth:`get_or_create_website`, this method will
                harmonize urls: ``WebSite.get_from_url('http://toto.com')``
                and  ``WebSite.get_from_url('http://toto.com/')`` will give
                you back the same result. This is intended, to avoid
                duplication.

        """
        try:
            proto, host_and_port, remaining = WebSite.split_url(url)

        except:
            LOGGER.exception('Unable to determine Website from "%s"', url)
            return None

        else:
            base_url = '%s://%s' % (proto, host_and_port)

            try:
                website, _ = WebSite.get_or_create_website(base_url)

            except ValidationError:
                LOGGER.exception('Cannot create website from url %s (via '
                                 u'original %s)', base_url, url)
                return None

            return website

    @classmethod
    def get_or_create_website(cls, url):
        """

            .. warning:: will always return the *master* :class:`WebSite`
                if the found one is a duplicate (eg. never returns the
                duplicate one).
        """

        try:
            website = cls.objects.get(url=url)

        except cls.DoesNotExist:
            try:
                return cls(url=url).save(), True

            except (NotUniqueError, DuplicateKeyError):
                # We just hit the race condition with two creations
                # At the same time. Same player shoots again.
                website = cls.objects.get(url=url)

        return website.duplicate_of or website, False

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        website = document

        if created:
            if not website.duplicate_of:
                # We don't run the post_create() task in the archive
                # database: the article is already complete.
                if website._db_name != settings.MONGODB_NAME_ARCHIVE:
                    website_post_create_task.delay(website.id)

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        if not self.slug:
            if self.name is None:
                proto, host_and_port, remaining = WebSite.split_url(self.url)
                self.name = host_and_port.replace(u'_', u' ').title()

            self.slug = slugify(self.name)

            self.save()

            statsd.gauge('websites.counts.total', 1, delta=True)


# •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Word relations


@task(name='Tag.post_create', queue='high')
def tag_post_create_task(tag_id, *args, **kwargs):

    tag = Tag.objects.get(id=tag_id)
    return tag.post_create_task(*args, **kwargs)


@task(name='Tag.replace_duplicate_everywhere', queue='low')
def tag_replace_duplicate_everywhere(tag_id, dupe_id, *args, **kwargs):

    tag  = Tag.objects.get(id=tag_id)
    dupe = Tag.objects.get(id=dupe_id)
    return tag.replace_duplicate_everywhere(dupe, *args, **kwargs)


class Tag(Document, DocumentHelperMixin):
    name     = StringField(verbose_name=_(u'name'), unique=True)
    slug     = StringField(verbose_name=_(u'slug'))
    language = StringField(verbose_name=_(u'language'), default='')
    parents  = ListField(ReferenceField('self',
                         reverse_delete_rule=PULL), default=list)
    children = ListField(ReferenceField('self',
                         reverse_delete_rule=PULL), default=list)
    # reverse_delete_rule=NULLIFY,
    origin   = GenericReferenceField(verbose_name=_(u'Origin'),
                                     help_text=_(u'Initial origin from where '
                                                 u'the tag was created from, '
                                                 u'to eventually help '
                                                 u'defining other attributes.'))
    duplicate_of = ReferenceField('Tag', reverse_delete_rule=NULLIFY,
                                  verbose_name=_(u'Duplicate of'),
                                  help_text=_(u'Put a "master" tag here to '
                                              u'help avoiding too much '
                                              u'different tags (eg. singular '
                                              u'and plurals) with the same '
                                              u'meaning and loss of '
                                              u'information.'))

    meta = {
        'indexes': ['name', ]
    }

    # See the `WordRelation` class before working on this.
    #
    # antonyms = ListField(ReferenceField('self'), verbose_name=_(u'Antonyms'),
    #                      help_text=_(u'Define an antonym tag to '
    #                      u'help search connectable but.'))

    def __unicode__(self):
        return _(u'{0} {1}⚐ (#{2})').format(self.name, self.language, self.id)

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        tag = document

        if created:
            if tag._db_name != settings.MONGODB_NAME_ARCHIVE:
                tag_post_create_task.delay(tag.id)

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        if not self.slug:
            self.slug = slugify(self.name)
            self.save()

            statsd.gauge('tags.counts.total', 1, delta=True)

    @classmethod
    def get_tags_set(cls, tags_names, origin=None):

        tags = set()

        for tag_name in tags_names:
            tag_name = tag_name.lower()

            try:
                tag = cls.objects.get(name=tag_name)

            except cls.DoesNotExist:
                try:
                    tag = cls(name=tag_name, origin=origin).save()

                except (NotUniqueError, DuplicateKeyError):
                    tag = cls.objects.get(name=tag_name)

            tags.add(tag.duplicate_of or tag)

        return tags

    def replace_duplicate_everywhere(self, duplicate, force=False):

        #
        # TODO: update search engine indexes…
        #

        for article in Article.objects(tags=duplicate).no_cache():
            for read in article.reads:
                if duplicate in read.tags:
                    read.update(pull__tags=duplicate)
                    read.update(add_to_set__tags=self)

            article.update(pull__tags=duplicate)
            article.update(add_to_set__tags=self)

        #
        # TODO: do the same for feeds, reads (, subscriptions?) …
        #

    def save(self, *args, **kwargs):
        """ This method will simply add the missing children/parents reverse
            links of the current Tag. This is needed when modifying tags from
            the Django admin, which doesn't know about the reverse-link
            existence.

            .. note:: sadly, we have no fast way to do the same for links
                removal.
        """

        super(Tag, self).save(*args, **kwargs)

        for parent in self.parents:
            if self in parent.children:
                continue

            try:
                parent.add_child(self, update_reverse_link=False,
                                 full_reload=False)
            except:
                LOGGER.exception(u'Exception while reverse-adding '
                                 u'child %s to parent %s', self, parent)

        for child in self.children:
            if self in child.parents:
                continue

            try:
                child.add_parent(self, update_reverse_link=False,
                                 full_reload=False)
            except:
                LOGGER.exception(u'Exception while reverse-adding '
                                 u'parent %s to child %s', self, child)

        return self

    def add_parent(self, parent, update_reverse_link=True, full_reload=True):

        self.update(add_to_set__parents=parent)

        if full_reload:
            self.safe_reload()

        if update_reverse_link:
            parent.add_child(self, update_reverse_link=False)

    def remove_parent(self, parent, update_reverse_link=True, full_reload=True):

        if update_reverse_link:
            parent.remove_child(self, update_reverse_link=False)

        self.update(pull__parents=parent)

        if full_reload:
            self.safe_reload()

    def add_child(self, child, update_reverse_link=True, full_reload=True):
        self.update(add_to_set__children=child)

        if full_reload:
            self.safe_reload()

        if update_reverse_link:
            child.add_parent(self, update_reverse_link=False)

    def remove_child(self, child, update_reverse_link=True, full_reload=True):

        if update_reverse_link:
            child.remove_parent(self, update_reverse_link=False)

        self.update(pull__children=child)

        if full_reload:
            self.safe_reload()


# •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Feed


def feed_all_articles_count_default(feed, *args, **kwargs):

    return feed.all_articles.count()


def feed_recent_articles_count_default(feed, *args, **kwargs):

    return feed.recent_articles.count()


def feed_subscriptions_count_default(feed, *args, **kwargs):

    return feed.subscriptions.count()


@task(name='Feed.update_latest_article_date_published', queue='low')
def feed_update_latest_article_date_published(feed_id, *args, **kwargs):

    feed = Feed.objects.get(id=feed_id)
    return feed.update_latest_article_date_published(*args, **kwargs)


@task(name='Feed.update_recent_articles_count', queue='low')
def feed_update_recent_articles_count(feed_id, *args, **kwargs):

    feed = Feed.objects.get(id=feed_id)
    return feed.update_recent_articles_count(*args, **kwargs)


@task(name='Feed.update_subscriptions_count', queue='low')
def feed_update_subscriptions_count(feed_id, *args, **kwargs):

    feed = Feed.objects.get(id=feed_id)
    return feed.update_subscriptions_count(*args, **kwargs)


@task(name='Feed.update_all_articles_count', queue='low')
def feed_update_all_articles_count(feed_id, *args, **kwargs):

    feed = Feed.objects.get(id=feed_id)
    return feed.update_all_articles_count(*args, **kwargs)


@task(name='Feed.refresh', queue='medium')
def feed_refresh(feed_id, *args, **kwargs):

    feed = Feed.objects.get(id=feed_id)
    return feed.refresh(*args, **kwargs)


class Feed(Document, DocumentHelperMixin):
    name           = StringField(verbose_name=_(u'name'))
    url            = URLField(unique=True, verbose_name=_(u'url'))
    site_url       = URLField(verbose_name=_(u'web site'))
    slug           = StringField(verbose_name=_(u'slug'))
    tags           = ListField(ReferenceField('Tag', reverse_delete_rule=PULL),
                               default=list, verbose_name=_(u'tags'),
                               help_text=_(u'This tags are used only when '
                                           u'articles from this feed have no '
                                           u'tags already. They are assigned '
                                           u'to new subscriptions too.'))
    languages      = ListField(StringField(max_length=5,
                               choices=settings.LANGUAGES),
                               verbose_name=_(u'Languages'),
                               required=False,
                               help_text=_(u'Set this to more than one '
                                           u'language to help article '
                                           u'language detection if none '
                                           u'is set in articles.'))
    date_added     = DateTimeField(default=datetime(2013, 07, 01),
                                   verbose_name=_(u'date added'))
    restricted     = BooleanField(default=False, verbose_name=_(u'restricted'),
                                  help_text=_(u'Is this feed available only to '
                                              u'paid subscribers on its '
                                              u'publisher\'s web site?'))
    closed         = BooleanField(default=False, verbose_name=_(u'closed'),
                                  help_text=_(u'Indicate that the feed is not '
                                              u'fetched anymore (see '
                                              u'“closed_reason” for why). '
                                              u'/!\\ WARNING: do not just '
                                              u'tick the checkbox; there is '
                                              u'a programmatic procedure to '
                                              u'close a feed properly.'))
    date_closed    = DateTimeField(verbose_name=_(u'date closed'))
    closed_reason  = StringField(verbose_name=_(u'closed reason'))

    fetch_interval = IntField(default=config.FEED_FETCH_DEFAULT_INTERVAL,
                              verbose_name=_(u'fetch interval'))
    last_fetch     = DateTimeField(verbose_name=_(u'last fetch'))

    # TODO: move this into WebSite to avoid too much parallel fetches
    # when using multiple feeds from the same origin website.
    fetch_limit_nr = IntField(default=config.FEED_FETCH_PARALLEL_LIMIT,
                              verbose_name=_(u'fetch limit'),
                              help_text=_(u'The maximum number of articles '
                                          u'that can be fetched from the feed '
                                          u'in parallel. If less than %s, '
                                          u'do not touch: the workers have '
                                          u'already tuned it from real-life '
                                          u'results.'))

    # Stored directly from feedparser data to avoid wasting BW.
    last_etag      = StringField(verbose_name=_(u'last etag'))
    last_modified  = StringField(verbose_name=_(u'modified'))

    mail_warned    = ListField(StringField())
    errors         = ListField(StringField())
    options        = ListField(IntField())
    duplicate_of   = ReferenceField(u'Feed', reverse_delete_rule=NULLIFY)
    notes          = StringField(verbose_name=_(u'Notes'),
                                 help_text=_(u'Internal notes for 1flow '
                                             u'staff related to this feed.'))

    good_for_use = BooleanField(verbose_name=_(u'Shown in selector'),
                                default=False,
                                help_text=_(u'Make this feed available to new '
                                            u'subscribers in the selector '
                                            u'wizard. Without this, the user '
                                            u'can still subscribe but he '
                                            u'must know it and manually enter '
                                            u'the feed address.'))
    thumbnail_url  = URLField(verbose_name=_(u'Thumbnail URL'),
                              help_text=_(u'Full URL of the thumbnail '
                                          u'displayed in the feed selector. '
                                          u'Can be hosted outside of 1flow.'))
    description_fr = StringField(verbose_name=_(u'Description (FR)'),
                                 help_text=_(u'Public description of the feed '
                                             u'in French language. '
                                             u'As Markdown.'))
    description_en = StringField(verbose_name=_(u'Description (EN)'),
                                 help_text=_(u'Public description of the feed '
                                             u'in English language. '
                                             u'As Markdown.'))

    # ••••••••••••••••••••••••••••••• properties, cached descriptors & updaters

    # TODO: create an abstract class that will allow to not specify
    #       the attr_name here, but make it automatically created.
    #       This is an underlying implementation detail and doesn't
    #       belong here.
    latest_article_date_published = DatetimeRedisDescriptor(
        # 5 years ealier should suffice to get old posts when starting import.
        attr_name='f.la_dp', default=now() - timedelta(days=1826))

    all_articles_count = IntRedisDescriptor(
        attr_name='f.aa_c', default=feed_all_articles_count_default,
        set_default=True)

    recent_articles_count = IntRedisDescriptor(
        attr_name='f.ra_c', default=feed_recent_articles_count_default,
        set_default=True)

    subscriptions_count = IntRedisDescriptor(
        attr_name='f.s_c', default=feed_subscriptions_count_default,
        set_default=True)

    @property
    def latest_article(self):

        latest = self.get_articles(1)

        try:
            return latest[0]

        except:
            return None

    def check_subscriptions(self, force=False):

        if not force:
            LOGGER.info(u'This method is very costy and should not be needed '
                        u'in normal conditions. Please call it with '
                        u'`force=True` if you are sure you want to run it.')
            return

        reads = 0
        failed = 0
        unreads = 0
        missing = 0
        unregistered = 0

        articles = self.good_articles.order_by('-id')

        for subscription in self.subscriptions:
            smissing, sunreg, sreads, sunreads, sfailed = \
                subscription.check_reads(force, articles)

            reads += sreads
            failed += sfailed
            missing += smissing
            unreads += sunreads
            unregistered += sunreg

        LOGGER.info(u'Checked feed #%s with %s subscriptions and %s articles. '
                    u'Totals: %s/%s non-existing/unregistered reads, '
                    u'%s/%s read/unread and %s not created.', self.id,
                    self.subscriptions.count(), articles.count(),
                    missing, unregistered, reads, unreads, failed)

    def update_latest_article_date_published(self):
        """ This seems simple, but this operations costs a lot in MongoDB. """

        try:
            # This query should still cost less than the pure and bare
            # `self.latest_article.date_published` which will first sort
            # all articles of the feed before getting the first of them.
            self.latest_article_date_published = self.recent_articles.order_by(
                '-date_published').first().date_published
        except:
            # Don't worry, the default value of
            # the descriptor should fill the gaps.
            pass

    @property
    def recent_articles(self):
        return Article.objects.filter(
            feeds__contains=self).filter(
                date_published__gt=today()
                - timedelta(
                    days=config.FEED_ADMIN_MEANINGFUL_DELTA))

    def update_recent_articles_count(self, force=False):
        """ This task is protected to run only once per day,
            even if is called more. """

        urac_lock = RedisExpiringLock(self, lock_name='urac', expire_time=86100)

        if urac_lock.acquire() or force:
            self.recent_articles_count = self.recent_articles.count()

        elif not force:
            LOGGER.warning(u'No more than one update_recent_articles_count '
                           u'per day (feed %s).', self)
        #
        # Don't bother release the lock, this will
        # ensure we are not called until tomorrow.
        #

    @property
    def subscriptions(self):

        return Subscription.objects(feed=self)

    def update_subscriptions_count(self):

        self.subscriptions_count = self.subscriptions.count()

    @property
    def good_articles(self):
        """ Subscriptions should always use :attr:`good_articles` to give
            to users only useful content for them, whereas :class:`Feed`
            will use :attr:`articles` or :attr:`all_articles` to reflect
            real numbers.
        """

        return self.articles.filter(duplicate_of=None,
                                    url_absolute=True,
                                    orphaned__ne=True)

    def update_all_articles_count(self):

        self.all_articles_count = self.articles.count()

    # •••••••••••••••••••••••••••••••••••••••••••• end properties / descriptors

    # Doesn't seem to work, because Grappelli doesn't pick up Mongo classes.
    #
    # @staticmethod
    # def autocomplete_search_fields():
    #     return ('name__icontains', 'url__icontains', 'site_url__icontains', )

    def __unicode__(self):
        return _(u'{0} (#{1})').format(self.name, self.id)

    @property
    def refresh_lock(self):
        try:
            return self.__refresh_lock

        except AttributeError:
            self.__refresh_lock = RedisExpiringLock(self, lock_name='fetch')
            return self.__refresh_lock

    @property
    def fetch_limit(self):
        """ XXX: not used until correctly implemented.
            I removed the code calling this method on 20130910.
        """

        try:
            return self.__limit_semaphore

        except AttributeError:
            self.__limit_semaphore = RedisSemaphore(self, self.fetch_limit_nr)
            return self.__limit_semaphore

    def set_fetch_limit(self):
        """ XXX: not used until correctly implemented.
            I removed the code calling this method on 20130910.
        """

        new_limit = self.fetch_limit.set_limit()
        cur_limit = self.fetch_limit_nr

        if cur_limit != new_limit:
            self.fetch_limit_nr = new_limit
            self.save()

            LOGGER.info(u'Feed %s parallel fetch limit set to %s.',
                        self, new_limit)

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        feed = document

        if created:
            if feed._db_name != settings.MONGODB_NAME_ARCHIVE:
                # Update the feed immediately after creation.
                feed_refresh.delay(feed.id)

    def has_option(self, option):
        return option in self.options

    def reopen(self, commit=True):

        self.errors[:]     = []
        self.closed        = False
        self.date_closed   = now()
        self.closed_reason = u'Reopen on %s' % now().isoformat()
        self.save()

        LOGGER.info(u'Feed %s has just beed re-opened.', self)

    def close(self, reason=None, commit=True):
        self.update(set__closed=True, set__date_closed=now(),
                    set__closed_reason=reason or u'NO REASON GIVEN')

        LOGGER.info(u'Feed %s closed with reason "%s"!',
                    self, self.closed_reason)

        self.safe_reload()

    @property
    def articles(self):
        """ A simple version of :meth:`get_articles`. """

        return Article.objects(feeds__contains=self)

    def get_articles(self, limit=None):
        """ A parameter-able version of the :attr:`articles` property. """

        if limit:
            return Article.objects.filter(
                feeds__contains=self).order_by('-date_published').limit(limit)

        return Article.objects.filter(
            feeds__contains=self).order_by('-date_published')

    def validate(self, *args, **kwargs):
        try:
            super(Feed, self).validate(*args, **kwargs)

        except ValidationError as e:

            # We pop() because any error will close the feed, whatever it is.
            site_url_error = e.errors.pop('site_url', None)

            if site_url_error is not None:
                # Bad site URL, the feed is most probably totally unparsable.
                # Close it. Admins will be warned about it via mail from a
                # scheduled core task.
                #
                # WAS: if not 'bad_site_url' in self.mail_warned:
                #           self.mail_warned.append('bad_site_url')

                self.site_url = None
                self.close('Bad site url: %s' % str(site_url_error))

            # We pop() because any error will close the feed, whatever it is.
            url_error = e.errors.pop('url', None)

            if url_error is not None:
                if not self.closed:
                    self.close(str(url_error))

            thumbnail_url_error = e.errors.get('thumbnail_url', None)

            if thumbnail_url_error is not None:
                if self.thumbnail_url == u'':
                    # Just make this field not required. `required=False`
                    # in the Document definition is not sufficient.
                    e.errors.pop('thumbnail_url')

            if e.errors:
                raise ValidationError('ValidationError', errors=e.errors)

    def error(self, message, commit=True, last_fetch=False):
        """ Take note of an error. If the maximum number of errors is reached,
            close the feed and return ``True``; else just return ``False``.

            :param last_fetch: as a commodity, set this to ``True`` if you
                want this method to update the :attr:`last_fetch` attribute
                with the value of ``now()`` (UTC). Default: ``False``.

            :param commit: as in any other Django DB-related method, set
                this to ``False`` if you don't want this method to call
                ``self.save()``. Default: ``True``.
        """

        LOGGER.error(u'Error on feed %s: %s.', self, message)

        # Put the errors more recent first.
        self.errors.insert(0, u'%s @@%s' % (message, now().isoformat()))

        if last_fetch:
            self.last_fetch = now()

        retval = False

        if len(self.errors) >= config.FEED_FETCH_MAX_ERRORS:
            if not self.closed:
                self.close(u'Too many errors on the feed. Last was: %s'
                           % self.errors[0],

                           # prevent self.close() to reload()
                           # us before we save().
                           commit=False)

                LOGGER.critical(u'Too many errors on feed %s, closed.', self)

            # Keep only the most recent errors.
            self.errors = self.errors[:config.FEED_FETCH_MAX_ERRORS]

            retval = True

        if commit:
            self.save()

        return retval

    def create_article_and_reads(self, article, feed_tags):
        """ Take a feedparser item and a list of Feed subscribers and
            feed tags, and create the corresponding Article and Read(s). """

        feedparser_content = getattr(article, 'content', CONTENT_NOT_PARSED)

        if isinstance(feedparser_content, list):
            feedparser_content = feedparser_content[0]
            content = feedparser_content.get('value', CONTENT_NOT_PARSED)

        else:
            content = feedparser_content

        try:
            date_published = datetime(*article.published_parsed[:6])

        except:
            date_published = None

        tags = list(Tag.get_tags_set((
                    t['term'] for t in article.get('tags', [])
                    # Sometimes, t['term'] can be None.
                    # http://dev.1flow.net/webapps/1flow/group/4082/
                    if t['term'] is not None), origin=self) | set(feed_tags))

        try:
            new_article, created = Article.create_article(
                # Sometimes feedparser gives us URLs with spaces in them.
                # Using the full `urlquote()` on an already url-quoted URL
                # could be very destructive, thus we patch only this case.
                #
                # If there is no `.link`, we get '' to be able to `replace()`,
                # but in fine `None` is a more regular "no value" mean. Sorry
                # for the weird '' or None that just does the job.
                url=getattr(article, 'link', '').replace(' ', '%20') or None,

                # We *NEED* a title, but as we have no article.lang yet,
                # it must be language independant as much as possible.
                title=getattr(article, 'title', u' '),

                content=content, date_published=date_published,
                feeds=[self], tags=tags, origin_type=ORIGIN_TYPE_FEEDPARSER)

        except:
            # NOTE: duplication handling is already
            # taken care of in Article.create_article().
            LOGGER.exception(u'Article creation failed in feed %s.', self)
            return False

        if created:
            new_article.add_original_data('feedparser', unicode(article))

        mutualized = created is None

        if created or mutualized:
            self.recent_articles_count += 1
            self.all_articles_count += 1

        # Update the "latest date" kind-of-cache.
        if date_published is not None and \
                date_published > self.latest_article_date_published:
            self.latest_article_date_published = date_published

        # Even if the article wasn't created, we need to create reads.
        # In the case of a mutualized article, it will be fetched only
        # once, but all subscribers of all feeds must be connected to
        # it to be able to read it.
        new_article.create_reads(self.subscriptions, verbose=created)

        # Don't forget the parenthesis else we return ``False`` everytime.
        return created or (None if mutualized else False)

    def subscribe_user(self, user, force=False):

        try:
            sub = Subscription(user=user, feed=self,
                               name=self.name, tags=self.tags).save()

        except (NotUniqueError, DuplicateKeyError):
            if not force:
                LOGGER.info(u'User %s already subscribed to feed %s.',
                            user, self)
                return

        sub.check_reads(True)

        LOGGER.info(u'Subscribed %s to %s.', user, self)

    def build_refresh_kwargs(self):

        kwargs = {}

        # Implement last-modified & etag headers to save BW.
        # Cf. http://pythonhosted.org/feedparser/http-etag.html
        if self.last_modified:
            kwargs['modified'] = self.last_modified

        else:
            kwargs['modified'] = self.latest_article_date_published

        if self.last_etag:
            kwargs['etag'] = self.last_etag

        # Circumvent https://code.google.com/p/feedparser/issues/detail?id=390
        http_logger        = HttpResponseLogProcessor()
        kwargs['referrer'] = self.site_url
        kwargs['handlers'] = [http_logger]

        return kwargs, http_logger

    def refresh_must_abort(self, force=False, commit=True):
        """ Returns ``True`` if one or more abort conditions is met.
            Checks the feed cache lock, the ``last_fetch`` date, etc.
        """

        if self.closed:
            LOGGER.info(u'Feed %s is closed. refresh aborted.', self)
            return True

        if config.FEED_FETCH_DISABLED:
            # we do not raise .retry() because the global refresh
            # task will call us again anyway at next global check.
            LOGGER.info(u'Feed %s refresh disabled by configuration.', self)
            return True

        if not self.refresh_lock.acquire():
            if force:
                LOGGER.warning(u'Forcing refresh for feed %s, despite of '
                               u'lock already acquired.', self)
                self.refresh_lock.release()
                self.refresh_lock.acquire()
            else:
                LOGGER.info(u'Refresh for %s already running, aborting.', self)
                return True

        if self.last_fetch is not None and self.last_fetch >= (
                now() - timedelta(seconds=self.fetch_interval)):
            if force:
                LOGGER.warning(u'Forcing refresh of recently fetched feed %s.',
                               self)
            else:
                LOGGER.info(u'Last refresh of feed %s too recent, aborting.',
                            self)
                return True

        return False

    def has_feedparser_error(self, parsed_feed):

        if parsed_feed.get('bozo', None) is None:
            return False

        error = parsed_feed.get('bozo_exception', None)

        # Charset declaration problems are harmless (until they are not).
        if str(error).startswith('document declared as'):
            LOGGER.warning('Feed %s: %s', self, error)
            return False

        # currently, I've encountered no error fatal to feedparser.
        return False

        # Thus, no need for this yet, but it's ready.
        #self.error(u'feedparser error %s', str(error))

        # Do not close for this: it can be a temporary error.
        # if isinstance(exception, SAXParseException):
        #     self.close(reason=str(exception))
        #     return True
        #
        #return False
        #
        pass

    @staticmethod
    def throttle_fetch_interval(interval, news, mutualized,
                                duplicates, etag, modified):
        """ Try to adapt dynamically the fetch interval, to fetch more feeds
            that produce a lot of new entries, and less the ones that do not.

            Feeds which correctly implement etags/last_modified should not
            be affected negatively.

            Feeds producing a lot of news should see their interval lower
            quickly. Feeds producing only duplicates will be fetched less.
            Feeds producing mutualized will still be fetched fast, because
            they are producing new content, even if it mutualized with other
            feeds.

            Feeds producing nothing and that do not implement etags/modified
            should suffer a lot and burn in hell like sheeps.

            This is a static method to allow better testing from outside the
            class.
        """

        if news:
            if mutualized:
                if duplicates:
                    multiplicator = 0.8

                else:
                    multiplicator = 0.7

            elif duplicates:
                multiplicator = 0.9

            else:
                # Only fresh news. My Gosh, this feed
                # produces a lot! Speed up fetches!!
                multiplicator = 0.6

            if mutualized > min(5, config.FEED_FETCH_RAISE_THRESHOLD):
                # The thing is prolific. Speed up even more.
                multiplicator *= 0.9

            if news > min(5, config.FEED_FETCH_RAISE_THRESHOLD):
                # The thing is prolific. Speed up even more.
                multiplicator *= 0.9

        elif mutualized:
            # Speed up, also. But as everything was already fetched
            # by komrades, no need to speed up too much. Keep cool.

            if duplicates:
                multiplicator = 0.9

            else:
                multiplicator = 0.8

        elif duplicates:
            # If there are duplicates, either the feed doesn't use
            # etag/last_mod [correctly], either its a master/subfeed
            # for which articles have already been fetched by a peer.

            if etag or modified:
                # There is something wrong with the website,
                # it should not have offered us anything when
                # using etag/last_modified.
                multiplicator = 1.25

            else:
                multiplicator = 1.125

        else:
            # No duplicates (feed probably uses etag/last_mod) but no
            # new articles, nor mutualized. Keep up the good work, don't
            # change anything.
            multiplicator = 1.0

        interval *= multiplicator

        if interval > min(604800, config.FEED_FETCH_MAX_INTERVAL):
            interval = config.FEED_FETCH_MAX_INTERVAL

        if interval < max(60, config.FEED_FETCH_MIN_INTERVAL):
            interval = config.FEED_FETCH_MIN_INTERVAL

        return interval

    def refresh(self, force=False):
        """ Find new articles in an RSS feed.

            .. note:: we don't release the lock, this is intentional. The
                next refresh should not occur within the feed official
                refresh interval, this would waste resources.
        """

        # In tasks, doing this is often useful, if
        # the task waited a long time before running.
        self.safe_reload()

        if self.refresh_must_abort(force=force):
            self.refresh_lock.release()
            return

        LOGGER.info(u'Refreshing feed %s…', self)

        feedparser_kwargs, http_logger = self.build_refresh_kwargs()
        parsed_feed = feedparser.parse(self.url, **feedparser_kwargs)

        # In case of a redirection, just check the last hop HTTP status.
        try:
            feed_status = http_logger.log[-1]['status']

        except IndexError, e:
            # The website could not be reached? Network
            # unavailable? on my production server???

            # self.refresh_lock.release() ???
            raise feed_refresh.retry((self.id, ), exc=e)

        # Stop on HTTP errors before stopping on feedparser errors,
        # because he is much more lenient in many conditions.
        if feed_status in (400, 401, 402, 403, 404, 500, 502, 503):
            self.error(u'HTTP %s on %s' % (http_logger.log[-1]['status'],
                       http_logger.log[-1]['url']), last_fetch=True)
            return

        if self.has_feedparser_error(parsed_feed):
            # the method will have already call self.error().
            return

        if feed_status == 304:
            LOGGER.info(u'No new content in feed %s.', self)

            with statsd.pipeline() as spipe:
                spipe.incr('feeds.refresh.fetch.global.unchanged')

        else:
            tags = Tag.get_tags_set(getattr(parsed_feed, 'tags', []),
                                    origin=self)

            if tags != set(self.tags):
                # We consider the publisher knows the nature of his content
                # better than us, and we trust him about the tags he sets
                # on the feed. Thus, we don't union() with the new tags,
                # but simply replace current by new ones.
                LOGGER.info(u'Updating tags of feed %s from %s to %s.',
                            self.tags, tags)
                self.tags = list(tags)

            new_articles  = 0
            duplicates    = 0
            mutualized    = 0

            with statsd.pipeline() as spipe:
                spipe.incr('feeds.refresh.fetch.global.updated')

            for article in parsed_feed.entries:
                created = self.create_article_and_reads(article, tags)
                if created:
                    new_articles += 1

                elif created is False:
                    duplicates += 1

                else:
                    mutualized += 1

            # Store the date/etag for next cycle. Doing it after the full
            # refresh worked ensures that in case of any exception during
            # the loop, the retried refresh will restart on the same
            # entries without loosing anything.
            self.last_modified = getattr(parsed_feed, 'modified', None)
            self.last_etag     = getattr(parsed_feed, 'etag', None)

            if not force:
                # forcing the refresh is most often triggered by admins
                # and developers. It should not trigger the adaptative
                # throttling computations, because it generates a lot
                # of false-positive duplicates, and will.

                new_interval = Feed.throttle_fetch_interval(self.fetch_interval,
                                                            new_articles,
                                                            mutualized,
                                                            duplicates,
                                                            self.last_etag,
                                                            self.last_modified)

                if new_interval != self.fetch_interval:
                    LOGGER.info(u'Fetch interval changed from %s to %s '
                                u'for feed %s (%s new article(s), %s '
                                u'duplicate(s)).', self.fetch_interval,
                                new_interval, self, new_articles, duplicates)

                    self.fetch_interval = new_interval

            with statsd.pipeline() as spipe:
                spipe.incr('feeds.refresh.global.fetched', new_articles)
                spipe.incr('feeds.refresh.global.duplicates', duplicates)
                spipe.incr('feeds.refresh.global.mutualized', mutualized)

        # Everything went fine, be sure to reset the "error counter".
        self.errors[:]  = []
        self.last_fetch = now()
        self.save()

        with statsd.pipeline() as spipe:
            spipe.incr('feeds.refresh.fetch.global.done')

        # As the last_fetch is now up-to-date, we can release the fetch lock.
        # If any other refresh job comes, it will check last_fetch and will
        # terminate if called too early.
        self.refresh_lock.release()


# •••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Feed Subscriptions


@task(name='Subscription.post_create', queue='high')
def subscription_post_create_task(subscription_id, *args, **kwargs):

    subscription = Subscription.objects.get(id=subscription_id)
    return subscription.post_create_task(*args, **kwargs)


class Subscription(Document, DocumentHelperMixin):
    feed = ReferenceField('Feed', reverse_delete_rule=CASCADE)
    user = ReferenceField('User', unique_with='feed',
                          reverse_delete_rule=CASCADE)

    # allow the user to rename the field in its own subscription
    name = StringField()

    # TODO: convert to UserTag to use ReferenceField and reverse_delete_rule.
    tags = ListField(GenericReferenceField(),
                     default=list, verbose_name=_(u'tags'),
                     help_text=_(u'Tags that will be applied to new reads in '
                                 u'this subscription.'))

    def __unicode__(self):
        return _(u'{0}+{1} (#{2})').format(
            self.user.username, self.feed.name, self.id)

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        subscription = document

        if created:
            if subscription._db_name != settings.MONGODB_NAME_ARCHIVE:
                subscription_post_create_task.delay(subscription.id)

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        self.name = self.feed.name

        self.save()

    @property
    def reads(self):
        return Read.objects.filter(user=self.user, subscriptions__contains=self)

    def check_reads(self, force=False, articles=None):

        if not force:
            LOGGER.info(u'This method is very costy and should not be needed '
                        u'in normal conditions, please call with `force=True` '
                        u'if you are really sure you want to run it.')
            return

        yesterday    = combine(today() - timedelta(days=1), time(0, 0, 0))
        is_older     = False
        my_now       = now()
        reads        = 0
        unreads      = 0
        failed       = 0
        missing      = 0
        unregistered = 0

        # When checking the subscription from its feed, allow optimising
        # the whole story by not querying the articles again for each
        # subscription. The feed will do the query once, and forward the
        # QuerySet to all subscriptions to be checked.

        if articles is None:
            articles = self.feed.good_articles.order_by('-id')

        for article in articles:

            params = {}

            if is_older:
                params = {
                    'is_read': True,
                    'is_auto_read': True,
                    'date_read': my_now,
                    'date_auto_read': my_now,
                }
                reads += 1

            else:
                if article.date_published is None \
                        or article.date_published < yesterday:

                    is_older = True

                    params = {
                        'is_read': True,
                        'is_auto_read': True,
                        'date_read': my_now,
                        'date_auto_read': my_now,
                    }
                    reads += 1

                else:
                    unreads += 1

            created = article.create_reads([self], False, **params)

            if created:
                missing += 1

            elif created is False:
                unregistered += 1

            else:
                failed += 1

        if missing or unregistered:
            self.all_articles_count = \
                subscription_all_articles_count_default(self)
            self.unread_articles_count = \
                subscription_unread_articles_count_default(self)

            for folder in self.folders:
                folder.all_articles_count = \
                    folder_all_articles_count_default(folder)
                folder.unread_articles_count = \
                    folder_unread_articles_count_default(folder)

        LOGGER.info(u'Checked subscription #%s. '
                    u'%s/%s non-existing/unregistered, '
                    u'%s/%s read/unread and %s not created.',
                    self.id, missing, unregistered,
                    reads, unreads, failed)

        return missing, unregistered, reads, unreads, failed


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Authors


@task(name=u'Author.post_create', queue=u'high')
def author_post_create_task(author_id, *args, **kwargs):

    author = Author.objects.get(id=author_id)
    return author.post_create_task(*args, **kwargs)


class Author(Document, DocumentHelperMixin):
    name        = StringField()
    website     = ReferenceField(u'WebSite', unique_with=u'origin_name',
                                 reverse_delete_rule=CASCADE)
    origin_name = StringField(help_text=_(u'When trying to guess authors, we '
                              u'have only a "fullname" equivalent. We need to '
                              u'store it for future comparisons in case '
                              u'firstname and lastname get manually modified '
                              u'after author creation.'))

    is_unsure = BooleanField(help_text=_(u'Set to True when the author '
                             u'has been found from its origin_name and '
                             u'not via email; because origin_name can '
                             u'be duplicated, but not emails.'),
                             default=False)

    user = ReferenceField(u'User', required=False, help_text=_(u'Link an '
                          u'internet author to a 1flow user.'),
                          reverse_delete_rule=NULLIFY)

    duplicate_of = ReferenceField(u'Author', reverse_delete_rule=NULLIFY)

    def __unicode__(self):
        return u'%s%s #%s for website %s' % (self.name or self.origin_name,
                                             _(u' (unsure)')
                                             if self.is_unsure else u'',
                                             self.id, self.website)

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        author = document

        if created:
            if author._db_name != settings.MONGODB_NAME_ARCHIVE:
                author_post_create_task.delay(author.id)

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        statsd.gauge('authors.counts.total', 1, delta=True)

    @classmethod
    def get_authors_from_feedparser_article(cls, feedparser_article,
                                            set_to_article=None):

        if set_to_article:
            # This is an absolutized URL, hopefully.
            article_url = set_to_article.url

        else:
            article_url = getattr(feedparser_article, 'link',
                                  '').replace(' ', '%20') or None

        if article_url:
            website = WebSite.get_from_url(article_url)

        else:
            LOGGER.critical(u'NO url, cannot get any author.')

        authors = set()

        if 'authors' in feedparser_article:
            # 'authors' can be [{}], which is useless.

            for author_dict in feedparser_article['authors']:
                author = cls.get_author_from_feedparser_dict(author_dict,
                                                             website)

                if author:
                    if set_to_article:
                        set_to_article.update(add_to_set__authors=author)

                    authors.add(author)

        if 'author_detail' in feedparser_article:
            author = cls.get_author_from_feedparser_dict(
                feedparser_article['author_detail'], website)

            if author:
                if set_to_article:
                    set_to_article.update(add_to_set__authors=author)

                authors.add(author)

        if 'author' in feedparser_article:
            author = cls.get_author_from_feedparser_dict(
                {'name': feedparser_article['author']}, website)

            if author:
                if set_to_article:
                    set_to_article.update(add_to_set__authors=author)

                authors.add(author)

        if set_to_article and authors:
            set_to_article.reload()

        # Always return a list, else we hit
        # http://dev.1flow.net/development/1flow-dev/group/4026/
        return list(authors)

    @classmethod
    def get_author_from_feedparser_dict(cls, author_dict, website):

        email = author_dict.get('email', None)

        if email:
            # An email is less likely to have a duplicates than
            # a standard name. It takes precedence if it exists.

            try:
                return cls.objects.get(origin_name=email, website=website)

            except cls.DoesNotExist:
                try:
                    return cls(origin_name=email, website=website,
                               is_unsure=False).save()

                except (NotUniqueError, DuplicateKeyError):
                    # We just hit the race condition with two creations
                    # At the same time. Same player shoots again.
                    return cls.objects.get(origin_name=email, website=website)

        home_page = author_dict.get('href', None)

        if home_page:
            # A home_page is less likely to have a duplicates than a standard
            # name too. It also takes precedence after email if it exists.

            try:
                return cls.objects.get(origin_name=home_page, website=website)

            except cls.DoesNotExist:
                try:
                    return cls(origin_name=home_page, website=website,
                               is_unsure=False).save()

                except (NotUniqueError, DuplicateKeyError):
                    # We just hit the race condition with two creations
                    # At the same time. Same player shoots again.
                    return cls.objects.get(origin_name=home_page,
                                           website=website)

        origin_name = author_dict.get('name', None)

        if origin_name:
            try:
                return cls.objects.get(origin_name=origin_name,
                                       website=website)

            except cls.DoesNotExist:
                try:
                    return cls(origin_name=origin_name,
                               website=website,
                               is_unsure=True).save()
                except (NotUniqueError, DuplicateKeyError):
                    # We just hit the race condition with two creations
                    # At the same time. Same player shoots again.
                    return cls.objects.get(origin_name=origin_name,
                                           website=website)

        return None


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Article


@task(name='Article.absolutize_url', queue='swarm', default_retry_delay=3600)
def article_absolutize_url(article_id, *args, **kwargs):

    article = Article.objects.get(id=article_id)
    return article.absolutize_url(*args, **kwargs)


@task(name='Article.postprocess_original_data', queue='low')
def article_postprocess_original_data(article_id, *args, **kwargs):

    article = Article.objects.get(id=article_id)
    return article.postprocess_original_data(*args, **kwargs)


@task(name='Article.replace_duplicate_everywhere', queue='low')
def article_replace_duplicate_everywhere(article_id, dupe_id, *args, **kwargs):

    article = Article.objects.get(id=article_id)
    dupe    = Article.objects.get(id=dupe_id)
    return article.replace_duplicate_everywhere(dupe, *args, **kwargs)


@task(name='Article.find_image', queue='fetch', default_retry_delay=3600)
def article_find_image(article_id, *args, **kwargs):

    article = Article.objects.get(id=article_id)
    return article.find_image(*args, **kwargs)


@task(name='Article.fetch_content', queue='fetch', default_retry_delay=3600)
def article_fetch_content(article_id, *args, **kwargs):

    article = Article.objects.get(id=article_id)
    return article.fetch_content(*args, **kwargs)


@task(name='Article.post_create', queue='high')
def article_post_create_task(article_id, *args, **kwargs):

    article = Article.objects.get(id=article_id)
    return article.post_create_task(*args, **kwargs)


class Article(Document, DocumentHelperMixin):

    title        = StringField(max_length=256, required=True,
                               verbose_name=_(u'Title'))
    slug         = StringField(max_length=256)
    url          = URLField(unique=True, verbose_name=_(u'Public URL'))
    url_absolute = BooleanField(default=False, verbose_name=_(u'Absolute URL'),
                                help_text=_(u'The article URL has been '
                                            u'successfully absolutized '
                                            u'to its unique and final '
                                            u'location.'))
    url_error  = StringField(verbose_name=_(u'URL fetch error'), default=u'',
                             help_text=_(u'Error when absolutizing the URL'))
    pages_urls = ListField(URLField(), verbose_name=_(u'Next pages URLs'),
                           help_text=_(u'In case of a multi-pages article, '
                                       u'other pages URLs will be here.'))
    # not yet.
    #short_url  = URLField(unique=True, verbose_name=_(u'1flow URL'))

    orphaned   = BooleanField(default=False, verbose_name=_(u'Orphaned'),
                              help_text=_(u'This article has no public URL '
                                          u'anymore, or is unfetchable for '
                                          u'some reason.'))

    word_count = IntField(verbose_name=_(u'Word count'))

    authors    = ListField(ReferenceField(u'Author', reverse_delete_rule=PULL))
    publishers = ListField(ReferenceField(u'User', reverse_delete_rule=PULL))

    date_published = DateTimeField(verbose_name=_(u'date published'),
                                   help_text=_(u"When the article first "
                                               u"appeared on the publisher's "
                                               u"website."))
    date_added     = DateTimeField(default=now,
                                   verbose_name=_(u'Date added'),
                                   help_text=_(u'When the article was added '
                                               u'to the 1flow database.'))

    tags = ListField(ReferenceField('Tag', reverse_delete_rule=PULL),
                     default=list, verbose_name=_(u'Tags'),
                     help_text=_(u'Default tags that will be applied to '
                                 u'new reads of this article.'))
    default_rating = FloatField(default=0.0, verbose_name=_(u'default rating'),
                                help_text=_(u'Rating used as a base when a '
                                            u'user has not already rated the '
                                            u'content.'))
    language       = StringField(verbose_name=_(u'Article language'),
                                 max_length=5,
                                 help_text=_(u'2 letters or 5 characters '
                                             u'language code (eg “en”, '
                                             u'“fr-FR”…).'))
    text_direction = StringField(verbose_name=_(u'Text direction'),
                                 choices=((u'ltr', _(u'Left-to-Right')),
                                          (u'rtl', _(u'Right-to-Left'))),
                                 default=u'ltr', max_length=3)

    image_url     = StringField(verbose_name=_(u'image URL'))
    abstract      = StringField(verbose_name=_(u'abstract'),
                                help_text=_(u'Small exerpt of content, '
                                            u'if applicable.'))
    content       = StringField(default=CONTENT_NOT_PARSED,
                                verbose_name=_(u'Content'),
                                help_text=_(u'Article content'))
    content_type  = IntField(default=CONTENT_TYPE_NONE,
                             verbose_name=_(u'Content type'),
                             help_text=_(u'Type of article content '
                                         u'(text, image…)'))
    content_error = StringField(verbose_name=_(u'Error'), default=u'',
                                help_text=_(u'Error when fetching content'))

    # A snap / a serie of snaps references the original article.
    # An article references its source (origin blog / newspaper…)
    source = ReferenceField('self', reverse_delete_rule=NULLIFY)

    origin_type = IntField(default=ORIGIN_TYPE_NONE,
                           verbose_name=_(u'Origin type'),
                           help_text=_(u'Origin of article (feedparser, '
                                       u'twitter, websnap…). Can be 0 '
                                       u'(none/unknown).'))

    feeds = ListField(ReferenceField('Feed', reverse_delete_rule=PULL),
                      default=list)

    comments_feed = URLField()

    @property
    def feed(self):
        """ return the first available feed for this article (an article can
            be mutualized in many RSS feeds and thus have more than one).

            .. note:: Can be ``None``, for example if the user snapped an
                article directly from a standalone web page in browser.
        """

        try:
            return self.feeds[0]

        except IndexError:
            return None

    # Allow quick find of duplicates if we ever want to delete them.
    duplicate_of = ReferenceField('Article', verbose_name=_(u'Duplicate of'),
                                  help_text=_(u'This article is a duplicate of '
                                              u'another, which is referenced '
                                              u'here. Even if they have '
                                              u'different URLs (eg. one can be '
                                              u'shortened, the other not), '
                                              u'they lead to the same final '
                                              u'destination on the web.'),
                                  reverse_delete_rule=NULLIFY)

    meta = {
        'indexes': [
            'content_type',
            'content_error',
            'url_error',
            'date_published',
            {'fields': ('duplicate_of', ), 'sparse': True},
            {'fields': ('source', ), 'sparse': True}

        ]
    }

    def __unicode__(self):
        return _(u'{0} (#{1}) from {2}').format(self.title, self.id, self.url)

    def validate(self, *args, **kwargs):
        try:
            super(Article, self).validate(*args, **kwargs)

        except ValidationError as e:
            title_error = e.errors.get('title', None)

            if title_error and str(title_error).startswith(
                    'String value is too long'):
                self.title = self.title[:255] + (self.title[:255] and u'…')
                e.errors.pop('title')

            tags_error = e.errors.get('tags', None)

            if tags_error and 'GenericReferences can only contain documents' \
                    in str(tags_error):

                self.tags = [t for t in self.tags if t is not None]
                e.errors.pop('tags')

            comments_error = e.errors.get('comments_feed', None)

            if comments_error and self.comments_feed == '':
                # Oh please, don't bother me.
                self.comments_feed = None
                e.errors.pop('comments_feed')

            language_error = e.errors.get('language', None)

            if language_error and self.language in (u'', None):
                # Oh please, don't bother me.
                # Again, required=False doesn't work at all.
                e.errors.pop('language')

            if e.errors:
                raise e

    def is_origin(self):
        return isinstance(self.source, Source)

    @property
    def reads(self):
        return Read.objects.filter(article=self)

    @property
    def get_source(self):

        if self.source:
            return self.source

        if self.feeds:
            return self.feeds

        return _('Unknown source')

    @property
    def get_source_unicode(self):

        source = self.get_source

        if source.__class__ in (unicode, str):
            return source

        sources_count = len(source)

        if sources_count > 2:
            return _(u'Multiple sources ({0} feeds)').format(sources_count)

        return u' / '.join(x.name for x in source)

    @property
    def content_display(self):

        if len(self.content) > config.READ_ARTICLE_MIN_LENGTH:

            # TODO: temporary measure, please get rid of this…

            title_len  = len(self.title)

            transient_content = self.content

            if title_len > 10:
                search_len = title_len * 2

                diff = difflib.SequenceMatcher(None,
                                               self.content[:search_len],
                                               self.title)

                if diff.ratio() > 0.51:
                    for blk in reversed(diff.matching_blocks):
                        # Sometimes, last match is the empty string… Skip it.
                        if blk[-1] != 0:
                            transient_content = self.content[blk[0] + blk[2]:]
                            break

            try:
                return markdown(transient_content)

            except Exception:
                LOGGER.exception(u'Live Markdown to HTML conversion '
                                 u'failed for article %s', self)

    @property
    def original_data(self):
        try:
            return OriginalData.objects.get(article=self)

        except OriginalData.DoesNotExist:
            return OriginalData(article=self).save()

    def add_original_data(self, name, value):
        od = self.original_data

        setattr(od, name, value)
        od.save()

    def remove_original_data(self, name):
        od = self.original_data

        try:
            delattr(od, name)

        except AttributeError:
            pass

        else:
            od.save()

    def absolutize_url_must_abort(self, force=False, commit=True):

        if config.ARTICLE_ABSOLUTIZING_DISABLED:
            LOGGER.info(u'Absolutizing disabled by configuration, aborting.')
            return True

        if self.url_absolute and not force:
            LOGGER.info(u'URL of article %s is already absolute!', self)
            return True

        if self.orphaned and not force:
            LOGGER.warning(u'Article %s is orphaned, absolutization aborted.',
                           self)
            return True

        if self.url_error:
            if force:
                self.url_error = u''

                if commit:
                    self.save()
            else:
                LOGGER.warning(u'Article %s already has an URL error, '
                               u'aborting absolutization (currently: %s).',
                               self, self.url_error)
                return True

        return False

    def absolutize_url_post_process(self, requests_response):

        url = requests_response.url

        try:
            proto, host_and_port, remaining = WebSite.split_url(url)

        except ValueError:
            return url

        if 'da.feedsportal.com' in host_and_port:
            # Sometimes the redirect chain breaks and gives us
            # a F*G page with links in many languages "click here
            # to continue".
            bsoup = BeautifulSoup(requests_response.content)
            for anchor in bsoup.findAll('a'):
                if u'here to continue' in anchor.text:
                    return clean_url(anchor['href'])

            # If we come here, feed portal template has probably changed.
            # Developers should be noticed about it.
            LOGGER.critical(u'Feedportal post-processing failed '
                            u'for article %s (no redirect tag found '
                            u'at address %s)!', self, url)

        # if nothing matched before, just clean the
        # last URL we got. Better than nothing.
        return clean_url(requests_response.url)

    def absolutize_url(self, requests_response=None, force=False, commit=True):
        """ Make the current article URL absolute. Eg. transform:

            http://feedproxy.google.com/~r/francaistechcrunch/~3/hEIhLwVyEEI/

            into:

            http://techcrunch.com/2013/05/18/hell-no-tumblr-users-wont-go-to-yahoo/ # NOQA
                ?utm_source=feeurner&utm_medium=feed&utm_campaign=Feed%3A+francaistechcrunch+%28TechCrunch+en+Francais%29 # NOQA

            and then remove all these F*G utm_* parameters to get a clean
            final URL for the current article.

            Returns ``True`` if the operation succeeded, ``False`` if the
            absolutization pointed out that the current article is a
            duplicate of another. In this case the caller should stop its
            processing because the current article will be marked for deletion.

            Can also return ``None`` if absolutizing is disabled globally
            in ``constance`` configuration.
        """

        # Another example: http://rss.lefigaro.fr/~r/lefigaro/laune/~3/7jgyrQ-PmBA/story01.htm # NOQA

        # ALL celery task methods need to reload the instance in case
        # we added new attributes before the object was pickled to a task.
        self.safe_reload()

        if self.absolutize_url_must_abort(force=force, commit=commit):
            return

        if requests_response is None:
            try:
                requests_response = requests.get(self.url,
                                                 headers=REQUEST_BASE_HEADERS)

            except requests.ConnectionError, e:
                statsd.gauge('articles.counts.url_errors', 1, delta=True)
                self.url_error = str(e)
                self.save()

                LOGGER.error(u'Connection failed while absolutizing URL or %s.',
                             self)
                return

        if not requests_response.ok or requests_response.status_code != 200:

            message = u'HTTP Error %s (%s) while resolving %s.'
            args = (requests_response.status_code, requests_response.reason,
                    requests_response.url)

            with statsd.pipeline() as spipe:
                spipe.gauge('articles.counts.orphaned', 1, delta=True)
                spipe.gauge('articles.counts.url_errors', 1, delta=True)

            self.orphaned  = True
            self.url_error = message % args
            self.save()

            LOGGER.error(message, *args)
            return

        #
        # NOTE: we could also get it eventually from r.headers['link'],
        #       which contains '<another_url>'. We need to strip out
        #       the '<>', and re-absolutize this link, because in the
        #       example it's another redirector. Also r.links is a good
        #       candidate but in the example I used, it contains the
        #       shortlink, which must be re-resolved too.
        #
        #       So: as we already are at the final address *now*, no need
        #       bothering re-following another which would lead us to the
        #       the same final place.
        #

        final_url = self.absolutize_url_post_process(requests_response)

        if final_url != self.url:

            # Just for displaying purposes, see below.
            old_url = self.url

            if self.url_error:
                statsd.gauge('articles.counts.url_errors', -1, delta=True)

            # Even if we are a duplicate, we came until here and everything
            # went fine. We won't need to lookup again the absolute URL.
            statsd.gauge('articles.counts.absolutes', 1, delta=True)
            self.url_absolute = True
            self.url_error    = u''

            self.url = final_url

            try:
                self.save()

            except (NotUniqueError, DuplicateKeyError):
                original = Article.objects.get(url=final_url)

                # Just to display the right "old" one in sentry errors and logs.
                self.url = old_url

                LOGGER.info(u'Article %s is a duplicate of %s, '
                            u'registering as such.', self, original)

                original.register_duplicate(self)
                return False

            # Any other exception will raise. This is intentional.
            else:
                LOGGER.info(u'Article %s (#%s) successfully absolutized URL '
                            u'from %s to %s.', self.title, self.id,
                            old_url, final_url)

        else:
            # Don't do the job twice.
            if self.url_error:
                statsd.gauge('articles.counts.url_errors', -1, delta=True)

            statsd.gauge('articles.counts.absolutes', 1, delta=True)
            self.update(set__url_absolute=True, set__url_error='')
            self.safe_reload()

        return True

    def postprocess_original_data(self, force=False, commit=True):

        methods_table = {
            ORIGIN_TYPE_NONE: self.postprocess_guess_origin_data,
            ORIGIN_TYPE_FEEDPARSER: self.postprocess_feedparser_data,
        }

        meth = methods_table.get(self.origin_type, None)

        if meth is None:
            LOGGER.warning(u'No method to post-process origin type %s of '
                           u'article %s.', self.origin_type, self)
            return

        # This is a Celery task. reload the object
        # from the database for up-to-date attributes.
        self.safe_reload()

        meth(force=force, commit=commit)

    def postprocess_guess_origin_data(self, force=False, commit=True):

        need_save = False

        if self.original_data.feedparser_hydrated:
            self.origin_type = ORIGIN_TYPE_FEEDPARSER
            need_save        = True

        elif self.original_data.google_reader_hydrated:
            self.origin_type = ORIGIN_TYPE_GOOGLE_READER
            need_save        = True

        if need_save:
            if commit:
                self.save()

            # Now that we have an origin type, re-run the real post-processor.
            self.postprocess_original_data(force=force, commit=commit)

    def postprocess_feedparser_data(self, force=False, commit=True):
        """ XXX: should disappear when feedparser_data is useless. """

        if self.original_data.feedparser_processed and not force:
            LOGGER.info('feedparser data already post-processed.')
            return

        fpod = self.original_data.feedparser_hydrated

        if fpod:
            if self.tags == [] and 'tags' in fpod:
                tags = list(Tag.get_tags_set((t['term']
                            # Sometimes, t['term'] can be None.
                            # http://dev.1flow.net/webapps/1flow/group/4082/
                            for t in fpod['tags'] if t['term'] is not None),
                            origin=self))

                self.update_tags(tags, initial=True, need_reload=False)
                self.safe_reload()

            if self.authors == []:
                Author.get_authors_from_feedparser_article(fpod,
                                                           set_to_article=self)

            if self.language is None:
                language = fpod.get('summary_detail', {}).get('language', None)

                if language is None:
                    language = fpod.get('title_detail', {}).get(
                                        'language', None)

                if language is not None:
                    try:
                        self.language = language.lower()
                        self.save()

                    except:
                        # This happens if the language code of the
                        # feedparser data does not correspond to a
                        # Django setting language we support.
                        LOGGER.exception(u'Cannot set language %s on '
                                         u'article %s.', language, self)

            if self.orphaned:
                # We have a chance to get at least *some* content. It will
                # probably be incomplete, but this is better than nothing.

                detail = fpod.get('summary_detail', {})

                if detail:
                    detail_type = detail.get('type', None)
                    detail_value = detail.get('value', '')

                    # We need some *real* data, though
                    if len(detail_value) > 20:

                        if detail_type == 'text/plain':
                            self.content = detail_value
                            self.content_type = CONTENT_TYPE_MARKDOWN
                            self.save()

                            statsd.gauge('articles.counts.markdown',
                                         1, delta=True)

                        elif detail_type == 'text/html':
                            self.content = detail_value
                            self.content_type = CONTENT_TYPE_HTML
                            self.save()

                            statsd.gauge('articles.counts.html',
                                         1, delta=True)

                            self.convert_to_markdown()

                        else:
                            LOGGER.warning(u'No usable content-type found '
                                           u'while trying to recover article '
                                           u'%s content: %s => "%s".', self,
                                           detail_type, detail_value)
                    else:
                        LOGGER.warning(u'Empty (or nearly) content-type '
                                       u'found while trying to recover '
                                       u'orphaned article %s '
                                       u'content: %s => "%s".', self,
                                       detail_type, detail_value)
                else:
                    LOGGER.warning(u'No summary detail found while trying '
                                   u'to recover orphaned article %s '
                                   u'content.', self)

            if self.comments_feed is None:

                comments_feed_url = fpod.get('wfw_commentrss', None)

                if comments_feed_url:
                    self.comments_feed = comments_feed_url
                    self.save()

            # We don't care anymore, it's already in another database.
            #self.offload_attribute('feedparser_original_data')

        self.original_data.update(set__feedparser_processed=True)

    def postprocess_google_reader_data(self, force=False, commit=True):
        LOGGER.warning(u'postprocess_google_reader_data() is not implemented '
                       u'yet but it was called for article %s!', self)

    def update_tags(self, tags, initial=False, need_reload=True):

        if initial:
            self.update(set__tags=tags)

        else:
            for tag in tags:
                self.update(add_to_set__tags=tag)

        if need_reload:
            self.safe_reload()

        for read in self.reads:
            if initial:
                read.update(set__tags=tags)

            else:
                for tag in tags:
                    read.update(add_to_set__tags=tag)

            if need_reload:
                read.safe_reload()

    def replace_duplicate_everywhere(self, duplicate, force=False):
        """ register :param:`duplicate` as a duplicate content of myself.

            redirect/modify all reads and feeds links to me, keeping all
            attributes as they are.
        """

        need_reload = False

        for feed in duplicate.feeds:
            try:
                self.update(add_to_set__feeds=feed)

            except:
                # We have to continue to replace reads,
                # and reload() at the end of the method.
                LOGGER.exception(u'Could not add feed %s to feeds of '
                                 u'article %s!', feed, self)
            else:
                need_reload = True

        if need_reload:
            self.safe_reload()

        for read in duplicate.reads:
            read.article = self

            try:
                read.save()

            except (NotUniqueError, DuplicateKeyError):
                # Already registered, simply delete the read.
                read.delete()

            except:
                LOGGER.exception(u'Could not replace current article in '
                                 u'read %s by %s!' % (read, self))

        statsd.gauge('articles.counts.duplicates', 1, delta=True)

        LOGGER.info(u'Article %s successfully registered as duplicate '
                    u'of %s and can be deleted if wanted.', duplicate, self)

    def create_reads(self, subscriptions, verbose=True, **kwargs):

        for subscription in subscriptions:
            new_read = Read(article=self, user=subscription.user)

            try:
                new_read.save()

            except (NotUniqueError, DuplicateKeyError):
                if verbose:
                    LOGGER.info(u'Duplicate read %s!', new_read)

                cur_read = Read.objects(article=self, user=subscription.user)
                # If another feed has already created the read, be sure the
                # current one is registered in the read via the subscriptions.
                cur_read.update(add_to_set__subscriptions=subscription)
                return False

            except:
                LOGGER.exception(u'Could not save read %s!', new_read)

            else:

                # XXX: todo remove this, when globally fixed.
                tags = [t for t in self.tags if t is not None]

                params = dict(('set__' + key, value)
                              for key, value in kwargs.items())

                new_read.update(set__tags=tags, **params)

                return True

    @classmethod
    def create_article(cls, title, url, feeds, **kwargs):
        """ Returns ``True`` if article created, ``False`` if a pure duplicate
            (already exists in the same feed), ``None`` if exists but not in
            the same feed. If more than one feed given, only returns ``True``
            or ``False`` (mutualized state is not checked). """

        if url is None:
            reset_url = True
            # Even for a temporary action, we need something unique…
            url = ARTICLE_ORPHANED_BASE + uuid.uuid4().hex

        else:
            reset_url = False
            url = clean_url(url)

        new_article = cls(title=title, url=url)

        try:
            new_article.save()

        except (DuplicateKeyError, NotUniqueError):
            LOGGER.info(u'Duplicate article “%s” (url: %s) in feed(s) %s.',
                        title, url, u', '.join(unicode(f) for f in feeds))

            cur_article = cls.objects.get(url=url)

            created_retval = False

            if len(feeds) == 1 and feeds[0] not in cur_article.feeds:
                # This article is already there, but has not yet been
                # fetched for this feed. It's mutualized, and as such
                # it is considered at partly new. At least, it's not
                # as bad as being a true duplicate.
                created_retval = None

            for feed in feeds:
                cur_article.update(add_to_set__feeds=feed)

            cur_article.safe_reload()

            return cur_article, created_retval

        else:

            tags = kwargs.pop('tags', [])

            if tags:
                new_article.update(add_to_set__tags=tags)
                new_article.safe_reload()

            need_save = False

            if kwargs:
                need_save = True
                for key, value in kwargs.items():
                    setattr(new_article, key, value)

            if reset_url:
                need_save       = True
                new_article.url = \
                    ARTICLE_ORPHANED_BASE + unicode(new_article.id)
                new_article.orphaned = True
                statsd.gauge('articles.counts.orphaned', 1, delta=True)

            if need_save:
                # Need to save because we will reload just after.
                new_article.save()

            if feeds:
                for feed in feeds:
                    new_article.update(add_to_set__feeds=feed)

                new_article.safe_reload()

            LOGGER.info(u'Created %sarticle %s in feed(s) %s.', u'orphaned '
                        if reset_url else u'', new_article,
                        u', '.join(unicode(f) for f in feeds))

            return new_article, True

    def fetch_content_must_abort(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_DISABLED:
            LOGGER.info(u'Article fetching disabled in configuration.')
            return True

        if self.content_type in CONTENT_TYPES_FINAL and not force:
            LOGGER.info(u'Article %s has already been fetched.', self)
            return True

        if self.content_error:
            if force:
                statsd.gauge('articles.counts.content_errors', -1, delta=True)
                self.content_error = u''

                if commit:
                    self.save()

            else:
                LOGGER.warning(u'Article %s has a fetching error, aborting '
                               u'(%s).', self, self.content_error)
                return True

        if self.url_error:
            LOGGER.warning(u'Article %s has an url error. Absolutize it to '
                           u'clear: %s.', self, self.url_error)
            return True

        if self.orphaned and not force:
            LOGGER.warning(u'Article %s is orphaned, cannot fetch.', self)
            return True

        if self.duplicate_of and not force:
            LOGGER.warning(u'Article %s is a duplicate, will not fetch.', self)
            return True

        return False

    def fetch_content(self, force=False, commit=True):

        # In tasks, doing this is often useful, if
        # the task waited a long time before running.
        self.safe_reload()

        if self.fetch_content_must_abort(force=force, commit=commit):
            return

        #
        # TODO: implement switch based on content type.
        #

        try:
            self.fetch_content_text(force=force, commit=commit)

        except StopProcessingException, e:
            LOGGER.info(u'Stopping processing of article %s on behalf of '
                        u'an internal caller: %s.', self, e)
            return

        except SoftTimeLimitExceeded, e:
            statsd.gauge('articles.counts.content_errors', 1, delta=True)
            self.content_error = str(e)
            self.save()

            LOGGER.error(u'Extraction took too long for article %s.', self)
            return

        except NotTextHtmlException, e:
            statsd.gauge('articles.counts.content_errors', 1, delta=True)
            self.content_error = str(e)
            self.save()

            LOGGER.error(u'No text/html to extract in article %s.', self)
            return

        except requests.ConnectionError, e:
            statsd.gauge('articles.counts.content_errors', 1, delta=True)
            self.content_error = str(e)
            self.save()

            LOGGER.error(u'Connection failed while fetching article %s.', self)
            return

        except Exception, e:
            # TODO: except urllib2.error: retry with longer delay.
            statsd.gauge('articles.counts.content_errors', 1, delta=True)
            self.content_error = str(e)
            self.save()

            LOGGER.exception(u'Extraction failed for article %s.', self)
            return

    def find_image_must_abort(self, force=False, commit=True):

        if self.image_url and not force:
            LOGGER.info(u'Article %s image already found.', self)
            return True

        if not self.content_type in (CONTENT_TYPE_MARKDOWN, ):
            LOGGER.warning(u'Article %s is not in Markdown format, '
                           u'aborting image lookup.', self)
            return True

    def find_image(self, force=False, commit=True):

        LOGGER.info(u'Article.find_image() needs love, disabled for now.')
        return

        if self.find_image_must_abort(force=force, commit=commit):
            return

        try:
            for match in re.finditer(ur'![[][^]]+[]][(]([^)]+)[)]',
                                     self.content):
                if match:
                    self.image_url = match.group(1)

                    if commit:
                        self.save()
                    break

            if not self.image_url:
                if self.feed and self.feed.default_image_url:
                    self.image_url = self.feed.default_image_url

                    if commit:
                        self.save()

        except Exception:
            LOGGER.exception(u'Image extraction failed for article %s.', self)
            return

    def fetch_content_image(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_IMAGE_DISABLED:
            LOGGER.info(u'Article video fetching disabled in configuration.')
            return

    def fetch_content_video(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_VIDEO_DISABLED:
            LOGGER.info(u'Article video fetching disabled in configuration.')
            return

    def needs_ghost_preparser(self):

        try:
            # TODO: this should be coming from the website, not the feed.
            return config.FEED_FETCH_GHOST_ENABLED and \
                self.feed.has_option(CONTENT_PREPARSING_NEEDS_GHOST)

        except AttributeError:
            # self.feed can be None…
            return False

    def likely_multipage_content(self):

        try:
            # TODO: this should be coming from the website, not the feed.
            return self.feed.has_option(CONTENT_FETCH_LIKELY_MULTIPAGE)

        except AttributeError:
            # self.feed can be None…
            return False

    def get_next_page_link(self, from_content):
        """ Try to find a “next page” link in the partial content given as
            parameter. """

        #soup = BeautifulSoup(from_content)

        return None

    def prepare_content_text(self, url=None):
        """ :param:`url` should be sinfon the case of multipage content. """

        if url is None:
            fetch_url = self.url

        else:
            fetch_url = url

        if self.needs_ghost_preparser():

            if ghost is None:
                LOGGER.warning(u'Ghost module is not available, content of '
                               u'article %s will be incomplete.', self)
                return requests.get(fetch_url,
                                    headers=REQUEST_BASE_HEADERS).content

                # The lock will raise an exception if it is already acquired.
                with global_ghost_lock:
                    GHOST_BROWSER.open(fetch_url)
                    page, resources = GHOST_BROWSER.wait_for_page_loaded()

                    #
                    # TODO: detect encoding!!
                    #
                    return page

        response = requests.get(fetch_url, headers=REQUEST_BASE_HEADERS)

        content_type = response.headers.get('content-type', u'unspecified')

        if content_type.startswith(u'text/html'):
            encoding = detect_encoding_from_requests_response(response)

            return response.content, encoding

        raise NotTextHtmlException(u"Content is not text/html "
                                   u"but %s." % content_type,
                                   response=response)

    def fetch_content_text_one_page(self, url=None):
        """ Internal function. Please do not call.
            Use :meth:`fetch_content_text` instead. """

        content, encoding = self.prepare_content_text(url=url)

        if not encoding:
            LOGGER.warning(u'Could not properly detect encoding for '
                           u'article %s, using utf-8 as fallback.', self)
            encoding = 'utf-8'

        if config.ARTICLE_FETCHING_DEBUG:
            try:
                LOGGER.info(u'————————— #%s HTML %s > %s —————————'
                            u'\n%s\n'
                            u'————————— end #%s HTML —————————',
                            self.id, content.__class__.__name__, encoding,
                            unicode(str(content), encoding), self.id)
            except:
                LOGGER.exception(u'Could not log source HTML content of '
                                 u'article %s.', self)

        STRAINER_EXTRACTOR = strainer.Strainer(parser='lxml', add_score=True)
        content = STRAINER_EXTRACTOR.feed(content, encoding=encoding)

        del STRAINER_EXTRACTOR
        gc.collect()

        # TODO: remove noscript blocks ?
        #
        # TODO: remove ads (after noscript because they
        #       seem to be buried down in them)
        #       eg. <noscript><a href="http://ad.doubleclick.net/jump/clickz.us/ # NOQA
        #       media/media-buying;page=article;artid=2280150;topcat=media;
        #       cat=media-buying;static=;sect=site;tag=measurement;pos=txt1;
        #       tile=8;sz=2x1;ord=123456789?" target="_blank"><img alt=""
        #       src="http://ad.doubleclick.net/ad/clickz.us/media/media-buying; # NOQA
        #       page=article;artid=2280150;topcat=media;cat=media-buying;
        #       static=;sect=site;tag=measurement;pos=txt1;tile=8;sz=2x1;
        #       ord=123456789?"/></a></noscript>

        if config.ARTICLE_FETCHING_DEBUG:
            try:
                LOGGER.info(u'————————— #%s CLEANED %s > %s —————————'
                            u'\n%s\n'
                            u'————————— end #%s CLEANED —————————',
                            self.id, content.__class__.__name__, encoding,
                            unicode(str(content), encoding), self.id)
            except:
                LOGGER.exception(u'Could not log cleaned HTML content of '
                                 u'article %s.', self)

        return content, encoding

    def fetch_content_text(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_TEXT_DISABLED:
            LOGGER.info(u'Article text fetching disabled in configuration.')
            return

        if self.content_type == CONTENT_TYPE_NONE:

            LOGGER.info(u'Parsing text content for article %s…', self)

            if self.likely_multipage_content():
                # If everything goes well, 'content' should be an utf-8
                # encoded strings. See the non-paginated version for details.
                content    = u''
                next_link  = self.url
                pages      = 0

                while next_link is not None:
                    pages       += 1
                    current_page, encoding = \
                        self.fetch_content_text_one_page(next_link)
                    content     += str(current_page)
                    next_link    = self.get_next_page_link(current_page)

                    if next_link:
                        self.pages_urls.append(next_link)

                LOGGER.info(u'Fetched %s page(s) for article %s.', pages, self)

            else:
                # first: http://www.crummy.com/software/BeautifulSoup/bs4/doc/#non-pretty-printing # NOQA
                # then: InvalidStringData: strings in documents must be valid UTF-8 (MongoEngine says) # NOQA
                content, encoding = self.fetch_content_text_one_page()

                # TRICK: `content` is a BS4 Tag, which cannot be
                # "automagically" converted by MongoEngine for
                # some unknown reason. There is also the famous:
                # TypeError: coercing to Unicode: need string or buffer, Tag found # NOQA
                #
                # Thus, we force it to unicode because this is the safe
                # pivot value in Python/MongoEngine, and MongoDB will
                # convert to an utf8 string internally.
                #
                # NOTE: We can be sure of the utf8 encoding, because
                # str(content) outputs utf8, this is documented in BS4.
                #
                self.content = unicode(str(content), 'utf-8')

            self.content_type = CONTENT_TYPE_HTML

            if self.content_error:
                statsd.gauge('articles.counts.content_errors', -1, delta=True)
                self.content_error = u''

            if commit:
                self.save()

            with statsd.pipeline() as spipe:
                spipe.gauge('articles.counts.empty', -1, delta=True)
                spipe.gauge('articles.counts.html', 1, delta=True)

        #
        # TODO: parse HTML links to find other 1flow articles and convert
        # the URLs to the versions we have in database. Thus, clicking on
        # these links should immediately display the 1flow version, from
        # where the user will be able to get to the public website if he
        # wants. NOTE: this is just the easy part of this idea ;-)
        #

        #
        # TODO: HTML word count here, before markdown ?
        #

        self.convert_to_markdown(force=force, commit=commit)

        LOGGER.info(u'Done parsing content for article %s.', self)

    def convert_to_markdown(self, force=False, commit=True):

        if config.ARTICLE_MARKDOWN_DISABLED:
            LOGGER.info(u'Article markdown convert disabled in '
                        u'configuration.')
            return

        if self.content_type == CONTENT_TYPE_MARKDOWN:
            if not force:
                LOGGER.info(u'Article %s already converted to Markdown.', self)
                return

            else:
                statsd.gauge('articles.counts.markdown', -1, delta=True)

        elif self.content_type != CONTENT_TYPE_HTML:
            LOGGER.warning(u'Article %s cannot be converted to Markdown, '
                           u'it is not currently HTML.', self)
            return

        LOGGER.info(u'Converting article %s to markdown…', self)

        md_converter = html2text.HTML2Text()

        # Set sane defaults. body_width > 0 breaks
        # some links by inserting \n inside them.
        #
        # MARKDOWN_V1 had [False, False, 78] (=default parameters)
        md_converter.unicode_snob = True
        md_converter.escape_snob  = True
        md_converter.body_width   = 0

        try:
            # NOTE: everything should stay in Unicode during this call.
            self.content = md_converter.handle(self.content)

        except Exception, e:
            statsd.gauge('articles.counts.content_errors', 1, delta=True)

            self.content_error = str(e)
            self.save()

            LOGGER.exception(u'Markdown convert failed for article %s.', self)
            return e

        self.content_type = CONTENT_TYPE_MARKDOWN

        if self.content_error:
            statsd.gauge('articles.counts.content_errors', -1, delta=True)
            self.content_error = u''

        #
        # TODO: word count here
        #
        self.postprocess_markdown_links(commit=False, force=force)

        if commit:
            self.save()

        with statsd.pipeline() as spipe:
            spipe.gauge('articles.counts.html', -1, delta=True)
            spipe.gauge('articles.counts.markdown', 1, delta=True)

        if config.ARTICLE_FETCHING_DEBUG:
            LOGGER.info(u'————————— #%s Markdown %s —————————'
                        u'\n%s\n'
                        u'————————— end #%s Markdown —————————',
                        self.id, self.content.__class__.__name__,
                        self.content, self.id)

    def postprocess_markdown_links(self, force=False,
                                   commit=True, test_only=False):
        """ Be sure we have no external links without the website part missing,
            else 1flow article internal links all point to 1flow, which makes
            them unusable.

            BTW, if the current article is an "old" markdown V1 one, try to
            repair its links by removing the `\n` inside them.
        """

        if self.content_type == CONTENT_TYPE_MARKDOWN:
            replace_newlines = False

        elif self.content_type == CONTENT_TYPE_MARKDOWN_V1:
            replace_newlines = True

        else:
            LOGGER.debug(u'Skipped non-Markdown article %s.', self)
            return

        website = WebSite.get_from_url(self.url)

        if website is None:
            LOGGER.warning(u'Article %s has no website??? Post-processing '
                           u'aborted.', self)
            return

        website_url = website.url

        def insert_website(link):
            if link.startswith(u'](/') or link.startswith(u'](.'):
                return u'](' + website_url + link[2:]

            else:
                return link

        # Use a copy during the operation to ensure we can start
        # again from scratch in a future call if anything goes wrong.
        content = self.content

        if replace_newlines:
            for repl_src in re.findall(ur'[[][^]]+[]][(]', content):

                # In link text, we replace by a space.
                repl_dst = repl_src.replace(u'\n', u' ')
                content  = content.replace(repl_src, repl_dst)

        for repl_src in re.findall(ur'[]][(][^)]+[)]', content):

            if replace_newlines:
                # In link URLs, we just cut out newlines.
                repl_dst = repl_src.replace(u'\n', u'')
            else:
                repl_dst = repl_src

            repl_dst = clean_url(insert_website(repl_dst))
            content  = content.replace(repl_src, repl_dst)

        if test_only:
            return content

        else:
            # Everything went OK. Put back the content where it belongs.
            self.content = content

            if replace_newlines:
                self.content_type = CONTENT_TYPE_MARKDOWN

            self.find_image(commit=False, force=force)

            if commit:
                self.save()

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        article = document

        if created:

            # Some articles are created "already orphaned" or duplicates.
            # In the archive database this is more immediate than looking
            # up the database name.
            if not (article.orphaned or article.duplicate_of):
                if article._db_name != settings.MONGODB_NAME_ARCHIVE:
                    article_post_create_task.delay(article.id)

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        if not self.slug:
            self.slug = slugify(self.title)
            self.save()

            with statsd.pipeline() as spipe:
                spipe.gauge('articles.counts.total', 1, delta=True)
                spipe.gauge('articles.counts.empty', 1, delta=True)

        post_absolutize_chain = tasks_chain(
            # HEADS UP: both subtasks are immutable, we just
            # want the group to run *after* the absolutization.
            article_fetch_content.si(self.id),
            article_postprocess_original_data.si(self.id),
        )

        # Randomize the absolutization a little, to avoid
        # http://dev.1flow.net/development/1flow-dev-alternate/group/1243/
        # as much as possible. This is not yet a full-featured solution,
        # but it's completed by the `fetch_limit` thing.
        #
        # Absolutization conditions everything else. If it doesn't succeed:
        #   - no bother trying to post-process author data for example,
        #     because we need the absolutized website domain to make
        #     authors unique and worthfull.
        #   - no bother fetching content: it uses the same mechanisms as
        #     absolutize_url(), and will probably fail the same way.
        #
        # Thus, we link the post_absolutize_chain as a callback. It will
        # be run only if absolutization succeeds. Thanks, celery :-)
        #
        article_absolutize_url.apply_async((self.id, ),
                                           countdown=randrange(5),
                                           link=post_absolutize_chain)

        #
        # TODO: create short_url
        #

        # TODO: remove_useless_blocks, eg:
        #       <p><a href="http://addthis.com/bookmark.php?v=250">
        #       <img src="http://cache.addthis.com/cachefly/static/btn/
        #       v2/lg-share-en.gif" alt="Bookmark and Share" /></a></p>
        #
        #       (in 51d6a1594adc895fd21c3475, see Notebook)
        #
        # TODO: link_replace (by our short_url_link for click statistics)
        # TODO: images_fetch
        #       eg. handle <img alt="2013-05-17_0009.jpg"
        #           data-lazyload-src="http://www.vcsphoto.com/blog/wp-content/uploads/2013/05/2013-05-17_0009.jpg" # NOQA
        #           src="http://www.vcsphoto.com/blog/wp-content/themes/prophoto4/images/blank.gif" # NOQA
        #           height="1198" sidth="900"/>
        #
        # TODO: authors_fetch
        # TODO: publishers_fetch
        # TODO: duplicates_find (content wise, not URL wise)
        #

        return


class OriginalData(Document, DocumentHelperMixin):

    article = ReferenceField('Article', unique=True,
                             reverse_delete_rule=CASCADE)

    # This should go away soon, after a full re-parsing.
    google_reader = StringField()
    feedparser    = StringField()

    # These are set to True to avoid endless re-processing.
    google_reader_processed = BooleanField(default=False)
    feedparser_processed    = BooleanField(default=False)

    meta = {
        'db_alias': 'archive',
    }

    @property
    def feedparser_hydrated(self):
        """ XXX: should disappear when feedparser_data is useless. """

        if self.feedparser:
            return ast.literal_eval(re.sub(r'time.struct_time\([^)]+\)',
                                    '""', self.feedparser))

        return None

    @property
    def google_reader_hydrated(self):
        """ XXX: should disappear when google_reader_data is useless. """

        if self.google_reader:
            return ast.literal_eval(self.google_reader)

        return None


READ_BOOKMARK_TYPE_CHOICES = (
    (u'U', _(u'Undefined')),
    (u'A', _(u'This afternoon')),
    (u'W', _(u'This week-end')),
)


@task(name='Read.post_create', queue='high')
def read_post_create_task(read_id, *args, **kwargs):

    read = Read.objects.get(id=read_id)
    return read.post_create_task(*args, **kwargs)


class Read(Document, DocumentHelperMixin):
    user = ReferenceField('User', reverse_delete_rule=CASCADE)
    article = ReferenceField('Article', unique_with='user',
                             reverse_delete_rule=CASCADE)

    subscriptions = ListField(ReferenceField(Subscription))

    date_created = DateTimeField(default=now)

    is_read   = BooleanField(help_text=_(u'The Owner has read the content or '
                             u'has manually marked it as such.'),
                             default=False)
    date_read = DateTimeField()

    is_auto_read   = BooleanField(help_text=_(u'The system has automatically '
                                  u'marked it as read, in respect of a system '
                                  u'rule or a user preference.'), default=False)
    date_auto_read = DateTimeField()

    # NOTE: is_starred has no default, because we use True
    #       as "I like it" and False as "I don't like it".
    is_starred   = BooleanField(help_text=_(u'The owner has starred the '
                                u'content, signifying he/she loves it or '
                                u'that it is much of interest for him/her.'))
    date_starred = DateTimeField()

    is_bookmarked   = BooleanField(help_text=_(u'This content is marked to '
                                   u'be read later. When, depends on the '
                                   u'`.bookmark_type` attribute.'),
                                   default=False)
    date_bookmarked = DateTimeField()
    bookmark_type   = StringField(max_length=1, default=u'U',
                                  choices=READ_BOOKMARK_TYPE_CHOICES)

    is_fact   = BooleanField(help_text=_(u'Qualifies a time-dependant fact.'),
                             default=False)
    date_fact = DateTimeField()

    is_quote   = BooleanField(help_text=_(u'Qualifies someone’s words, '
                              u'thoughts or intentions.'), default=False)
    date_quote = DateTimeField()

    is_number   = BooleanField(help_text=_(u'Qualifies explicitely quantized '
                               u'data.'), default=False)
    date_number = DateTimeField()

    is_analysis   = BooleanField(help_text=_(u'Qualifies in-depth analysis, '
                                 u'studies or research publications.'),
                                 default=False)
    date_analysis = DateTimeField()

    is_prospective   = BooleanField(help_text=_(u'Qualifies things that want'
                                    u' to watch, that will happen or not.'),
                                    default=False)
    date_prospective = DateTimeField()

    is_knowhow   = BooleanField(help_text=_(u'Qualifies anything about '
                                u'How-to-do things and profession '
                                u'best-practices.'), default=False)
    date_knowhow = DateTimeField()

    is_rules   = BooleanField(help_text=_(u'Qualifies anything about laws, '
                              u'governments/public regulations.'),
                              default=False)
    date_rules = DateTimeField()

    is_knowledge   = BooleanField(help_text=_(u'Qualifies anything that the '
                                  u'owner wants to retain as a “must know”, '
                                  u'whatever the context.'), default=False)
    date_knowledge = DateTimeField()
    knowledge_type = StringField(max_length=2)

    is_fun   = BooleanField(help_text=_(u'Qualifies anything that makes you '
                            u'laugh out loud.'), default=False)
    date_fun = DateTimeField()

    # TODO: convert to UserTag to use ReferenceField and reverse_delete_rule.
    tags = ListField(GenericReferenceField(),
                     default=list, verbose_name=_(u'Tags'),
                     help_text=_(u'User set of tags for this read.'))

    # This will be set to Article.default_rating
    # until the user sets it manually.
    rating = FloatField()

    # For free users, fix a limit ?
    #meta = {'max_documents': 1000, 'max_size': 2000000}

    status_data = {

        'is_read': {
            'list_name':    _p(u'past participle, plural', u'read'),
            'view_name':    u'read',
            'list_url':     _(ur'^read/read/$'),
            'do_title':     _(u'Mark as read'),
            'undo_title':   _(u'Mark as unread'),
            'do_label' :    _(u'Mark read'),
            'undo_label':   _(u'Mark unread'),
            'status_label': _p(u'adjective', u'read'),
            'do_icon':      _p(u'awesome-font icon name', u'check-empty'),
            'undo_icon':    _p(u'awesome-font icon name', u'check'),
        },

        'is_starred': {
            'list_name':    _(u'starred'),
            'view_name':    u'starred',
            'list_url':     _(ur'^read/starred/$'),
            'do_title':     _(u'Star (add to favorites)'),
            'undo_title':   _(u'Remove from starred/favorites'),
            'do_label' :    _p(u'verb', u'Star'),
            'undo_label':   _(u'Unstar'),
            'status_label': _(u'starred'),
            'do_icon':      _p(u'awesome-font icon name', u'star-empty'),
            'undo_icon':    _p(u'awesome-font icon name', u'star'),
        },

        'is_bookmarked': {
            'list_name':    _(u'later'),
            'view_name':    u'later',
            'list_url':     _(ur'^read/later/$'),
            'do_title':     _(u'Keep for reading later'),
            'undo_title':   _(u'Remove from reading list'),
            'do_label':     _(u'Read later'),
            'undo_label':   _(u'Do not read later'),
            'status_label': _(u'kept for later'),
            'do_icon':      _p(u'awesome-font icon name', u'bookmark-empty'),
            'undo_icon':    _p(u'awesome-font icon name', u'bookmark'),
        },

        'is_fact': {
            'list_name':    _(u'facts'),
            'view_name':    u'facts',
            'list_url':     _(ur'^read/facts/$'),
            'do_title':     _(u'Mark as fact / important event'),
            'undo_title':   _(u'Remove from facts / important events'),
            'status_title': _(u'This article contains one or '
                              u'more important facts'),
            'do_label' :    _(u'Mark as fact'),
            'undo_label':   _(u'Unmark fact'),
            'status_label': _(u'fact'),
            'do_icon':      _p(u'awesome-font icon name', u'circle-blank'),
            'undo_icon':    _p(u'awesome-font icon name', u'bullseye'),
        },

        'is_number': {
            'list_name':    _(u'numbers'),
            'view_name':    u'numbers',
            'list_url':     _(ur'^read/numbers/$'),
            'do_title':     _(u'Mark as valuable number'),
            'undo_title':   _(u'Remove from valuable numbers'),
            'status_title': _(u'This article contains quantified '
                              u'numbers for a watch.'),
            'do_label' :    _(u'Mark as number'),
            'undo_label':   _(u'Unmark number'),
            'status_label': _(u'number'),
            'do_icon':      _p(u'awesome-font icon name', u'bar-chart'),
            'undo_icon':    _p(u'awesome-font icon name',
                               u'bar-chart icon-flip-horizontal'),
            'status_icon':  _p(u'awesome-font icon name', u'bar-chart'),
            #'undo_icon_stack': True,
        },

        'is_analysis': {
            'list_name':    _(u'analysis'),
            'view_name':    u'analysis',
            'list_url':     _(ur'^read/analysis/$'),
            'do_title':     _(u'Mark as analysis / study / research'),
            'undo_title':   _(u'Unmark analysis / study / research'),
            'status_title': _(u'This article contains an analysis, '
                              u'an in-depth study or a research '
                              u'publication.'),
            'do_label' :    _(u'Mark as analysis'),
            'undo_label':   _(u'Unmark analysis'),
            'status_label': _(u'analysis'),
            'do_icon':      _p(u'awesome-font icon name', u'beaker'),
            'undo_icon':    _p(u'awesome-font icon name',
                               u'beaker icon-rotate-90'),
            'status_icon':  _p(u'awesome-font icon name', u'beaker'),
        },

        'is_quote': {
            'list_name':    _(u'quotes'),
            'view_name':    u'quotes',
            'list_url':     _(ur'^read/quotes/$'),
            'do_title':     _(u'Mark as containing quote(s) from people '
                              u'you consider important'),
            'undo_title':   _(u'Unmark as containing quotes '
                              u'(people are not famous anymore?)'),
            'status_title': _(u'This article contains one or more quote '
                              u'from people you care about.'),
            'do_label' :    _(u'Mark as quote'),
            'undo_label':   _(u'Unmark quote'),
            'status_label': _p(u'noun', u'quote'),
            'do_icon':      _p(u'awesome-font icon name',
                               u'quote-left icon-flip-vertical'),
            'undo_icon':    _p(u'awesome-font icon name', u'quote-right'),
            'status_icon':  _p(u'awesome-font icon name',
                               u'quote-left icon-flip-vertical'),
        },

        'is_prospective': {
            'list_name':    _(u'prospective'),
            'view_name':    u'prospective',
            'list_url':     _(ur'^read/prospective/$'),
            'do_title':     _(u'Mark as prospective-related content'),
            'undo_title':   _(u'Unmark as prospective-related content'),
            'status_title': _(u'This article contains prospective element(s) '
                              u'or must-remember hypothesis.'),
            'do_label' :    _(u'Mark as prospective'),
            'undo_label':   _(u'Unmark prospective'),
            'status_label': _(u'prospective'),
            'do_icon':      _p(u'awesome-font icon name', u'lightbulb'),
            'undo_icon':    _p(u'awesome-font icon name',
                               u'lightbulb icon-rotate-180'),
            'status_icon':  _p(u'awesome-font icon name', u'lightbulb'),
            #'undo_icon_stack': True,
        },

        'is_rules': {
            'list_name':    _(u'rules'),
            'view_name':    u'rules',
            'list_url':     _(ur'^read/rules/$'),
            'do_title':     _(u'Mark as legal/regulations-related content'),
            'undo_title':   _(u'Unmark as legal content (overriden laws?)'),
            'status_title': _(u'This article contains regulations/'
                              u'law/rules element(s)'),
            'do_label' :    _(u'Mark as law/regul.'),
            'undo_label':   _(u'Unmark law/regul.'),
            'status_label': _(u'regulations'),
            'do_icon':      _p(u'awesome-font icon name',
                               u'legal icon-flip-horizontal'),
            'undo_icon':    _p(u'awesome-font icon name',
                               u'legal icon-rotate-180'),
            'status_icon':  _p(u'awesome-font icon name',
                               u'legal icon-flip-horizontal'),
        },

        'is_knowhow': {
            'list_name':    _(u'best-practices'),
            # WARNING: there is a '_' in the view name, and a '-' in the URL.
            'view_name':    u'best_practices',
            'list_url':     _(ur'^read/best-practices/$'),
            'do_title':     _(u'Mark as best-practices / state of art '
                              u'content'),
            'undo_title':   _(u'Unmark as best-practices / state of art '
                              u'(has it become obsolete?)'),
            'status_title': _(u'This article contains best-practices / '
                              u' state of art element(s).'),
            'do_label' :    _(u'Mark as best-practice'),
            'undo_label':   _(u'Unmark best-practice'),
            'status_label': _p(u'noun', u'know-how'),
            'do_icon':      _p(u'awesome-font icon name', u'trophy'),
            'undo_icon':    _p(u'awesome-font icon name',
                               u'trophy icon-flip-vertical'),
            'status_icon':  _p(u'awesome-font icon name', u'trophy'),
        },

        'is_knowledge': {
            'list_name':    _(u'knowlegde'),
            'view_name':    u'knowledge',
            'list_url':     _(ur'^read/knowledge/$'),
            'do_title':     _(u'Mark as a valuable piece of '
                              u'knowlegde for your brain or life'),
            'undo_title':   _(u'Unmark as neuronal-exciting '
                              u'element(s)'),
            'status_title': _(u'This article contains a valuable '
                              u'piece of knowlegde.'),
            'do_label' :    _(u'Mark as Knowledge'),
            'undo_label':   _(u'Unmark knowlegde'),
            'status_label': _(u'knowledge'),
            'do_icon':      _p(u'awesome-font icon name', u'globe'),
            'undo_icon':    _p(u'awesome-font icon name',
                               u'globe icon-rotate-180'),
            'status_icon':  _p(u'awesome-font icon name', u'globe'),
        },

        'is_fun': {
            'list_name':    _(u'funbox'),
            'view_name':    u'fun',
            'list_url':     _(ur'^read/fun/$'),
            'do_title':     _(u'Mark as being fun. Are you sure?'),
            'undo_title':   _(u'Not fun anymore, sadly.'),
            'status_title': _(u'OMG, this thing is sooooooooo fun! LMAO!'),
            'do_label' :    _(u'Mark as fun'),
            'undo_label':   _(u'Mark as boring'),
            'status_label': _(u'fun'),
            'do_icon':      _p(u'awesome-font icon name', u'smile'),
            'undo_icon':    _p(u'awesome-font icon name', u'frown'),
            'status_icon':  _p(u'awesome-font icon name', u'smile'),
        },
    }

    meta = {
        'indexes': ['user', ]
    }

    @classmethod
    def get_status_attributes(cls):
        try:
            return cls._status_attributes_cache

        except AttributeError:
            cls._status_attributes_cache = [fname for fname, field
                                            in cls._fields.items()
                                            if fname.startswith('is_')
                                            and isinstance(field,
                                                           BooleanField)]

            return cls._status_attributes_cache

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        read = document

        if created:
            if read._db_name != settings.MONGODB_NAME_ARCHIVE:
                read_post_create_task.delay(read.id)

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        self.rating = self.article.default_rating

        self.set_subscriptions(commit=False)

        self.save()

    def __unicode__(self):
        return _(u'{0}∞{1} (#{2}) {3} {4}').format(
            self.user, self.article, self.id,
            _p(u'adjective', u'read')
                if self.is_read else _p(u'adjective', u'unread'), self.rating)

    def set_subscriptions(self, commit=True):
        user_feeds    = [sub.feed for sub in self.user.subscriptions]
        article_feeds = [feed for feed in self.article.feeds
                         if feed in user_feeds]
        self.subscriptions = list(Subscription.objects(feed__in=article_feeds))

        if commit:
            self.save()

        return self.subscriptions

    @property
    def title(self):

        article = self.article
        feed    = article.feed

        if feed:
            source = _(u' ({feed})').format(feed=feed.name)

        else:
            source = u''

        return _(u'{title}{source}').format(title=article.title,
                                            source=source)

    def remove_tags(self, tags=[]):
        """ If the user remove his own tags from a Read, it will get back the
            default tags from the article it comes from. """

        if tags:
            for tag in Tag.get_tags_set(tags, origin=self):
                self.update(pull__tags=tag)

            self.safe_reload()

        if self.tags == []:
            self.tags = self.article.tags.copy()
            self.save()

    def add_tags(self, tags):

        for tag in Tag.get_tags_set(tags, origin=self):
            self.update(add_to_set__tags=tag)

        self.safe_reload()


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Comment


class Comment(Document, DocumentHelperMixin):
    TYPE_COMMENT = 1
    TYPE_INSIGHT = 10
    TYPE_ANALYSIS = 20
    TYPE_SYNTHESIS = 30

    VISIBILITY_PUBLIC  = 1
    VISIBILITY_GROUP   = 10
    VISIBILITY_PRIVATE = 20

    nature = IntField(default=TYPE_COMMENT)
    visibility = IntField(default=VISIBILITY_PUBLIC)

    is_synthesis = BooleanField()
    is_analysis = BooleanField()
    content = StringField()

    feedback = EmbeddedDocumentField(FeedbackDocument)

    # We don't comment reads. We comment articles.
    #read = ReferenceField('Read')
    article = ReferenceField('Article', reverse_delete_rule=CASCADE)

    # Thus, we must store
    user = ReferenceField('User', reverse_delete_rule=CASCADE)

    in_reply_to = ReferenceField('Comment', reverse_delete_rule=NULLIFY)

    # @property
    # def type(self):
    #     return self.internal_type
    # @type.setter
    # def type(self, type):
    #     parent_type = comment.in_reply_to.type
    #     if parent_type is not None:
    #         if parent_type == Comment.TYPE_COMMENT:
    #             if type == Comment.TYPE_COMMENT:
    #                 self.internal_type = Comment.TYPE_COMMENT
    #             raise ValueError('Cannot synthetize a comment')
    #             return Comment.TYPE_COMMENT


# •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Source


class Source(Document, DocumentHelperMixin):
    """ The "original source" for similar articles: they have different authors,
        different contents, but all refer to the same information, which can
        come from the same article on the net (or radio, etc).

        Eg:
            - article1 on Le Figaro
            - article2 on Liberation
            - both refer to the same AFP news, but have different content.

    """
    type    = StringField()
    uri     = URLField(unique=True)
    name    = StringField()
    authors = ListField(ReferenceField('User', reverse_delete_rule=PULL))
    slug    = StringField()


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• End classes


connect_mongoengine_signals(globals())
