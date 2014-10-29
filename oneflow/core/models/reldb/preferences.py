# -*- coding: utf-8 -*-
"""
Copyright 2014 Olivier Cortès <oc@1flow.io>.

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

import logging

# from collections import OrderedDict
from constance import config

from django.db import models
from django.db.models.signals import post_save  # , pre_save, pre_delete
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _
from sparks.django.models import ModelDiffMixin

from common import DjangoUser as User

LOGGER = logging.getLogger(__name__)


__all__ = [
    'Preferences',
]


# —————————————————————————————————————————————————————————————————————— Models


class Preferences(ModelDiffMixin):

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Preferences set')
        verbose_name_plural = _(u'Preferences sets')

    user = models.OneToOneField(User, primary_key=True,
                                verbose_name=_(u'Owner'))

    def __unicode__(self):
        return _(u'Preferences for user {0}').format(self.user.username)

    def check(self):

        for name, model in (
            ('snap', SnapPreferences, ),
            ('read', ReadPreferences, ),
            ('selector', SelectorPreferences, ),
            ('staff', StaffPreferences, ),
            ('share', SharePreferences, ),
            ('home', HomePreferences, ),
            ('wizards', HelpWizards, ),
            # ('notification', NotificationPreferences, ),
        ):

            try:
                getattr(self, name)

            except ObjectDoesNotExist:
                pref = model(preferences=self)
                pref.save()

# ———————————————————————————————————————————————————————————— User preferences


class SnapPreferences(ModelDiffMixin):

    """ Snap feature preferences. """

    class Meta:
        app_label = 'core'

    preferences = models.OneToOneField(Preferences, primary_key=True,
                                       related_name='snap')

    select_paragraph = models.BooleanField(
        verbose_name=_(u'Select whole paragraph on click'),
        default=False, blank=True)

    default_public = models.BooleanField(
        verbose_name=_(u'Grows public by default'),
        default=True, blank=True)


class NotificationPreferences(models.Model):
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

READING_SPEED_CHOICES = (
    (50, _(u'under 100 wpm')),
    (100, _(u'around 100 wpm')),
    (200, _(u'around 200 wpm')),
    (300, _(u'around 300 wpm')),
    (400, _(u'around 400 wpm')),
    (500, _(u'around 500 wpm')),
    (600, _(u'around 600 wpm')),
    (800, _(u'around 800 wpm')),
    (1000, _(u'around 1000 wpm (really?)')),
)


def read_default_reading_speed():

    return (config.READ_AVERAGE_READING_SPEED
            if config.READ_AVERAGE_READING_SPEED
            in [x[0] for x in READING_SPEED_CHOICES]
            else 200)


class ReadPreferences(ModelDiffMixin):

    """ Reading list preferences. """

    class Meta:
        app_label = 'core'

    preferences = models.OneToOneField(Preferences, primary_key=True,
                                       related_name='read')

    starred_marks_read = models.BooleanField(
        verbose_name=_(u'Starring marks read too'),
        help_text=_(u'When you mark an article starred, this will '
                    u'automatically mark it as read (default: true; we '
                    u'consider you have read it before you decide to '
                    u'like it).'),
        default=True, blank=True)

    starred_marks_archived = models.BooleanField(
        verbose_name=_(u'Starring marks archived too'),
        help_text=_(u'When you mark an article starred, this will '
                    u'automatically archive it, if not already '
                    u'done (default: false).'),
        default=False, blank=True)

    bookmarked_marks_archived = models.BooleanField(
        verbose_name=_(u'Reading later marks archived too'),
        help_text=_(u'Marking an article to read later will automatically '
                    u'archive it if not already done. (default: false).'),
        default=False, blank=True)

    watch_attributes_mark_archived = models.BooleanField(
        verbose_name=_(u'Setting any watch attribute marks archived too'),
        help_text=_(u'Setting any watch attribute will also mark it archived '
                    u'if not already done. (default: false).'),
        default=False, blank=True)

    starred_removes_bookmarked = models.BooleanField(
        verbose_name=_(u'Starring unmarks “read later”'),
        help_text=_(u'When you mark an article starred, this will '
                    u'automatically remove it from the “read later” '
                    u'list. (default: true; we consider you have read '
                    u'it before you decide to like it, thus it is not '
                    u'“to read later” anymore).'),
        default=True, blank=True)

    bookmarked_marks_unread = models.BooleanField(
        verbose_name=_(u'Reading later marks unread'),
        help_text=_(u'Marking an article to read later marks it as unread. '
                    u'As a consequence, articles to read later are counted '
                    u'in unread when this setting is enabled (default: true).'),
        default=True, blank=True)

    reading_speed = models.IntegerField(
        verbose_name=_(u'Average reading speed'),
        help_text=_(u'Set your reading speed for accurate reading time '
                    u'computations on text content.'),
        default=read_default_reading_speed, blank=True,
        choices=READING_SPEED_CHOICES)

    auto_mark_read_delay = models.IntegerField(
        verbose_name=_(u'Auto mark-read delay'),
        help_text=_(u'The delay after which an open article in any reading '
                    u'list will be automatically marked as read if it is not.'),
        default=4500, blank=True,
        choices=AUTO_MARK_READ_DELAY_CHOICES)

    read_switches_to_fullscreen = models.BooleanField(
        verbose_name=_(u'Switch to full-screen while reading'),
        help_text=_(u'Automatically hide navigation bars when opening an '
                    u'article for reading (default: false).<br />'
                    u'When enabled, fullscreen will remain active while you '
                    u'switch from one open article to another. Navigation bars '
                    u'will reappear when you close the current opened article '
                    u'without opening a new one (eg. when you return to the '
                    u'list view).<br />'
                    u'Whatever this setting, you can always show or hide '
                    u'navbars manually with the `shift`+`f` keyboard '
                    u'shortcut.'),
        default=False, blank=True)

    show_bottom_navbar = models.BooleanField(
        verbose_name=_(u'Show the bottom “jump to” navbar'),
        help_text=_(u'When you are in any reading list, either reading '
                    u'articles or just scrolling the list, you can have '
                    u'a navigation bar at the bottom of the screen, allowing '
                    u'you to quickly jump to other reading lists, or back to '
                    u'the sources selector.<br />'
                    u'<span class="muted">Default is not to show this '
                    u'navigation bar.</span>'),
        default=False, blank=True)


class SelectorPreferences(ModelDiffMixin):

    """ Source selector preferences. """

    class Meta:
        app_label = 'core'

    preferences = models.OneToOneField(Preferences, primary_key=True,
                                       related_name='selector')

    titles_show_unread_count = models.BooleanField(
        verbose_name=_(u'Feed names show unread count'),
        help_text=_(u'Activate this if you want to see the articles '
                    u'unread count in parenthesis near the feed titles.'),
        default=False, blank=True)

    lists_show_unread_count = models.BooleanField(
        verbose_name=_(u'Reading lists show unread count'),
        help_text=_(u'Each reading list is appended the number of articles '
                    u'marked as being part of it.'),
        default=False, blank=True)

    folders_show_unread_count = models.BooleanField(
        verbose_name=_(u'Folders show unread count'),
        help_text=_(u'Each folder is appended the sum of unread articles '
                    u'of each of its subfolders and subscriptions.'),
        default=False, blank=True)

    extended_folders_depth = models.BooleanField(
        verbose_name=_(u'folders can hold three levels of subfolders'),
        help_text=_(u'Folders have one level of subfolders in normal '
                    u'conditions. With this setting, you can push the limit '
                    u'to three (which makes a total classifying depth of four '
                    u'for your subscriptions).<br />'
                    u'<span class="muted">NOTE: The interface will become a '
                    u'little more difficult to read. Having a big and wide '
                    u'screen could help.</span>'),
        default=False, blank=True)

    subscriptions_in_multiple_folders = models.BooleanField(
        verbose_name=_(u'Subscriptions can be attached to multiple folders'),
        help_text=_(u'In normal conditions, a given subscription can be '
                    u'attached to only one folder. With this settings, you '
                    u'can make any subscription show in multiple places.'),
        default=False, blank=True)

    show_closed_streams = models.BooleanField(
        verbose_name=_(u'Show closed streams'),
        help_text=_(u'Display streams that have been closed by the system '
                    u'but to which you are still subscribed. As there will '
                    u'never be new content in them, it is safe to hide them '
                    u'in the selector. Unread articles from closed streams '
                    u'still show in the unread list.'),
        # TODO: use reverse_lazy('read') and make a link.
        # 20131004: it just crashes because of a circular
        # import loop in mongoadmin, to change.
        default=False, blank=True)


class StaffPreferences(ModelDiffMixin):
    """ Preferences for staff members / super users. """

    class Meta:
        app_label = 'core'

    preferences = models.OneToOneField(Preferences, primary_key=True,
                                       related_name='staff')

    super_powers_enabled = models.BooleanField(
        verbose_name=_(u'Super powers enabled'),
        help_text=_(u'Globaly enable or not every bit of staff/superuser '
                    u'features in the 1flow interface. If disabled, only the '
                    u'<strong>MAINTENANCE_MODE</strong> label in the navbar '
                    u'will visible, and this preference pane to be able to '
                    u're-enable the features once deactivated.<br />'
                    u'<span class="muted">Default: enabled.</span>'),
        default=True, blank=True)

    reading_lists_show_bad_articles = models.BooleanField(
        verbose_name=_(u'Show duplicates, orphaned and other transient data'),
        help_text=_(u'<strong>Warning</strong>: this breaks keyboard shortcut '
                    u'navigation whenever the first bad article is '
                    u'encountered.<br />'
                    u'<span class="muted">Default: disabled.</span>'),
        default=False, blank=True)

    selector_shows_admin_links = models.BooleanField(
        verbose_name=_(u'Selector shows admin links'),
        help_text=_(u'Automatically link to the admin from the selector '
                    u'whenever folder/subscription has missing data.<br />'
                    u'<span class="muted">Default: enabled.</span>'),
        default=True, blank=True)

    no_home_redirect = models.BooleanField(
        verbose_name=_(u'Landing page does not redirect to webapp'),
        help_text=_(u'As a staff member, you can have access to the landing '
                    u'page for testing / check purposes even if you are '
                    u'logged in, whereas standard logged in users are always '
                    u'automatically redirected to the web application.'),
        default=False, blank=True)

    allow_all_articles = models.BooleanField(
        verbose_name=_(u'Allow display of all articles'),
        help_text=_(u'As a staff member, you can have access to all fulltext '
                    u'content for testing / checking purposes. PLEASE DO NOT '
                    u'ENABLE IN NORMAL CONDITIONS.'),
        default=False, blank=True)


class SharePreferences(ModelDiffMixin):

    """ Preferences used when the user shares something. """

    class Meta:
        app_label = 'core'

    preferences = models.OneToOneField(Preferences, primary_key=True,
                                       related_name='share')

    # This has no default intentionnaly, in order
    # to use the generated one from inside the form.
    default_message = models.TextField(
        verbose_name=_(u'Default share message'),
        null=True, blank=True)


HOME_STYLE_CHOICES = (
    (u'RL', _(u'Reading list')),
    (u'TL', _(u'Tiled News')),
)


READ_SHOWS_CHOICES = (
    (1, _(u'Unread articles')),
    (2, _(u'Source selector')),
    (3, _(u'Read later list')),
    (4, _(u'Imported items')),
    (5, _(u'Starred items')),
)


class HomePreferences(ModelDiffMixin):

    """ Various HOME settings. """

    class Meta:
        app_label = 'core'

    preferences = models.OneToOneField(Preferences, primary_key=True,
                                       related_name='home')

    style_templates = {
        u'RL': 'snippets/read/read-list-item.html',
        u'TL': 'snippets/read/read-tiles-tile.html',
    }

    style = models.CharField(
        verbose_name=_(u'How the user wants his 1flow home to appear'),
        max_length=2, choices=HOME_STYLE_CHOICES, default=u'RL', blank=True)

    show_advanced_preferences = models.BooleanField(
        verbose_name=_(u'I want to play with my life'),
        help_text=_(u'With this setting, you will be able to tune the 1flow '
                    u'interface a lot more. <strong>But BEWARE:</strong> you '
                    u'will gain access to features which are not referenced in '
                    u'the standard documentation. You assume implicitly being '
                    u'a “power-user”, completely autonomous to discover hidden '
                    u'treasures… And traps!<br />'
                    u'<span class="muted">Default: disabled. We want your '
                    u'user experience to stay as smooth as possible.</span>'),
        default=False, blank=True)

    read_shows = models.IntegerField(
        verbose_name=_(u'Clicking <code>Read</code> displays:'),
        help_text=_(u'Define what 1flow will display when you click on '
                    u'the <code>Read</code> link in the top navbar of the '
                    u'interface. <br /><span class="muted">Default: shows '
                    u'the <strong>sources selector</strong>.</span>'),
        choices=READ_SHOWS_CHOICES,
        default=2, blank=True)

    experimental_features = models.BooleanField(
        verbose_name=_(u'Activate experimental features'),
        help_text=_(u'Activate features that are currently under '
                    u'development, beiing tested or privately '
                    u'deployed. USE AT YOUR OWN RISK!'),
        default=False, blank=True)

    def get_read_list_item_template(self):
        return HomePreferences.style_templates.get(self.style)


class HelpWizards(ModelDiffMixin):

    """ Stores if the user viewed the wizards / assistants or not.

    Special attribute is :attr:`show_all` via which the user
    can avoid them to be showed complely or not.
    """

    class Meta:
        app_label = 'core'

    preferences = models.OneToOneField(Preferences, primary_key=True,
                                       related_name='wizards')

    show_all           = models.BooleanField(default=True, blank=True)
    welcome_beta_shown = models.BooleanField(default=False, blank=True)


# ————————————————————————————————————————————————————————————————————— Signals


def user_post_save(instance, **kwargs):
    """ Create the UserFeeds set. """

    user = instance

    if kwargs.get('created', False):

        preferences = Preferences(user=user)
        preferences.check()

post_save.connect(user_post_save, sender=User)
