# -*- coding: utf-8 -*-
u"""
Copyright 2012-2014 Olivier Cortès <oc@1flow.io>.

This file is part of the 1flow project.

1flow is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

1flow is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

import os
import six
import time
import redis
import urllib2
import charade
import logging
import importlib

try:
    import blinker
except:
    blinker = None  # NOQA

from celery import task
from bs4 import BeautifulSoup

from mongoengine import Document, signals

from django.conf import settings
from django import db
from django.db import models, DatabaseError, InterfaceError  # , transaction
from django.template import Context

from djangojs.context_serializer import ContextSerializer
from oneflow import VERSION
from .dateutils import ftstamp

LOGGER = logging.getLogger(__name__)

REDIS = redis.StrictRedis(host=settings.REDIS_HOST,
                          port=settings.REDIS_PORT,
                          db=settings.REDIS_DB)

boolcast = {
    'True': True,
    'False': False,
    'None': None,
    # The real None is needed in case of a non-existing key.
    None: None
}


def full_version():
    u""" Return full version, with Git informations, if relevant.

    .. note:: *relevant* means “not on master branch”.
    """

    try:
        import pygit2

    except ImportError:
        LOGGER.error(u'PyGit2 not importable, version string '
                     u'could be incomplete!')

        return VERSION

    current_working_directory = os.getcwd()
    repository_path = pygit2.discover_repository(current_working_directory)
    repository = pygit2.Repository(repository_path)

    head = repository.head

    commit = repository[head.target]

    # http://stackoverflow.com/a/21015031/654755
    commit_rev = commit.hex[:7]

    if '/develop' in head.name:
        return u'1flow v{0}+{1} (develop)'.format(VERSION, commit_rev)

    if '/feature/' in head.name:
        return u'1flow v{0}+{1} (feat. {2})'.format(VERSION, commit_rev,
                                                    head.name.rsplit('/', 1)[1])

    if 'master' in head.name:
        return u'1flow v{0} (master)'.format(VERSION)

    else:
        return u'1flow v{0}+{1} (unknown)'.format(VERSION, commit_rev)


# —————————————————————————————————————————————————————————————————— Decorators


def register_task_method(klass, meth, module_globals,
                         queue=None, default_retry_delay=None):
    """ A simple wrapper to register methods as celery tasks.

    Necessary because celery tasks-as-methods don't work as expected,
    and we don't want to create to create function tasks because it
    makes no sense in our OO context.


    :param klass: a class where the :param:`meth` method belongs to.
    :param meth: the method that will run as the task.
    :param queue: the celery queue the method will run in.
        Defaults to ``medium``.

    .. note:: we gave a try at :mod:`method_decorator` to implement
        this as a method decorator, but it didn't work with decorator
        arguments, it's much more complicated than it seems. Thus this
        simpler function, that requires a little more typing in the
        modules, but just works.
    """
    class_name  = klass.__name__
    method_name = meth.im_func.func_name

    if method_name.lower().startswith(class_name.lower()):
        # +1 to remove the ClassName_ trailing underscore.
        method_name = method_name[len(class_name) + 1:]

    if method_name.endswith(u'_method'):
        method_name = method_name[:-7]

    task_name = u'{0}.{1}'.format(class_name, method_name)

    if task_name.endswith(u'_task'):
        # The method name ends with “_class” to signify it's
        # not a standard method. It's not mandatory though.

        exported_name = task_name.lower().replace('.', '_')

        # The celery name is “User.post_create” only, though.
        task_name = task_name[:-5]

    else:
        # We add the suffix to the local name, to make explicit
        # it's a task if the local module is inspected.
        exported_name = u'{0}_task'.format(
            task_name.lower().replace('.', '_'))

    #
    # HEADS UP: issubclass(…, models.Model) includes PolymorphicModel,
    #           and will work as expected as long as .objects is a
    #           PolymorphicManager().
    #
    if issubclass(klass, models.Model):

        @task(name=task_name, queue=queue, bind=True,
              default_retry_delay=default_retry_delay)
        def task_func(self, object_pk, *args, **kwargs):

            stop_chain_on_false = kwargs.pop('stop_chain_on_false', False)

            try:
                # with transaction.atomic():
                objekt = klass.objects.get(pk=object_pk)

                result = getattr(objekt, method_name)(*args, **kwargs)

            except klass.DoesNotExist, exc:
                # The transaction was not commited, the task went too fast.
                LOGGER.warning(u'Instance does not exist prior to running '
                               u'task %s on %s #%s; Retrying.', method_name,
                               klass._meta.model.__name__,
                               object_pk)

                module_globals[exported_name].retry(exc=exc)

            except (InterfaceError, DatabaseError), exc:
                # Why closing the connection ?
                # http://blog.tryolabs.com/2014/02/12/long-time-running-process-and-django-orm/  # NOQA

                LOGGER.warning(u'Database error while running %s on %s #%s; '
                               u'closing connection and retrying the task.',
                               method_name, klass._meta.model.__name__,
                               object_pk)

                db.connection.close()
                module_globals[exported_name].retry(exc=exc)

            except SystemExit:
                # Stop flooding sentry with that.
                pass

            except:
                LOGGER.exception(u'exception while running %s on %s #%s',
                                 method_name, klass._meta.model.__name__,
                                 object_pk)

            else:
                if stop_chain_on_false and result is False:
                    # Abort chain in the middle on a condition.
                    # http://stackoverflow.com/a/21106596/654755
                    self.request.callbacks[:] = []

                return result
    else:

        @task(name=task_name, queue=queue,
              default_retry_delay=default_retry_delay)
        def task_func(object_id, *args, **kwargs):

            try:
                objekt = klass.objects.get(id=object_id)

                return getattr(objekt, method_name)(*args, **kwargs)
            except:
                LOGGER.exception(u'exception while running %s on %s #%s',
                                 method_name, klass.__name__, object_id)

    # Export the new task in the current module.
    module_globals[exported_name] = task_func

    # Make it available for celery to import it.
    module_globals['__all__'].append(exported_name)

    # if __debug__ and settings.DEBUG:
    #     LOGGER.debug(u'Registered “%s” as Celery task “%s”.',
    #                  exported_name, task_name)


# ——————————————————————————————————————————————————————————————— utils/helpers


def connect_mongoengine_signals(module_globals):
    """ Automatically connect handlers to signals.

    Given they follow the name pattern
    ``signal_<signal_name>_handler()``.

    See https://mongoengine-odm.readthedocs.org/en/latest/guide/signals.html#overview # NOQA
    for a list of valid signal names.
    """

    if blinker is None:
        LOGGER.error('blinker module is not installed, '
                     'cannot connect mongoengine signals!')
        return

    if __debug__:
        connected = 0

    for key, potential_class in module_globals.items():

        # TODO: use ReferenceDocument and other Mongo classes if appropriate?
        try:
            look_for_handlers = issubclass(potential_class, Document)

        except:
            # potential_class is definitely not a class/document ;-)
            continue

        if look_for_handlers:
            for signal_name in ('pre_init', 'post_init', 'pre_save',
                                'pre_save_post_validation', 'post_save',
                                'pre_delete', 'post_delete',
                                'pre_bulk_insert', 'post_bulk_insert'):
                handler_name = 'signal_{0}_handler'.format(signal_name)
                if hasattr(potential_class, handler_name):
                    getattr(signals, signal_name).connect(
                        getattr(potential_class, handler_name),
                        sender=potential_class)
                    if __debug__:
                        connected += 1

    # if __debug__ and settings.DEBUG and connected:
    #    LOGGER.debug('Connected %s signal handlers to MongoEngine senders.',
    #                 connected)


def request_context_celery(request, *args, **kwargs):
    """ Create a standard Django :class:`Context`, and add useful things.

    From the current RequestContext, without all the fudge. Eg.::

    - ``request.user`` becomes ``context['user']``
    - ``request.session`` becomes ``context['session']``
    - ``request.META`` becomes ``context['meta']`` (lowercase) and
      gets cleaned from non-pickable values (see later).
    - ``request.LANGUAGE_CODE`` becomes ``context['language_code']``
      if it is available in the request, else it is set to ``None``.

    With :param:`args` and :param:`kwargs`, you can pass anything you
    want to be added to the context, these arguments will be passed
    verbatim to the :class:`Context` constructor.

    This Context instance is specialy forged for celery tasks,
    and should not make them crash with :class:`PicklingError`.
    In case it still does, you can mark ``HttpRequest.META`` keys to
    be removed from the context via the ``CELERY_CONTEXT_EXPUNGE_META``
    setting directive. Defaults keys purged are::

        ('wsgi.errors', 'wsgi.input', 'wsgi.file_wrapper',
         'gunicorn.socket', )

    You can specify non-existing keys, they will just be skipped.

    .. note:: the default keys will *always* be purged. You do not need
        to add them to ``CELERY_CONTEXT_EXPUNGE_META``. Said another way
        there is currently no way to avoid expunging them, and this is
        intentional.

    """

    # TODO: i18n
    context = Context(*args, **kwargs)

    meta = request.META.copy()

    expunge_keys = getattr(settings, 'CELERY_CONTEXT_EXPUNGE_META', ())

    # We always get the basics for free.
    expunge_keys += ('wsgi.errors', 'wsgi.input', 'wsgi.file_wrapper',
                     'gunicorn.socket', )

    for key in expunge_keys:
        try:
            del meta[key]

        except KeyError:
            pass

    context.update({
                   'meta': meta,
                   'session_key': request.session.session_key,
                   'user_id': request.user.id,
                   })

    try:
        context.update({'language_code': request.LANGUAGE_CODE})

    except:
        context.update({'language_code': None})

    return context


def detect_encoding_from_requests_response(response, meta=False, deep=False):
    """ :param:`response` beiing a :module:`requests` response, this function
        will try to detect the encoding as much as possible. Fist, the "normal"
        response encoding will be tried, else the headers will be parsed, and
        finally the ``<head>`` of the ``<html>`` content will be parsed. If
        nothing succeeds, we will rely on :module:`charade` to guess from the
        content.

        .. todo:: we have to check if content-type is HTML before parsing the
            headers. For now you should use this function only on responses
            which you are sure they will contain HTML.
    """

    if getattr(response, 'encoding', None) and not (meta or deep):

        if settings.DEBUG:
            LOGGER.debug(u'detect_encoding_from_requests_response(): '
                         u'detected %s via `requests` module.',
                         response.encoding)

        return response.encoding

    # If requests doesn't bring us any encoding, we have 3 fallback options:
    # - inspect the server headers ourselves (fast, but rarely they exist,
    #   and sometimes they are wrong),
    # - look up the META tags (fast, but sometimes the tag is not
    #   present or is wrong too),
    # - detect it via `charade` (slow, but gives good results).

    encoding = response.headers.get(
        'content-type', None).lower().split('charset=')[-1]

    # If found and no deeper search is wanted, return it.
    if encoding is not None and not (meta or deep):

        if settings.DEBUG:
            LOGGER.debug(u'detect_encoding_from_requests_response(): '
                         u'detected %s via server headers.',
                         encoding)

        return encoding

    # HTTP headers don't contain any encoding.
    # Search in page head, then try to detect from data.

    html_content = BeautifulSoup(response.content, 'lxml')

    for meta_header in html_content.head.findAll('meta'):
        for attribute, value in meta_header.attrs.items():
            if attribute.lower() == 'http-equiv':
                if value.lower() == 'content-type':
                    content  = meta_header.attrs.get('content')
                    encoding = content.lower().split('charset=')[-1]
                    break

    # If no deeper search is wanted, return it now.
    if encoding not in ('text/html', '') and not deep:

        if settings.DEBUG:
            LOGGER.debug(u'detect_encoding_from_requests_response(): '
                         u'detected %s via HTML meta tags.',
                         encoding)

        return encoding

    try:
        charade_result = charade.detect(response)

    except:
        pass

    else:
        if settings.DEBUG:
            LOGGER.debug(u'detect_encoding_from_requests_response(): '
                         u'detected %s via `charade` module (with %s%% '
                         u'confidence).',
                         charade_result['encoding'],
                         charade_result['confidence'])
        return charade_result['encoding']

    LOGGER.critical('detect_encoding_from_requests_response(): could not '
                    u'detect encoding of %s via all test methods.', response)
    return None


def eventually_deferred(thing):
    """ Try to import ``thing``'s parent and return a runtime reference to
        ``thing`` if it's callable. ``parent.parent`` will be tried too,
        but no more. """

    if thing is None:
        return thing

    if callable(thing):
        return thing

    if isinstance(thing, str) or isinstance(thing, unicode):
        try:
            module_name, callable_name = thing.rsplit(u'.', 1)

        except ValueError:
            # 'thing' is a simple string with no special meaning.
            return thing

        else:
            try:
                module = importlib.import_module(module_name)

            except ImportError, e:
                try:
                    # Perhaps we failed to import 'module.submodule.MyClass'.
                    # Try one level up.
                    sup_module_name, class_name = module_name.rsplit(u'.', 1)

                except ValueError:
                    # There is a real import problem,
                    # raise the original exception.
                    raise e

                else:
                    # Any exception at this level is bubbled directly.
                    # If we were able to `rsplit('.')` 2 times, we are
                    # most probably dealing with a real Python module.
                    # Any error at import time must be known.
                    sup_module = importlib.import_module(module_name)

                    candidate = getattr(getattr(sup_module, class_name),
                                        callable_name)

                    if callable(candidate):
                        return candidate

                    else:
                        raise RuntimeError(u'Cannot use "%s" as deferred '
                                           u'default value, it is not '
                                           u'callable.' % thing)

            else:
                candidate = getattr(module, callable_name)

                if callable(candidate):
                    return candidate

                else:
                    raise RuntimeError(u'Cannot use "%s" as deferred default '
                                       u'value, it is not callable.' % thing)

    return thing


# •••••••••••••••••••••••••••••••••••••••••••••••••••••••• utils/helper classes

class ro_classproperty(object):
    """ http://stackoverflow.com/q/5189699/654755 is my friend, and
        more particularly http://stackoverflow.com/a/5192374/654755 which
        fits perfectly for R/O part. """

    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        return self.f(owner)


class JsContextSerializer(ContextSerializer):
    """ This class should probably move into sparks some day. """

    def process_backends(self, backends, data):
        """ Just force social_auth's backend `LazyDict()` to be converted.

        To a dict for the JSON serialization to work properly. """

        data['backends'] = dict(six.iteritems(backends))

    def handle_user(self, data):
        """ We just add the user ID to everything already gathered by Django.JS
            user serializer. """

        super(JsContextSerializer, self).handle_user(data)

        data['user']['id'] = self.request.user.id


class StopProcessingException(Exception):
    """ Exception to notify a caller that it should just stop its processing
        because for some reason it would be useless or obsolete to continue. """
    pass


class AlreadyLockedException(Exception):
    """ Simple Exception to notify a caller that uses RedisExpiringLock
        as a context manager that the lock could not be taken. """
    pass


class RedisExpiringLock(object):
    """ Simple lock for multi-hosted machines workers (eg. celery).
        Implemented via REDIS from http://redis.io/commands/set

        At start it was implemented via Memcache, but it doesn't work on
        development machines where cache is the DummyCache implementation.

        For commodity, if the instance has a ``fetch_interval`` attribute,
        it will be taken as the default ``expire_time`` value. If not and
        no ``expire_time`` argument is present, 3600 will be used to avoid
        persistent locks related problems.

        .. note:: **this lock can be re-entrant**: just give an
            unique :param:`lock_value` (eg. ``uuid.uuid4().hex``, to
            name only this one…), and pass it as the only argument to
            :meth:`acquire`. If the argument is equal to the lock value
            then the acquire method will return ``True``. This is a poor
            man's implementation, but should work.
    """

    REDIS     = None
    key_base  = 'rxl'
    exc_class = AlreadyLockedException

    def __init__(self, instance, lock_name=None,
                 lock_value=None, expire_time=None):

        if isinstance(instance, str):
            self.lock_id = '%s:str:%s:%s' % (self.key_base, instance,
                                             lock_name or 'giant')
            self.expire_time = expire_time or 3600

        else:
            self.lock_id = '%s:%s:%s:%s' % (
                self.key_base,
                instance.__class__.__name__,
                instance.id if hasattr(instance, 'id') else instance.pk,
                lock_name or 'giant')

            self.expire_time = expire_time or getattr(instance,
                                                      'fetch_interval',
                                                      3600)

        self.lock_value  = ('locked_by:%s' % lock_value
                            ) if lock_value else 'locked'

    def __enter__(self):
        if not self.acquire():
            raise self.exc_class()

    def __exit__(self, *a, **kw):
        return self.release()

    def acquire(self, reentrant_id=None):
        """ We implement the re-entrant lock with a poor-man's solution:
            In case of an already taken lock, if the new acquirer's ID
            equals the lock_value, we return ``True``.

            There is still a risk of race condition because the current
            method is not guaranteed to run atomically, but it's small
            in a multi-node networked environment.
        """
        val = self.REDIS.set(self.lock_id, self.lock_value,
                             ex=self.expire_time, nx=True)

        if reentrant_id:
            if val is None:
                return self.REDIS.get(self.lock_id)[10:] == reentrant_id

        return val

    def release(self):
        val = self.REDIS.get(self.lock_id)

        if val == self.lock_value:
            try:
                self.REDIS.delete(self.lock_id)

            except ValueError:
                # When used as a simple lock, the 'locked' value we use
                # produces “ValueError: invalid literal for int() with
                # base 10: 'locked'”. This is completely harmless. Other
                # values and exceptions must raise, though.
                if val != 'locked':
                    raise

            return True

        return False

    def is_locked(self):
        """ OMG this method costs so much,
            and can even have a race condition.
            Hope we don't need it too often.
        """

        if self.acquire():
            self.release()
            return False
        return True

# By default take the normal REDIS connection, but still allow
# to override it in tests via the class attribute.
RedisExpiringLock.REDIS = REDIS


class NoResourceAvailableException(Exception):
    """ Raised by the RedisSemaphore when the limit is reached. """

    pass


class RedisSemaphore(RedisExpiringLock):
    """ A simple but networked-machines-safe semaphore implementation.

        .. warning:: as this class inherits from :class:`RedisExpiringLock`,
            it has the automagic ability to make the semaphore expire after
            the default expiration period.

            This is OK for me because the Sem should be used to avoid
            concurrent requests in a short period of time, and should
            expire automatically to avoid problems with dead tasks.

            But, this can be surprising, and could probably lead to
            some frustration some day…
    """

    REDIS     = None
    key_base  = 'rsm'
    exc_class = NoResourceAvailableException

    def __init__(self, instance, resources_number=None):
        super(RedisSemaphore, self).__init__(instance=instance)

        #
        # NOT A GOOD Idea to reset semaphore at instanciation,
        # parallel workers have different instances of it.
        #
        self.sem_limit = resources_number or 1

        #LOGGER.warning('SEMinit: %s %s', self.lock_id, self.holders())

    def acquire(self):

        #LOGGER.warning('>> ACQUIRE before: %s', self.holders())

        val = self.REDIS.incr(self.lock_id)

        #LOGGER.warning('>> ACQUIRE after: %s', self.holders())

        if val <= self.sem_limit:
            return True

        else:
            #LOGGER.warning('>> WILL -1: %s', self.holders())

            self.release()
            return False

    def release(self):

        #LOGGER.warning('>> RELEASE before: %s', self.REDIS.get(self.lock_id))

        val = self.REDIS.decr(self.lock_id)

        #LOGGER.warning('>> RELEASE after: %s', val)

        if val < 0:
            # This should happen only during test, but just in case…
            LOGGER.warning(u'Semaphore value %s is under zero (%s), resetting.',
                           self.lock_id, val)
            self.REDIS.set(self.lock_id, 0)
            return False

        return True

    def set_limit(self, limit=None):

        if limit is None:
            limit = self.holders() + 1

        if self.sem_limit != limit:
            LOGGER.info('Semaphore %s limit changed from %s to %s.',
                        self.lock_id, self.sem_limit, limit)
            self.sem_limit = limit

        return limit

    def holders(self):
        # LOGGER.warning('>> HOLDERS: %s %s', self.lock_id,
        #                int(self.REDIS.get(self.lock_id) or 0))
        return int(self.REDIS.get(self.lock_id) or 0)


# By default take the normal REDIS connection, but still allow
# to override it in tests via the class attribute.
RedisSemaphore.REDIS = REDIS


class HttpResponseLogProcessor(urllib2.BaseHandler):
        """ urllib2 processor that maintains a log of HTTP responses.
            See http://code.google.com/p/feedparser/issues/detail?id=390
            For why it exists.
        """

        # Run after anything that's mangling headers (usually 500 or less),
        # but before HTTPErrorProcessor (1000).
        handler_order = 900

        def __init__(self):
            self.log = []

        def http_response(self, req, response):
            entry = {
                "url": req.get_full_url(),
                "status": response.getcode(),
            }
            location = response.info().get("Location")

            if location is not None:
                entry["location"] = location

            self.log.append(entry)

            return response

        https_response = http_response


class RedisStatsCounter(object):
    """ A small statistics counter implemented on top of REDIS. Meant to
        be replaced by a full-featured StatsD implementation at some point
        in the future.

        We explicitely need to cast return values. See
        http://stackoverflow.com/a/13060733/654755 for details. It should
        normally not be needed (cf.
        https://github.com/andymccurdy/redis-py#response-callbacks) but
        for an unknown reason it drove me crazy and I finally re-casted
        them again to make the whole thing work.
    """
    REDIS      = None
    GLOBAL_KEY = 'gbl'

    def __init__(self, *args, **kwargs):

        # This could clash with a pure Django model because IDs overlap
        # from one model to another. It doesn't with MongoDB documents,
        # where IDs are unique accross the whole database.
        if __debug__ and args:
            assert not isinstance(args[0], models.Model)

        self.instance_id = (args[0].id if isinstance(args[0], Document)
                            else args[0]
                            ) if args else RedisStatsCounter.GLOBAL_KEY

        try:
            self.key_base = '{0}:{1}'.format(self.__class__.key_base,
                                             self.instance_id)
        except AttributeError:
            raise RuntimeError(u'RedisStatsCounter is an abstract class. '
                               u'You should not use it directly but '
                               u'rather create your own stats class '
                               u'with a `cls.key_base` attribute.')

    @classmethod
    def _time_key(cls, key, set_time=False, time_value=None):

        if set_time:
            return cls.REDIS.set(key, time.time()
                                 if time_value is None else time_value)

        return ftstamp(float(cls.REDIS.get(key) or 0.0))

    @classmethod
    def _int_incr_key(cls, key, increment=False):

        if increment == 'reset':
            # return, else we increment to 1…
            return cls.REDIS.delete(key)

        if increment:
            return int(cls.REDIS.incr(key))

        return int(cls.REDIS.get(key) or 0)

    @classmethod
    def _int_set_key(cls, key, set_value=None):

        if set_value is None:
            return int(cls.REDIS.get(key) or 0)

        return cls.REDIS.set(key, set_value)

    def running(self, set_running=None):

        key = self.key_base + ':run'

        # Just to be sure we need to cast…
        # LOGGER.warning('running: set=%s, value=%s type=%s',
        #                set_running, self.REDIS.get(self.key_base),
        #                type(self.REDIS.get(self.key_base)))

        if set_running is None:
            return boolcast[RedisStatsCounter.REDIS.get(key)]

        return RedisStatsCounter.REDIS.set(key, set_running)

# By default take the normal REDIS connection, but still allow
# to override it in tests via the class attribute.
RedisStatsCounter.REDIS = REDIS


def word_match_consecutive_once(term, word):
    """ Eat letters as far as we find them
        to get a quite-enough fuzy match. """

    for char in term:
        idx = word.find(char)

        if idx >= 0:
            word = word[idx + 1:]

        else:
            return False

    return True


def get_common_values(orig_dikt, exclude_list=None, match_strict=False):
    """ Return a list of common elements in dict values.

    We assume that:

    - dictionnary values are lists. The function will alter them in a copy,
      but for easiness of first implementation, we will not try turn every
      kind of iterable into a mutable one.
    - finding an element in another list is enough to consider it “common”.
      Doing a strict intersection is left as an exercise when we need it,
      with the :param:`match_strict` parameter.


    .. warning:: as of 20141006, this function is not tested; the feature
        that relied on it has been postponed.
    """

    if exclude_list is None:
        exclude_list = ()

    common_names = set()

    for pivot_key, pivot_values in orig_dikt.copy().items():

        for current_item_name in pivot_values:
            if current_item_name in exclude_list:
                continue

            for account, mailboxes in orig_dikt:
                if account == pivot_key:
                    continue

                if current_item_name in mailboxes:
                    common_names.add(current_item_name)

                    for remacct, remmb in orig_dikt.items():
                        try:
                            remmb.remove(current_item_name)

                        except:
                            # It is likely that many accounts have
                            # different mailboxes structure.
                            pass

    return common_names


def list_chunks(lisT, chunks_len):
    """ Split a :param:`lisT` in chunks of :param:`chunks_len`.

    Cf. http://stackoverflow.com/q/312443/654755
    """

    for i in xrange(0, len(lisT), chunks_len):
            yield lisT[i:i + chunks_len]
