check:
	python setup.py $@ -mrs
	pep8
	py.test-2.7
	py.test-3.4 --cov --cov-fail-under=100

clean:
	hg st -in | xargs rm
	rm -rf dist multimethod.egg-info

dist:
	python setup.py sdist
	rst2html.py README.rst $@/README.html
