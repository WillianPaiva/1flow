
# Rebuild scrollbars.js

To rebuild the contents of this folder from source:

	sudo npm install -g component
	cd ~/sources/1flow/oneflow/base/static/vendor/scrollbars
	component install Swatinem/scrollbars
	cd components/swatinem/scrollbars/*/
	component build
	cp build/build.css ../../../../scrollbars.css
	cp build/build.js ../../../../scrollbars.js
	cd ../../../..
	rm -rf components

This is far from clean if you have multiple `component` modules which have
common dependancies in the Django project, they will be included more than
once and this should be worked around.

PS: no need to minify, this is handled by `django-pipeline` when running
the `collectstatic` target.
