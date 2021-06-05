check:
	pytest --cov

lint:
	black --check .
	flake8
	mypy -p multimethod

html:
	PYTHONPATH=$(PWD) mkdocs build
