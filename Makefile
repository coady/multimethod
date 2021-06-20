check:
	pytest -s --cov

lint:
	black --check .
	flake8
	mypy -p multimethod
	mypy tests/static.py | grep -qv Any

html:
	PYTHONPATH=$(PWD) mkdocs build
