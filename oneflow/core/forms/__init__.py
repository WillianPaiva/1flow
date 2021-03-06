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

from .preferences import (HomePreferencesForm, ReadPreferencesForm,  # NOQA
                          SelectorPreferencesForm, StaffPreferencesForm)

from folder import ManageFolderForm  # NOQA

from subscription import AddSubscriptionForm, ManageSubscriptionForm  # NOQA

from .importers import WebPagesImportForm  # NOQA

from .read import ReadShareForm  # NOQA

from .website import WebSiteEditProcessingParametersForm  # NOQA

from .article import (  # NOQA
    ArticleEditExcerptForm,
    ArticleEditContentForm,
    HistoricalArticleEditExcerptForm,
    HistoricalArticleEditContentForm,
)

# —————————————————————————————————————————————————————————————————————— E-mail

from mailaccount import MailAccountForm  # NOQA

from mailfeed import MailFeedForm  # NOQA

from mailfeedrule import (  # NOQA
    MailFeedRuleForm,
    MailFeedRulePositionForm,
    MailFeedRuleGroupForm,
)

# ————————————————————————————————————————————————————————————————————— Twitter

from twitteraccount import TwitterAccountForm  # NOQA

from twitterfeed import TwitterFeedForm  # NOQA

from twitterfeedrule import (  # NOQA
    TwitterFeedRuleForm,
    TwitterFeedRulePositionForm,
    TwitterFeedRuleGroupForm,
)

# ——————————————————————————————————————————————————————————————————— Processor

from processor import (  # NOQA
    ProcessorForm,
    ProcessorEditRequirementsForm,
    ProcessorEditParametersForm,
    ProcessorEditAcceptCodeForm,
    ProcessorEditProcessCodeForm,
)

from processingchain import (  # NOQA
    ProcessingChainForm,
    # ProcessingChainEditRequirementsForm,
)

from chaineditem import (  # NOQA
    ChainedItemForm,
    ChainedItemPositionForm,
    ChainedItemEditParametersForm,
)


# ———————————————————————————————————————————————————————————————————————— Sync

from sync import SyncNodeForm  # NOQA
