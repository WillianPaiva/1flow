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
import re
import logging
import operator

from collections import OrderedDict
from positions import PositionField

from django.db import models
from django.utils.translation import ugettext_lazy as _

# from django.utils.translation import ugettext as _
# from django.utils.text import slugify
# from sparks.django.models import ModelDiffMixin
# from oneflow.base.utils.dateutils import now

from sparks.django.models.mixins import ModelDiffMixin

from base import BaseFeed
# import mail_common as common
# from mailfeed import MailFeed
from combined import CombinedFeed

LOGGER = logging.getLogger(__name__)


class CombinedFeedRule(ModelDiffMixin):

    """  *feed rule (acts as filter and grouper).

    A Combined feed can have one or more rule.

    Each rule can apply to one or more feeds.

    If the feed type / feed is null the rule will apply to all.


        feed_type: all, mail, rss, twitter…
        feed

            feed_type == any + feed selected → incompatible.

        other attributes
    """

    INPLACEEDIT_PARENTCHAIN = ('combinedfeed', )

    FILTER_FIELD_CHOICES = OrderedDict((
        (u'titags', _(u'Title or tags')),
        (u'title', _(u'Title')),
        (u'tags', _(u'tags')),
        (u'content', _(u'content')),
        (u'any', _(u'Any (eg. title, tags or content)')),
        (u'type', _(u'Type')),
        (u'origin', _(u'Origin')),
        (u'lang', _(u'Language')),
        (u'restr', _(u'Is restricted')),
        (u'wc', _(u'Word count')),
    ))

    MATCH_TYPE_CHOICES = OrderedDict((
        (u'contains', _(u'contains')),
        (u'ncontains', _(u'does not contain')),
        (u'starts', _(u'starts with')),
        (u'nstarts', _(u'does not start with')),
        (u'ends', _(u'ends with')),
        (u'nends', _(u'does not end with')),
        (u'equals', _(u'strictly equals')),
        (u'nequals', _(u'is not equal to')),
        (u'greater', _(u'is greater than')),
        (u'greatereq', _(u'is greater or equal than')),
        (u'lower', _(u'is lower than')),
        (u'lowereq', _(u'is lower or equal than')),
        (u'ngreater', _(u'is not greater than')),
        (u'ngreatereq', _(u'is not greater or equal than')),
        (u'nlower', _(u'is not lower than')),
        (u'nlowereq', _(u'is not lower or equal than')),
        (u're_match', _(u'matches regular expression')),
        (u'nre_match', _(u'does not match reg. expr.')),
    ))

    combinedfeed = models.ForeignKey(CombinedFeed)

    feeds = models.ManyToManyField(BaseFeed)

    # filter_field = models.CharField(verbose_name=_(u'Field'),
    #                                 max_length=10, default=u'any',
    #                                 choices=tuple(HEADER_FIELD_CHOICES.items()),
    #                                 help_text=_(u"E-mail field on which the "
    #                                             u"match type is applied."))
    # match_type = models.CharField(verbose_name=_(u'Match type'),
    #                               max_length=10, default=u'contains',
    #                               choices=tuple(MATCH_TYPE_CHOICES.items()),
    #                               help_text=_(u"Operation applied on the "
    #                                           u"header to compare with match "
    #                                           u"value."))
    # match_case = models.BooleanField(verbose_name=_(u'Match case'),
    #                                  default=False, blank=True,
    #                                  help_text=_(u"Do we care about uppercase "
    #                                              u"and lowercase characters?"))
    # match_value = models.CharField(verbose_name=_(u'Match value'),
    #                                default=u'', max_length=1024,
    #                                help_text=_(u"Examples: “Tweet de”, "
    #                                            u"“Google Alert:”. Can be "
    #                                            u"any text."))

    # match_action = models.CharField(
    #     verbose_name=_(u'Action when matched'),
    #     max_length=10, null=True, blank=True,
    #     choices=tuple(MailFeed.MATCH_ACTION_CHOICES.items()),
    #     help_text=_(u'Choose nothing to execute '
    #                 u'action defined at the feed level.'))

    # finish_action =  models.CharField(
    #     verbose_name=_(u'Finish action'),
    #     max_length=10, null=True, blank=True,
    #     choices=tuple(MailFeed.FINISH_ACTION_CHOICES.items()),
    #     help_text=_(u'Choose nothing to execute '
    #                 u'action defined at the feed level.'))

    # Used to have many times the same rule in different feeds
    clone_of = models.ForeignKey('MailFeedRule', null=True, blank=True)
    position = PositionField(collection='mailfeed', default=0, blank=True)
    is_valid = models.BooleanField(verbose_name=_(u'Checked and valid'),
                                   default=True, blank=True)
    check_error = models.CharField(max_length=255, default=u'', blank=True)

    class Meta:
        app_label = 'core'
        ordering = ('position', )

    @property
    def operation(self):
        """ Return a Python function doing the operation of the rule.

        Cache it in an attribute to avoid redoing all the work each time
        this property is called, because in many cases the rule will be
        called more than once (on multiple messages of multiple mailboxes).
        """

        try:
            return self._operation_

        except AttributeError:

            def mymethodcaller(name):
                def caller(a, b):
                    return getattr(a, name)(b)

                return caller

            def ncontains(a, b):
                return not operator.contains(a, b)

            def nstarts(a, b):
                return not a.startswith(b)

            def nends(a, b):
                return not a.endswith(b)

            if self.match_type in (u're_match', u'nre_match'):
                # The .lower() should work also with the RE. It
                # should even be faster than a standard /I match().
                compiled_re = re.compile(self.match_value
                                         if self.match_case
                                         else self.match_value.lower())

            def re_match(a, b):
                """ :param:`b` is ignored, it's here for call compat only. """

                return bool(compiled_re.match(a))

            def nre_match(a, b):
                return not re_match(a, b)

            OPERATIONS = {
                u'contains': operator.contains,
                u'ncontains': ncontains,
                u'starts': mymethodcaller('startswith'),
                u'nstarts': nstarts,
                u'ends': mymethodcaller('endswith'),
                u'nends': nends,
                u'equals': operator.eq,
                u'nequals': operator.ne,
                u're_match': re.match,
                u'nre_match': nre_match,
            }

            self._operation_ = OPERATIONS[self.match_type]

            return self._operation_

    # —————————————————————————————————————————————————————————————————— Django

    def save(self, *args, **kwargs):
        """ Check the rule is valid before saving. """

        changed_fields = self.changed_fields

        if 'header_field' in changed_fields \
            or 'other_header' in changed_fields \
            or 'match_type' in changed_fields \
                or'match_value' in changed_fields:

            self.check_is_valid(commit=False)

        super(CombinedFeedRule, self).save(*args, **kwargs)

    # ——————————————————————————————————————————————————————————————— Internals

    def check_is_valid(self, commit=True):
        """ TODO: implement this for a combined feed rule. """

        is_valid = True

        if is_valid != self.is_valid:
            self.is_valid = is_valid

            if is_valid and self.check_error:
                self.check_error = u''

            if commit:
                self.save()

    def match_item(self, message):
        """ Return ``True`` if :param:`item` matches the current rule. """

        return False
