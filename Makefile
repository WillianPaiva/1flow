runable:
	fab local runable
	fab test runable

fastdeploy:
	fab test fastdeploy

runapp:
	SPARKS_DJANGO_SETTINGS=chani_app ./manage.py runserver 0.0.0.0:8000

runserver:
	./manage.py runserver 0.0.0.0:8000


shell:
	./manage.py shell

shellapp:
	SPARKS_DJANGO_SETTINGS=chani_app ./manage.py shell
