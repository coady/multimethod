check:
	python -m pytest -s --cov

lint:
	black --check .
	ruff .
	mypy -p multimethod
	mypy tests/static.py | grep -qv Any

html:
	PYTHONPATH=$(PWD) python -m mkdocs build
