all: check
	make -C docs html SPHINXOPTS=-W

check:
	python3 setup.py $@ -ms
	flake8
	pytest-2.7 --cov
	pytest --cov --cov-append --cov-fail-under=100

clean:
	hg st -in | xargs rm
	rm -rf build dist multimethod.egg-info

dist:
	python3 setup.py sdist bdist_wheel
