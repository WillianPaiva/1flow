# "bootstrap" is like "make runable", but with the
# bare minimum for Fabric calls to succeed.
#
# SPARKS_PARALLEL=false is required for the
# first installation, but not subsequent runs.
bootstrap:
	echo $$VIRTUAL_ENV | grep 1flow
	pip install paramiko
	pip install -r config/dev-requirements.txt
	export SPARKS_PARALLEL=false ; fab local -H localhost sdf.fabfile.db_memcached sdf.fabfile.db_redis
	export SPARKS_PARALLEL=false ; fab local -H localhost sdf.fabfile.db_mongodb sdf.fabfile.db_postgresql
	export SPARKS_PARALLEL=false ; fab local -H localhost sdf.fabfile.dev_django_full
	sudo chown -R `whoami`: ~/.virtualenvs/1flow
	pip install Cython
	export SPARKS_PARALLEL=false ; fab local runable
	fab local minimal_content

runable:
	fab local runable

fullrunable:
	fab test runable
	fab prod runable

#runapp:
#	SPARKS_DJANGO_SETTINGS=chani_app ./manage.py runserver 0.0.0.0:8000

compass:
	(cd oneflow/core/static; compass watch)

collectstatic:
	./manage.py collectstatic

run: clean
	honcho -f Procfile.development start --quiet flower,shell,celery_beat

runweb: clean
	honcho -f Procfile.development start web

runworkers:
	honcho -f Procfile.development start flower beat worker permanent mongo --quiet flower,beat,shell

runpermanent:
	honcho -f Procfile.development start flower beat worker permanent --quiet flower,beat,shell,worker

	#,worker_high,worker_medium,worker_low,worker_fetch,worker_background,worker_swarm,worker_clean

runshell:
	honcho -f Procfile.development --quiet shell start shell

loglevel?=warning
autoscale?=1,1
processtype=gevent

worker:
	./manage.py celery worker -P $(processtype) --without-mingle --without-gossip --without-heartbeat --loglevel=$(loglevel) --autoscale=$(autoscale) --queues=$(queues)

clean:
	ps ax | grep manage.py | grep -v grep | grep -v shell_plus | awk '{print $$1}' | xargs kill -9 || true
	ps ax | grep celeryd | grep -v grep | awk '{print $$1}' | xargs kill -9 || true
	rm -f celery*.pid

purge:
	./manage.py celery purge

test:
	# REUSE fails with
	# "AttributeError: 'DatabaseCreation' object has no attribute '_rollback_works'"
	# until https://github.com/jbalogh/django-nose/pull/101 is merged.
	#REUSE_DB=1 ./manage.py test oneflow  --noinput --stop
	./manage.py test oneflow --noinput --stop

shell:
	./manage.py shell_plus

shell_classic:
	./manage.py shell_plus

#shellapp:
#	SPARKS_DJANGO_SETTINGS=chani_app ./manage.py shell

messages:
	fab local sdf.makemessages

compilemessages:
	fab local sdf.compilemessages

upgrade-requirements:
	(cd config && pip-review -vai)

update-requirements:
	(cd config && pip-dump)

requirements:
	fab local sdf.requirements

sparks:
	pip install -e git+https://github.com/1flow/sparks.git@develop#egg=sparks

syncdb:
	fab local sdf.syncdb
	fab local sdf.migrate

shell-superfast:
	git bkp || true
	git upa
	fab prod H:worker-01.1flow.io pull
	fab prod R:shell pull

web-superfast:
	git bkp || true
	git upa
	fab prod R:web pull restart:1

webshell-superfast:
	git bkp || true
	git upa
	fab prod H:worker-01.1flow.io pull
	fab prod R:web,shell pull restart:1

superfast: deploy-superfast

deploy-superfast:
	git bkp || true
	git upa
	fab prod pull restart:1

migrate-superfast:
	git bkp || true
	git upa
	fab prod pull migrate restart:1

web-collectstatic:
	git bkp || true
	git upa
	fab prod R:web pull
	fab prod -H 1flow.io -- rm -rf www/src/static
	fab prod -H 1flow.io sdf.collectstatic
	fab prod R:web restart:1

web-compilemessages:
	git bkp || true
	git upa
	fab prod R:web pull
	fab prod -H 1flow.io sdf.compilemessages
	fab prod R:web restart:1

webdeploy-collectcompile:
	git bkp || true
	git upa
	fab prod R:web pull
	fab prod -H 1flow.io -- rm -rf www/src/static
	fab prod -H 1flow.io sdf.collectstatic sdf.compilemessages
	fab prod R:web restart:1

webdeploy-environment:
	fab prod push_environment restart:1

allfixtures: datafixtures fixtures

datafixtures:
	@find . -name '*.json' -path '*/data/*'

fixtures:
	@find . -name '*.json' -path '*/fixtures/*'
