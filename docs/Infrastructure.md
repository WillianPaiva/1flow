# Databases

# Redis

## Configuration

    databases 20

## Numbering and accesses

- Main 1flow database (comments, ratings…) is **0**.
    - on preview we could set it to **10**, to avoid mixing prod/preview, except
      if it's a desired behavior (cutting edge code on real data).

- Celery broker and results is **1**.
    - except on preview, where is it **11**. This allows eventually running production and preview on the same Redis server.

- Redis-sessions is **2**,
    - on preview, **12**.


## Installing a new node

Actions in telegraphic style:

    # OVH: manager
    # edit DNS entries…

    # SSH: duncan
    # edit pg_hba.conf ?
    # edit ~groups/local_config/iptables/iptables.d/* ?

    # SSH: gurney
    sudo lxc-create -n worbi.1flow.io -t ubuntu -- -b olive
    # edit …/config -> lxc.network.ipv4 = …
    # edit /etc/rc.local

    # LOCAL
    # edit .ssh/config … user:olive
    cd ~/Dropbox

    # NOTE: not needed in sparks 2.0
    #fab -H worbi.1flow.io -- sudo apt-get -q update

    fab -H worbi.1flow.io tasks.lxc_base

    # SSH:worbi
    sudo adduser 1flow --force-badname
    sudo adduser 1flow sudo

    # LOCAL
    # edit .ssh/config … user:1flow
    ssh-copy-id worbi
    scp .bashrc worbi:

    # SSH: worbi
    install supervisor

    # LOCAL
    workon 1flow
    cd ~/sources/1flow

    # IF: worker
    fab -H worbi.1flow.io test deploy

    # IF: web
