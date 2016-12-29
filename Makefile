check:
	python setup.py $@ -mrs
	flake8
	pytest-2.7
	pytest --cov --cov-fail-under=100

clean:
	hg st -in | xargs rm
	rm -rf build dist multimethod.egg-info

dist:
	python setup.py sdist bdist_wheel
	rst2html.py README.rst $@/README.html
