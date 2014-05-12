# See file COPYING distributed with sjs for copyright and license.

default : build

build : dist/sjs-0.1.1.tar.gz

dist/sjs-0.1.1.tar.gz : 
	python setup.py sdist

register : 
	python setup.py register

upload : 
	python setup.py sdist upload

check : 
	python setup.py check
	rst2html.py --halt=2 README.rst > /dev/null

clean : 
	rm -f MANIFEST

clobber : clean
	rm -rf dist

# eof
