# -*- coding: utf-8 -*-
u"""
Copyright 2012-2014 Olivier Cortès <oc@1flow.io>.

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

import os
import psutil
import logging

from collections import namedtuple


LOGGER = logging.getLogger(__name__)


disk_ntuple = namedtuple('partition', 'device mountpoint fstype')
usage_ntuple = namedtuple('usage', 'total used free percent')


def disk_partitions(all=False):
    """Return all mountd partitions as a nameduple.

    If all == False return phyisical partitions only.
    """

    phydevs = []
    f = open("/proc/filesystems", "r")

    for line in f:
        if not line.startswith("nodev"):
            phydevs.append(line.strip())

    retlist = []
    f = open('/etc/mtab', "r")
    dev_done = []

    for line in f:
        if not all and line.startswith('none'):
            continue

        fields = line.split()
        device = fields[0]
        mountpoint = fields[1]
        fstype = fields[2]

        if (not all and fstype not in phydevs) or device in dev_done:
            continue

        if device == 'none':
            device = ''

        retlist.append(disk_ntuple(device, mountpoint, fstype))

        # Avoid doing devices twice. This happens in LXCs with bind mounts.
        # All we need is that / is mounted before other for it to show
        # instead of them. Hoppefully, it should always be the case ;-)
        dev_done.append(device)

    return retlist


def disk_usage(path):
    """Return disk usage associated with path."""
    st = os.statvfs(path)
    free = (st.f_bavail * st.f_frsize)
    total = (st.f_blocks * st.f_frsize)
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    try:
        percent = (float(used) / total) * 100

    except ZeroDivisionError:
        percent = 0

    # NB: the percentage is -5% than what shown by df due to
    # reserved blocks that we are currently not considering:
    # http://goo.gl/sWGbH
    return usage_ntuple(total, used, free, round(percent, 1))


def find_mount_point(path):
    """ Find the mount point of a given path. """

    path = os.path.abspath(path)
    while not os.path.ismount(path):
        path = os.path.dirname(path)
    return path


def memory():
    """ Return memory usage for local machine. """

    # svmem(total=8289701888L, available=1996591104L, percent=75.9,
    #       used=8050712576L, free=238989312L, active=6115635200,
    #       inactive=1401483264, buffers=40718336L, cached=1716883456)

    psutil_vm = psutil.virtual_memory()

    memory = {
        'raw': psutil_vm,
        'active_pct': psutil_vm.active * 100.0 / psutil_vm.total,
        'inactive_pct': psutil_vm.inactive * 100.0 / psutil_vm.total,
        'buffers_pct': psutil_vm.buffers * 100.0 / psutil_vm.total,
        'cached_pct': (psutil_vm.cached * 100.0 / psutil_vm.total),
    }

    memory['used_pct'] = (
        memory['active_pct']
        + memory['inactive_pct']
        + memory['buffers_pct']
        + memory['cached_pct']
    )

    if memory['used_pct'] > 100:
        # Sometimes, the total is > 100 (I've
        # seen 105.xxx many times while developing).
        memory['cached_pct'] = memory['cached_pct'] - (
            memory['used_pct'] - 100.0)

    return memory


def partitions_status():
    """ The wrap-all-in-one function for templates rendering. """

    return {
        part: disk_usage(part.mountpoint)
        for part in disk_partitions()
    }
