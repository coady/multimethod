check:
	pytest -s --cov

lint:
	python3 -m black --check .
	flake8
	mypy -p multimethod
	mypy tests/static.py | grep -qv Any

html:
	PYTHONPATH=$(PWD) python3 -m mkdocs build
