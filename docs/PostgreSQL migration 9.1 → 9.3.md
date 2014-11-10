
See http://blog.1flow.io/post/101834978423/quick-update-migrating-postgresql-from-9-1-to-9-3 for full details.

    echo "deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main" > /etc/apt/sources.list.d/pgdg.list
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
    sudo apt-get update
    sudo apt-get upgrade

    sudo apt-get install postgresql-9.3 postgresql-contrib-9.3

    sudo service postgresql stop 9.3
    sudo service postgresql stop 9.1

    /usr/lib/postgresql/9.3/bin/pg_upgrade \
    	-b /usr/lib/postgresql/9.1/bin/ \
    	-B /usr/lib/postgresql/9.3/bin/ \
    	-d /var/lib/postgresql/9.1/main \
    	-D /var/lib/postgresql/9.3/main \
    	-o ' -c config_file=/etc/postgresql/9.1/main/postgresql.conf' \
    	-O ' -c config_file=/etc/postgresql/9.3/main/postgresql.conf'


