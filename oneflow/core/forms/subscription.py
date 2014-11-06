class ManageSubscriptionForm(forms.ModelForm):

    """ Edit subscription properties. """

    class Meta:
        model = Subscription

        # NOTE: as we manage `folders` differently and very specially, given
        # the value of a user preference, we MUST NOT put `folders` here in
        # `fields`, because in one of 2 cases, setting the initial value will
        # not work because of attribute being a list and field being not.
        fields = ('name', )
        widgets = {
            'name': forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        """ init(me). """

        super(ManageSubscriptionForm, self).__init__(*args, **kwargs)

        folders_queryset = self.instance.user.folders_tree

        if self.instance.user.preferences.selector.subscriptions_in_multiple_folders:  # NOQA
            self.fields['folders'] = OnlyNameMultipleChoiceField(
                queryset=folders_queryset, required=False, label=_(u'Folders'),
                widget=Select2MultipleWidget(), initial=self.instance.folders)
            # no empty_label here.

        else:
            self.fields['folders'] = OnlyNameChoiceField(
                queryset=folders_queryset, required=False,
                widget=Select2Widget(), label=_(u'Folder'),
                empty_label=_(u'(None)'))

            try:
                self.fields['folders'].initial = self.instance.folders[0]

            except IndexError:
                # Subscription is not in any folder yet.
                pass

    def save(self, commit=True):
        """ Save the form, Luke. """

        subscription = super(ManageSubscriptionForm, self).save(commit=False)
        preferences  = subscription.user.preferences.selector

        # Handle `folders` manually, because it's not in form.fields.
        if preferences.subscriptions_in_multiple_folders:
            if self.cleaned_data['folders']:
                subscription.folders = self.cleaned_data['folders']

        elif self.cleaned_data['folders'] is not None:
            # Avoid the:
            #   - 'folders : Saisissez une liste de valeurs.' error.
            #   - A ReferenceField only accepts DBRef or documents: ['folders']
            #       when nothing is selected, this makes value=[None].
            #
            # In "one folder only", we used a "select" widget which didn't
            # built a list. We need to reconstruct it for the save() to work.
            subscription.folders = [self.cleaned_data['folders']]

        elif self.cleaned_data['folders'] is None:
            # User emptied the folder field. The subscription is back to
            # “un-sorted” pseudo-folder.
            subscription.folders = []

        if commit:
            subscription.save()

        return subscription


class AddSubscriptionForm(forms.Form):

    """ Subscribe the user to feeds. """

    feeds = OnlyNameMultipleChoiceField(queryset=BaseFeed.objects.none(),
                                        required=False,
                                        label=_(u'Search 1flow\'s streams'))

    search_for = forms.CharField(label=_(u'Enter an URL'), required=False)

    def __init__(self, *args, **kwargs):
        """ INIT ME. """

        self.owner = kwargs.pop('owner')

        super(AddSubscriptionForm, self).__init__(*args, **kwargs)

        # not_shown = [s.feed.id for s in self.owner.subscriptions]
        # LOGGER.warning(len(not_shown))

        # NOTE: this query is replicated in the completer view.
        self.fields['feeds'].queryset = BaseFeed.good_feeds(
            id__nin=[s.feed.id for s in self.owner.subscriptions])

        count = self.fields['feeds'].queryset.count()

        self.fields['feeds'].widget = HeavySelect2MultipleWidget(
            data_url=reverse_lazy('feeds_completer'))

        self.fields['feeds'].widget.set_placeholder(
            _(u'Select feed(s) from the {0} referenced').format(count))

        self.fields['search_for'].help_text = _(
            u'<span class="muted">NOTE: this can be long. '
            u'You will be notified when search is done.</span> '
            u'<a href="{0}" target="_blank">How does it work?</a>').format(
                reverse('help') + unicode(_(u'#adding-subscriptions')))

    def is_valid(self):
        """ Be sure the user selects one field out the two. """

        res = super(AddSubscriptionForm, self).is_valid()

        if not res:
            return False

        if not self.cleaned_data['feeds'] \
                and not self.cleaned_data['search_for']:
            self._errors['nothing_choosen'] = \
                _(u'You have to fill at least one of the two fields.')
            return False

        return True

    def save(self, commit=True):
        """ Subscribe user to new feeds. """

        created_subscriptions = []

        selector_prefs = self.owner.preferences.selector

        for feed in self.cleaned_data['feeds']:

            folders = []

            for tag in feed.tags:
                folders.append(Folder.add_folder_from_tag(tag, self.owner))

                if not selector_prefs.subscriptions_in_multiple_folders:
                    # One is enough.
                    break

            subscription = Subscription.subscribe_user_to_feed(self.owner, feed,
                                                               background=True)

            subscription.folders = folders

            if commit:
                subscription.save()

            created_subscriptions.append(subscription)

        return created_subscriptions
