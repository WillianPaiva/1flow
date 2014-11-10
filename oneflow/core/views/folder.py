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

import logging

from django.http import (
    HttpResponseRedirect,
    HttpResponseForbidden,
    HttpResponseBadRequest,
)
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from ..forms import ManageFolderForm
from ..models import Folder, folder_purge_task

LOGGER = logging.getLogger(__name__)
User = get_user_model()


def manage_folder(request, **kwargs):
    """ Implement add & edit functions for folders. """

    # For creation, ID is None (not even in the arguments)
    folder_id = kwargs.pop('folder_id', None)
    folder    = get_object_or_404(Folder, id=folder_id) if folder_id else None
    edit_mode = folder is not None
    user      = request.user

    if request.POST:
        if edit_mode:
            form = ManageFolderForm(request.POST,
                                    instance=folder,
                                    owner=user)

        else:
            form = ManageFolderForm(request.POST, owner=user)

        if form.is_valid():

            try:
                folder = form.save()

            except Exception as e:
                LOGGER.exception(u'Could not save Folder %s', folder)
                messages.error(request, _(u'Save <em>{0}</em> '
                               u'failed: {1}').format(folder.name, e),
                               extra_tags=u'safe')

            else:
                messages.info(request, _(u'Folder <em>{0}</em> successfully '
                              u'{1}.').format(folder.name, _(u'modified')
                                              if edit_mode else _(u'created')),
                              extra_tags=u'safe')

        else:
            LOGGER.error(u'%s: %s, %s',
                         unicode(str(form.errors), errors='replace'),
                         u', '.join(u'%s: %s' % (f.name, f.errors)
                                    for f in form.visible_fields()),
                         unicode(str(form.cleaned_data), errors='replace'))

            messages.warning(request, _(u'Could not {0} folder: {1}.').format(
                             _(u'modify') if edit_mode else _(u'create'),
                             form.errors), extra_tags='sticky safe')

        return HttpResponseRedirect(reverse('source_selector')
                                    + (u"#folder-{0}".format(folder.id)
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


def delete_folder(request, folder_id, purge=False):
    """ Delete a folder. """

    folder = get_object_or_404(Folder, id=folder_id)

    if request.user.is_superuser or folder.user == request.user:

        if purge:
            messages.info(request,
                          _(u'Purging folder <em>{0}</em>, '
                            u'subfolders and subscriptions in the '
                            u'background…').format(folder.name),
                          extra_tags=u'safe')

            folder_purge_task.delay(folder.id)

        else:
            # With MPTT, we need to extract and move children first,
            # else they will be deleted with their parent if we don't.
            folder.children.all().update(parent=folder.parent)

            folder.delete()

            messages.info(request,
                          _(u'Folder <em>{0}</em>, deleted.').format(
                              folder.name),
                          extra_tags=u'safe')

        return redirect('source_selector')

    return HttpResponseForbidden()
