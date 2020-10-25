all: check
	PYTHONPATH=$(PWD) mkdocs build

check:
	python3 setup.py $@ -ms
	black -q --$@ .
	flake8
	mypy -p multimethod
	pytest --cov --cov-fail-under=100
