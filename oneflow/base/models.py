# -*- coding: utf-8 -*-

from jsonfield import JSONField

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _


class UserProfile(models.Model):

    user = models.ForeignKey(User)
    register_request_data = JSONField(_('Register data'),
                                      default='{}', blank=True)
    select_paragraph = models.BooleanField(_('Select whole paragraph on click'),
                                           default=False, blank=True)
    default_public = models.BooleanField(_('Grows public by default'),
                                         default=True, blank=True)
    last_modified = models.DateTimeField(_('Last modified'), auto_now_add=True)

    class Meta:
        verbose_name = _(u'User profile')
        verbose_name_plural = _(u'User profiles')

    def __unicode__(self):
        return u'Profile for User %s' % self.user.username

User.profile = property(lambda u: UserProfile.objects.get_or_create(user=u)[0])
