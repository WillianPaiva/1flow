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

from django.http import (
    HttpResponseRedirect,
    HttpResponseForbidden,
    HttpResponseBadRequest,
)
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from ..forms import ManageFolderForm
from ..models.nonrel import Folder, TreeCycleException

LOGGER = logging.getLogger(__name__)
User = get_user_model()


def manage_folder(request, **kwargs):
    """ Implement add & edit functions for folders. """

    folder_id = kwargs.pop('folder', None)
    folder    = Folder.get_or_404(folder_id) if folder_id else None
    edit_mode = folder is not None
    user      = request.user.mongo

    if request.POST:
        messages.info(request, u'manage folder POST "%s"' % request.POST,
                      extra_tags='safe')

        if edit_mode:
            messages.info(request, u'manage folder EDIT %s' % folder,
                          extra_tags='safe')

            form = ManageFolderForm(request.POST, instance=folder,
                                    owner=user)

        else:
            form = ManageFolderForm(request.POST, owner=user)

        if form.is_valid():

            try:
                folder = form.save()

            except TreeCycleException as e:
                messages.error(request, _(u'Save <em>{0}</em> '
                               u'failed: {1}').format(folder.name, e),
                               extra_tags=u'safe')

            else:
                messages.info(request, _(u'Folder <em>{0}</em> successfully '
                              u'{1}.').format(folder.name, _(u'modified')
                                              if edit_mode else _(u'created')),
                              extra_tags=u'safe')

        else:
            messages.info(request, u'TEST2', extra_tags='safe')
            messages.warning(request, _(u'Could not {0} folder: {1}.').format(
                             _(u'modify') if edit_mode else _(u'create'),
                             form.errors), extra_tags='sticky safe')

            LOGGER.error(u'%s: %s', form.errors, form.cleaned_data)

        return HttpResponseRedirect(reverse('source_selector')
                                    + (u"#{0}".format(folder.id)
                                       if folder else u''))

    else:
        if not request.is_ajax():
            return HttpResponseBadRequest('Did you forget to do an Ajax call?')

        if folder:
            form = ManageFolderForm(instance=folder, owner=user)

        else:
            parent = kwargs.pop('parent', None)

            if parent:
                form = ManageFolderForm(owner=user, initial={'parent': parent})
            else:

                form = ManageFolderForm(owner=user)

    return render(request, 'snippets/selector/manage-folder.html',
                  {'form': form, 'folder': folder})


def delete_folder(request, folder):
    """ Delete a folder. """

    folder = Folder.get_or_404(folder)

    if request.user.is_superuser or folder.owner == request.user.mongo:
        folder.delete()
        return redirect('source_selector')

    return HttpResponseForbidden()
