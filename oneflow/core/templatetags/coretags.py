# -*- coding: utf-8 -*-
"""
Copyright 2013-2014 Olivier Cortès <oc@1flow.io>.

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
import difflib
import mistune

from constance import config
from markdown_deux import markdown as mk2_markdown

from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from ...base.templatetags.base_utils import get_view_name
from ...base.utils.dateutils import (now, today,
                                     naturaldelta as onef_naturaldelta)

from oneflow.core import models   # , CACHE_ONE_WEEK

from ..context_processors import content_types

LOGGER = logging.getLogger(__name__)

register = template.Library()

reading_lists = {

    'web_import': (_(u'Imported elements'),
                   # tooltip_both,
                   _(u'You have {0} newly imported items.'),
                   # tooltip_unread
                   _(u'You have {0} newly imported items, out of {1} so far'),
                   # tooltip_all,
                   _(u'You imported {0} web items so far'),
                   # tooltip_none
                   _(u'You did not import anything until now'),
                   ),

    'read_all':         (_(u'All articles'),
                         _(u'You have {0} articles in 1flow'),
                         'all_articles_count'),
    'read':             (_(u"All unread"),
                         _(u'You have {0} unread articles'),
                         'unread_articles_count'),
    'read_later':       (_(u"Read later"),
                         _(u'You have {0} articles to read later'),
                         'bookmarked_articles_count'),
    'read_starred':     (_(u'Starred'),
                         _(u'You have {0} starred articles'),
                         'starred_articles_count'),
    'read_archived':    (_(u"Archived"),
                         _(u'You have {0} archived articles'),
                         'archived_articles_count'),

    'read_fun':         (_(u'Funbox'),
                         _(u'You have {0} fun articles'),
                         'fun_articles_count'),

    'read_facts':       (_(u'Facts'),
                         _(u'You have {0} articles marked as fact(s)'),
                         'fact_articles_count'),
    'read_numbers':     (_(u'Numbers'),
                         _(u'You have {0} articles marked as number(s)'),
                         'number_articles_count'),
    'read_analysis':    (_(u'Analysis'),
                         _(u'You have {0} articles marked as analysis'),
                         'analysis_articles_count'),
    'read_prospective': (_(u'Prospective'),
                         _(u'You have {0} articles marked as prospective'),
                         'prospective_articles_count'),
    'read_know_how':    (_(u'Best-practices'),
                         _(u'You have {0} articles marked as best-practices'),
                         'knowhow_articles_count'),
    'read_rules':       (_(u'Regulations'),
                         _(u'You have {0} articles marked as regulation/legal'),
                         'rules_articles_count'),
    'read_quotes':      (_(u'Quotes'),
                         _(u'You have {0} articles marked as quote(s)'),
                         'quote_articles_count'),
    'read_knowledge':   (_(u'Knowledge'),
                         _(u'You have {0} articles marked as knowledge'),
                         'knowledge_articles_count'),
}


# colors =["%06x" % random.randint(0,0xFFFFFF) for i in range(255)]
random_colors = [
    'e5479e', 'e37331', 'a0072f', '2d58d5', 'c4dce6', 'b2d547', '235746',
    '1b30d4', '406596', '2955b3', '70e1f8', 'ad3b12', 'c4bd01', '8b32fe',
    '3ead7e', '689900', 'abdb8f', 'de9e17', 'fe99f5', '9a451a', '8091be',
    '50fbab', 'c18b8e', 'df3d42', '81a09f', 'fdf27c', '3a939d', '6944a6',
    '90206c', 'd98fa5', '5f2265', '6f218a', '5eb070', '296616', 'c46e9d',
    'eec4aa', 'bca7b3', 'a59ea7', '8617a1', '2a76d8', '79997d', 'bd4797',
    '7b58e9', '082214', '198688', '614708', 'f50529', '05a652', 'cb346b',
    '1d1162', '083658', 'a787e7', 'dee937', '3a2228', '4ffde8', 'b4adcc',
    '2f7052', '1d00b7', '6faee5', '40e2ec', 'bfa558', '5203e4', '457e56',
    '94c67c', 'c21ab2', 'c07e03', 'c111f6', '3771f7', '094cf4', '4c9ea2',
    '4a1f83', 'feb28e', 'f60971', '749a9e', '78b058', '258a65', '5b9cb0',
    '4d1bc8', '23d0bc', '70a8d2', '5f4648', '603070', '952c58', '2b9bb3',
    'f4ba8f', 'b0e0d6', '6ea6c5', '8b1706', '0cb904', '767021', 'ea21b4',
    'b28f0f', '67c76b', 'ad3599', 'cd65d2', '5c5f84', 'e7d9a0', '40ef4f',
    'b41768', 'd64200', 'd37288', '2aa6be', '845e91', '1b793e', '7544f6',
    '558e91', '98ffd0', '4ed9f0', '52f5e3', '23748c', '192912', '2c2547',
    '643ce0', '3d9924', '603f5d', 'eed6c8', 'c58e19', 'bd3d43', 'c1bf9b',
    '839d96', '4dab28', 'd07948', 'da5b9c', '640e71', '247538', '0e9ebf',
    '63e204', '3ee4d1', 'aab2ce', '9156ff', '730779', '54a6f4', 'b719c3',
    '2c626f', 'f2593e', 'd4dcaf', '41c177', '0c2e9b', '788b61', '7d3fd9',
    '1d06ec', '7c3a0a', 'b01827', '01b18f', 'cc9f7f', 'd302ec', '40cfbe',
    'f9e817', '5625ac', '088157', 'eb7c64', '94db02', 'fb5aa8', '406694',
    '6166d8', 'ba2c61', 'f99ac7', 'd8eafa', '128e4e', '604062', '4b343b',
    '4baebe', 'fb3c64', '032f90', '576b9a', 'b8afb1', '5f06e6', 'c8b897',
    '9689e3', '19a641', 'dc7785', 'a9dc1f', 'a7bc2e', '764f45', 'bcac0c',
    'e0c848', '3e3aa8', 'b9f8d5', 'a37726', 'c1ba2a', '4bb9cd', '45f18f',
    'ec7bc3', 'd55c9e', 'bc5ed6', 'bdb494', '2436e9', '0141cb', '8dbda0',
    '016354', '6c6386', '0bff73', '59e646', '831f4c', 'dcc0b3', '834508',
    'a33a55', '63b06b', '9357db', 'bb31b7', '541161', 'f84041', '722a7f',
    '8512ce', 'b48bc0', 'ad82d6', 'd9b5df', 'c06730', '698767', 'cd9f78',
    'fa8f13', '3c69c5', '9883f9', 'de283c', '41bdcf', '48005d', '96c274',
    'df3b7d', '87bd69', 'ae00bd', 'eee68c', '5304a7', '69071d', '7a61a6',
    '33573a', '89a44e', '689625', 'ec8235', '084f3e', '4fd8f6', '82caa1',
    '8a9db7', '0b88ed', '7a7ac3', 'a4e454', 'cd9373', '340111', '4a6f79',
    'afa195', 'd60429', '3660fd', 'c37e93', '993047', '06bb9a', 'e1a26b',
    'e629dc', 'be882d', 'b63bd3', '563aec', '716490', 'e27bc0', 'a17405'
    '80d8d8', '928525', 'f07344',
]

@register.filter
def naturaldelta(the_datetime):

    return onef_naturaldelta(now() - the_datetime)


@register.simple_tag
def feature_not_ready():

    return mark_safe(u' title="{0}" data-toggle="tooltip" '.format(
                     _(u'Feature coming soon. More information on the '
                       u'1flow blog http://blog.1flow.io/ or Twitter '
                       u'@1flow_io.')))


@register.simple_tag(takes_context=True)
def search_action(context):

    view_name = get_view_name(context)

    if view_name == u'source_selector':
        return u'action="{0}"'.format(reverse('read_all'))

    return u''


@register.simple_tag(takes_context=True)
def search_label(context):

    view_name = get_view_name(context)

    if u'folder' in view_name:
        return _(u'Search in folder…')

    elif u'feed' in view_name:
        return _(u'Search in feed…')

    return _(u'Search…')


@register.simple_tag
# HEADS UP: we can't cache simpletags results, it will
# cache only one value, whatever the tag arguments are…
#@cached(CACHE_ONE_WEEK)
def read_status_css(read):

    css = []

    for attr in models.Read.get_status_attributes():
        css.append(attr if getattr(read, attr) else (u'not_' + attr))

    return u' '.join(css)


@register.simple_tag
def reading_list_with_count(user, view_name, show_unreads=False,
                            css_classes=None):

    list_name, tooltip, count_attr_name = reading_lists[view_name]

    if user.preferences.selector.lists_show_unread_count:
        count_span = u'&nbsp; <small class="unread-count">({0})</small>'
    else:
        count_span = u''

    count = getattr(user, count_attr_name)

    if show_unreads and count:
        has_unread_start = u'<span class="has-unread">'
        has_unread_end   = u'</span>'

    else:
        has_unread_start = u''
        has_unread_end   = u''

    return mark_safe(
        (
            u'{5}<a href="{0}" class="{1} name" title="{2}" '
            u'data-toggle="tooltip">{3}{4}</a>{6}'
        ).format(
            reverse(view_name), css_classes or u'nowrap',
            tooltip.format(count), list_name, count_span.format(count),
            has_unread_start, has_unread_end
        )
    )


@register.simple_tag
def subscription_css(subscription, folder, level):

    css_classes = u'subscription'

    if subscription.has_unread:
        css_classes += u' has-unread'

    if subscription.is_closed:
        css_classes += u' is_closed'

    # On small devices, any level takes the whole width.
    css_classes += u' col-xs-12'

    if level == 1:
        if folder:
            nb_subscriptions = folder.subscriptions.count()

        else:
            # We don't care.
            nb_subscriptions = 1

        if nb_subscriptions > 8:
            css_classes += u' col-sm-6 col-md-4 col-lg-4'

        elif nb_subscriptions > 3:
            css_classes += u' col-sm-6 col-md-6 col-lg-6'

    else:

        css_classes += u' col-sm-6 col-md-4 col-lg-3'

    return css_classes


@register.simple_tag
def folder_css(folder, level):

    nb_subscriptions = folder.subscriptions.count()

    #css_classes = u'folder'
    css_classes = u''

    if folder.has_content:
        css_classes += u' has_content'

    # On small devices, any level takes the whole width.
    css_classes += u' col-xs-12'

    if level == 1:
        if nb_subscriptions > 8:
            css_classes += u' col-sm-12 col-md-12 col-lg-9'

        elif nb_subscriptions > 3:
            css_classes += u' col-sm-12 col-md-8 col-lg-6'

        else:
            css_classes += u' col-sm-12 col-md-4 col-lg-3'

    return css_classes


@register.simple_tag
def special_subscription_list_with_count(user, special_name, css_classes=None):

    list_name, tooltip_both, tooltip_unread, tooltip_all, tooltip_none = \
        reading_lists[special_name]

    subscription = getattr(user, special_name + u'_subscription')
    all_count    = subscription.all_articles_count
    unread_count = subscription.unread_articles_count

    count_span = u''
    make_span  = False

    if unread_count and unread_count == all_count:
        tooltip   = tooltip_both.format(unread_count, all_count)
        make_span = True

    elif unread_count:
        tooltip   = tooltip_unread.format(unread_count, all_count)
        make_span = True

    elif all_count:
        tooltip = tooltip_all.format(all_count)

    else:
        tooltip = _(u'You have nothing in this list yet.')

    if make_span and user.preferences.selector.lists_show_unread_count:
        count_span = (u'&nbsp; <small class="unread-count">'
                      u'({0})</small>'.format(unread_count))

    if unread_count:
        has_unread_start = u'<span class="has-unread">'
        has_unread_end   = u'</span>'

    else:
        has_unread_start = u''
        has_unread_end   = u''

    return mark_safe(
        (
            u'{5}<a href="{0}" class="{1} name" title="{2}" '
            u'data-toggle="tooltip">{3}{4}</a>{6}'
        ).format(
            reverse('read_all_feed', kwargs={'feed': subscription.id}),
            css_classes or u'nowrap', tooltip, list_name, count_span,
            has_unread_start, has_unread_end
        )
    )


@register.simple_tag
def container_reading_list_with_count(view_name, container_type, container,
                                      attrname, translation, css_classes=None,
                                      always_show=False):

    # u'<a href="{0}" class="{1} {2} async-get" data-async-get="count">{3}'
    # u'<span class="count"></span></a>'

    count      = getattr(container, attrname + '_articles_count')
    view_name += u'_' + container_type

    if always_show or count > 0:
        count_as_digits = unicode(count)

        small_class = u''
        add_title   = False

        if len(count_as_digits) > 6:
            small_class     = u'small'
            count_as_digits = count_as_digits[:-6] + unicode(_(u'M+'))
            add_title       = True

        elif len(count_as_digits) > 3:
            small_class     = u'small'
            count_as_digits = count_as_digits[:-3] + unicode(_(u'k+'))
            add_title       = True

        elif len(count_as_digits) > 2:
            small_class = u'small'

        return mark_safe((
            u'<a href="{url}" class="{class1} {class2}" {title}>{trans}'
            u'&nbsp;<span class="unread-count count {small}">'
            u'({count})</span></a>'
        ).format(
            url=reverse(view_name, kwargs={container_type: container.id}),
            class1=view_name,
            class2=css_classes or u'nowrap',
            title=(u'title="%s" data-toggle="tooltip"' %
                   _(u'{0} articles').format(count)) if add_title else u'',
            trans=translation,
            small=small_class,
            count=count_as_digits))

    return u''


@register.inclusion_tag('snippets/home/announcements.html')
def system_announcements(user):
    """ Get announcements in the constance database, if set.

        If the `ANNOUNCEMENT_{USER,STAFF}` key contains nothing,
        the corresponding announcement will not be done. All other
        parameters (prefix, dates, priority) can stay set between
        announcements, this doesn't hurt.

    """

    announcements = []
    dttoday = today()

    def stack_announcement(announcement_name):

        ANNMT  = u'ANNOUNCEMENT_' + announcement_name
        hide   = 'true'  # This is javascript :-D

        message = getattr(config, ANNMT, u'').strip()
        prefix = getattr(config, ANNMT + u'_PREFIX', u'')

        if message:
            # NOTE: This is a non-breakable space, else it gets lost.
            message = mistune.markdown(prefix + (u' ' if prefix else u'')
                                       + message).strip()

            priority = getattr(config, ANNMT + u'_PRIORITY', u'').lower()

            if priority not in (u'', u'info', u'success', u'error'):
                priority = u'info'

            if priority in (u'info', u'error'):
                hide = 'false'

            start_date = getattr(config, ANNMT + u'_START', u'')
            end_date   = getattr(config, ANNMT + u'_END', u'')

            if (not start_date or start_date <= dttoday) and (
                    not end_date or end_date >= dttoday):

                announcements.append((message, priority, hide))

    stack_announcement(u'USER')

    if user.is_staff or user.is_superuser:
        stack_announcement(u'STAFF')

    return {'announcements': announcements}


@register.simple_tag
def read_action_toggle_url(read):

    any_key = models.Read.get_status_attributes()[0]
    url_base = reverse('toggle', kwargs={'klass': 'Read',
                       'oid': read.id, 'key': any_key}).replace(
        any_key, u'@@KEY@@')

    return u'data-url-action-toggle={0}'.format(url_base)


#@cached(CACHE_ONE_WEEK)
def article_full_content_display(article):

    if article.content_type == models.CONTENT_TYPE_MARKDOWN:

        if len(article.content) > config.READ_ARTICLE_MIN_LENGTH:

            # START temporary measure.
            # TODO: please get rid of this…

            title_len = len(article.title)

            transient_content = article.content

            if title_len > 10:
                search_len = title_len * 2

                diff = difflib.SequenceMatcher(None,
                                               article.content[:search_len],
                                               article.title)

                if diff.ratio() > 0.51:
                    for blk in reversed(diff.matching_blocks):
                        # Sometimes, last match is the empty string… Skip it.
                        if blk[-1] != 0:
                            transient_content = article.content[
                                blk[0] + blk[2]:
                            ]
                            break

            # END temporary measure.

            try:
                # On large screens, make the article start a little far from
                # the top of the screen, it makes a better reading experience.
                return (u'<div class="spacer50 visible-lg"></div>'
                        + mistune.markdown(transient_content))

            except:
                LOGGER.exception(u'Live Markdown to HTML conversion '
                                 u'failed for article %s, trying '
                                 u'alternate parser.', article)

                try:
                    return (u'<div class="spacer50 visible-lg"></div>'
                            + mk2_markdown(transient_content))

                except:
                    LOGGER.exception(u'Alternate live Markdown to HTML '
                                     u'conversion failed for article %s',
                                     article)
                    return None


@register.simple_tag
#@cached(CACHE_ONE_WEEK)
def read_original(article, with_text=None):

    return u'''<span class="action action-read-original {0} popover-top"
      title="{1}"><a href="{2}" target="_blank" class="nowrap">
      <i class="icon-fixed-width icon-globe"></i>&nbsp;{3}</a></span>'''.format(
        u'popover-tooltip' if with_text else u'',
        _(u"Display on the original website"), article.url,
        u'<span class="hidden-inline-xs hidden-inline-sm">'
        u'{0}&nbsp;</span>'.format(_(u'Read original'))
    )


def article_excerpt_content_display(article):

    excerpt = article.excerpt

    if excerpt:
        if len(excerpt) > config.READ_ARTICLE_MIN_LENGTH:
            # HTML content…
            # if re.search(r'<[^>]+>', excerpt):

            return excerpt

            # try:
            #     return markdown(excerpt)
            # except Exception:
            #     LOGGER.exception(u'Live Markdown to HTML conversion '
            #                      u'failed for article %s', article)
            #     return None

    #
    # Now, if we don't have any excerpt, just cut down the content a lot
    # to be sure WE are not cut down by repressive laws from another age.
    #

    if article.content_type == models.CONTENT_TYPE_MARKDOWN:

        try:
            # Save it for next time / user to cool CPU usage.    save=True
            return article.make_excerpt()

        except Exception:
            LOGGER.exception(u'Live Markdown to HTML conversion '
                             u'failed for article %s', article)
            return None


@register.inclusion_tag('snippets/read/article-content.html',
                        takes_context=True)
def article_read_content(context, read):

    if read.is_restricted:
        #content = article_excerpt_content_display(article)
        #excerpt = True

        # Having None triggers the iframe display, which is more elegant
        # and directly useful to the user than displaying just an excerpt.
        content = None
        excerpt = None

    else:
        content = article_full_content_display(read.article)
        excerpt = False

    context.update({
        'read': read,
        'article': read.article,

        # We don't mark_safe() here, else mark_safe(None) outputs "None"
        # in the templates, and "if content" tests fail because content
        # is "None" instead of plain `None`.
        'content': content,
        'excerpt': excerpt
    })

    # WHY DO I NEED TO DO THIS? WHY !?
    context.update(content_types(None))

    return context


@register.inclusion_tag('snippets/read/read-action.html')
def read_action(article, action_name, with_text=True, popover_direction=None):

    if action_name.startswith('is_'):
        return {
            'with_text': with_text,
            'popover_direction': popover_direction or 'top',
            'action_name': action_name,
            'action_data': models.Read.status_data.get(action_name),
            'popover_class': '' if with_text else 'popover-tooltip',
            'js_func': "toggle_status(event, '{0}', '{1}')".format(
                       article.id, action_name)
        }

    return {
        'with_text': with_text,
        'popover_direction': popover_direction or 'top',
        'action_name': action_name,
        'action_data': {
            'do_title':      _(u'Convert to full-text'),
            'undo_title':    _(u'Switch back to original'),
            'do_label':      _(u'Convert to full-text'),
            'undo_label':    _(u'View original'),
            'status_label':  _(u'converted'),
            'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                           u'exchange'),
            'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                           u'exchange'),
        },
        'popover_class': '' if with_text else 'popover-tooltip',
        'js_func': "switch_view('{0}', '{1}')".format(
                   article.id, action_name)
    }


@register.inclusion_tag('snippets/read/read-action-status.html')
def read_action_status(action_name, with_text=False):

    return {
        'with_text': with_text,
        'action_name': action_name,
        'action_data': models.Read.status_data.get(action_name),
    }


@register.simple_tag
def read_status_css_styles():
    """ Just in case we add/remove/change read status/attributes in the
        future, the CSS are auto-generated from the list, in a “as DRY
        as possible” attitude.

    .. warning:: ``display: inherit`` was making our ``<span>``s
        display as block, thus I forced ``inline-block``. But it
        could break things in the future if HTML structure changes
        deeply.
    """

    return u' '.join((
                     u'.{0} .action-mark-not_{0}{{display:inline-block}} '
                     u'.{0} .action-mark-{0}{{display:none}}'
                     u'.not_{0} .action-mark-not_{0}{{display:none}} '
                     u'.not_{0} .action-mark-{0}{{display:inline-block}}'
                     ).format(status)
                     for status in models.Read.status_data.keys()
                     if 'list_url' in models.Read.status_data[status])


# —————————————————————————————————————————————————————————— Mail accounts tags


@register.simple_tag
def core_icon(klass_name):
    """ Centralize all model icons and render them. """

    return u'<i class="icon icon-{0} icon-fixed-width"></i>'.format({
        'MailAccount': 'inbox',
        'MailFeed': 'envelope',
        'MailFeedRule': 'random',
        'Profile': 'user',
        'HistoryEntry': 'book',
    }[klass_name])


@register.simple_tag
def mail_is_usable_to_icon(mailthing):
    """ Render an icon with tooltip, given account state. """

    # {% if mailaccount.is_usable %}
    # {% mailfeed_rules_count mailaccount %}</td>
    # <td class="right">{{ mailaccount.mailboxes|length }}</td>
    # {% else %}
    # <td></td>
    # <td></td>
    # {% endif %}

    if isinstance(mailthing, models.MailAccount):
        attr_name = 'is_usable'
        err_attr  = 'conn_error'
        message_ok = _(u'Account successfully working, tested {ago} ago.')
        message_er = _(u'Account not working, tested {ago} ago. '
                       u'Error reported: {err}')
        ago = onef_naturaldelta(now() - mailthing.date_last_conn)
    else:
        attr_name = 'is_valid'
        err_attr  = 'check_error'
        message_ok = _(u'Rule validated successfully and will be '
                       u'used for next fetch.')
        message_er = _(u'Rule did not validate. Error reported: {err}')
        ago = None

    template = (u'<span class="label label-{0}" title="{2}" '
                u'data-toggle="tooltip" data-placement="top">'
                u'<i class="icon icon-fixed-width icon-{1}"></i></span>')

    if getattr(mailthing, attr_name):
        return template.format('success', 'ok', message_ok.format(ago=ago))

    else:
        error_text = getattr(mailthing, err_attr)

        if error_text:
            return template.format('danger', 'exclamation',
                                   message_er.format(ago=ago, err=error_text))
        else:
            return template.format('warning', 'question',
                                   _(u'Account connectivity not yet tested. '
                                     u'Please wait a few seconds and reload '
                                     u'the current page.'))


@register.simple_tag
def mailfeed_rules_count(mailaccount):
    """ Return a count of rules applicable to a given account. """

    return (mailaccount.mailfeedrule_set.all().count()
            + models.MailFeedRule.objects.filter(account=None).count())


# ————————————————————————————————————————————————————————————— History entries

@register.inclusion_tag('snippets/history/userimport-feeds.html')
def userimport_feeds_details(user, feeds_urls):

    feeds = []

    for url in feeds_urls:
        try:
            feeds.append(models.Feed.objects.get(url=url))

        except:
            LOGGER.exception(u'Could not get feed with URL %s', url)

    subscriptions = []

    # HEADS UP: copy[:], else the remove() gives half the results
    for feed in feeds[:]:
        try:
            subscriptions.append(user.subscriptions.get(feed=feed))

        except:
            LOGGER.exception(u'Could not get subscription with feed %s '
                             u'for user %s', feed, user)

        else:
            feeds.remove(feed)

    return {
        'subscriptions': subscriptions,
        'feeds': feeds,
    }


@register.inclusion_tag('snippets/history/userimport-articles.html')
def userimport_articles_details(user, articles_urls):

    articles = []

    for url in articles_urls:
        try:
            articles.append(models.Article.objects.get(url=url))

        except:
            LOGGER.exception(u'Could not get article with URL %s', url)

    reads = []

    # HEADS UP: copy[:], else the remove() gives half the results
    for article in articles[:]:
        try:
            reads.append(user.reads.get(article=article))

        except:
            LOGGER.exception(u'Could not get read with article %s for user %s',
                             article, user)

        else:
            articles.remove(article)

    return {
        'reads': reads,
        'articles': articles,
    }

@register.filter
def randcolor(number):
    """ Return a random color from a number. """

    return random_colors[number % len(random_colors)]
