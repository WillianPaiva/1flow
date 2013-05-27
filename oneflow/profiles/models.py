# -*- coding: utf-8 -*-

import uuid

from threading import Timer
from jsonfield import JSONField

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models, IntegrityError
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _


class UserProfile(models.Model):

    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                related_name='profile',
                                on_delete=models.CASCADE,
                                primary_key=True)

    email_announcements = models.BooleanField(_('Email announcements'),
                                              default=True, blank=True)
    register_request_data = JSONField(_('Register data'),
                                      default='{}', blank=True)
    last_modified = models.DateTimeField(_('Last modified'), auto_now_add=True)
    hash_code = models.CharField(_(u'Current validation code'), max_length=32,
                                 default=lambda: uuid.uuid4().hex)

    class Meta:
        verbose_name = _(u'User profile')
        verbose_name_plural = _(u'User profiles')

    def __unicode__(self):
        return u'Profile for User %s' % self.user.username

    def renew_hash_code(self, commit=True):
        self.hash_code = uuid.uuid4().hex
        if commit:
            self.save(update_fields=('hash_code',))

    def unsubscribe_url(self):
        return u'http://{0}{1}'.format(settings.SITE_DOMAIN,
                                       reverse('unsubscribe',
                                       kwargs={'hash_code': self.hash_code}))


def create_user_profile(sender, instance, created, **kwargs):

    def __create_user_profile(instance):
        try:
            profile, _ = UserProfile.objects.get_or_create(user=instance)

        except IntegrityError, e:
            if not 'duplicate key' in e.args[0]:
                    raise
    # 2 scenarii:
    # - the creation is made via the admin, and the admin will have already
    #   created the profile.
    # - the user is created elsewhere, and we *must* create the userprofile
    #   manually.
    #
    # We have to delay the creation, else we could trigger an integrity error
    # in the first case, which would imply rolling back the whole user creation.
    # In the Timer(), the creation will fail with the same error, but at least
    # it will be OK on the admin side.
    # In other conditions, the userprofile creation will just have been delayed
    # a little, which I hope is not a serious problem.
    #
    # The LogEntry test is useless, because the log entry is created after
    # the signals processing…
    # if LogEntry.objects.latest('action_time').get_edited_object() != instance:

    if created:
        t = Timer(1.0, __create_user_profile, args=(instance, ))
        t.start()

post_save.connect(create_user_profile, sender=get_user_model())
