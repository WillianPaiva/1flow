# -*- coding: utf-8 -*-
u"""
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

from django.conf import settings

from django.contrib import admin


from ..models.reldb import (
    # DjangoUser as User,

    HistoryEntry,

    MailAccount,

    Author,
    Folder,

    SyncNode,
    NodePermissions,
)


if settings.FULL_ADMIN:
    from helpcontent import HelpContent, HelpContentAdmin
    admin.site.register(HelpContent, HelpContentAdmin)


from website import WebSite, WebSiteAdmin
admin.site.register(WebSite, WebSiteAdmin)

admin.site.register(Author)
admin.site.register(Folder)

from processor import (
    Processor, ProcessorAdmin,
    ProcessingChain,
    ChainedItem, ChainedItemAdmin,
    ChainedItemParameter,
    ProcessingError,
    ProcessorCategory,
)
admin.site.register(Processor, ProcessorAdmin)
admin.site.register(ProcessingChain)
admin.site.register(ChainedItem, ChainedItemAdmin)
admin.site.register(ChainedItemParameter)
admin.site.register(ProcessingError)
admin.site.register(ProcessorCategory)

from language import Language, LanguageAdmin
admin.site.register(Language, LanguageAdmin)

admin.site.register(MailAccount)

# admin.site.register(CombinedFeedRule)

admin.site.register(HistoryEntry)

from userimport import UserImport, UserImportAdmin
admin.site.register(UserImport, UserImportAdmin)

admin.site.register(SyncNode)
admin.site.register(NodePermissions)

from feed import (
    RssAtomFeed, RssAtomFeedAdmin,
    MailFeed,
    MailFeedRule, MailFeedRuleAdmin,
    # CombinedFeed
    # TwitterFeed
)

admin.site.register(RssAtomFeed, RssAtomFeedAdmin)
admin.site.register(MailFeed)
admin.site.register(MailFeedRule, MailFeedRuleAdmin)
# admin.site.register(CombinedFeed)

from subscription import Subscription, SubscriptionAdmin
admin.site.register(Subscription, SubscriptionAdmin)

from article import Article, ArticleAdmin, OriginalData
admin.site.register(Article, ArticleAdmin)
admin.site.register(OriginalData)

from read import Read, ReadAdmin
admin.site.register(Read, ReadAdmin)

from tag import Tag, TagAdmin
admin.site.register(Tag, TagAdmin)

# TODO: remove this when migration is finished
import mongo  # NOQA
