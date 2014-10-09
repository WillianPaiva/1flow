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
