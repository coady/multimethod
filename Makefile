all: check
	make -C docs html SPHINXOPTS=-W

check:
	python3 setup.py $@ -ms
	black -q --$@ .
	flake8
	pytest-2.7 --cov
	pytest --cov --cov-append --cov-fail-under=100
