check:
	uv run pytest -s --cov

bench:
	uv run pytest --codspeed

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy -p multimethod
	uv run mypy tests/static.py | grep -qv Any

html:
	uv run --with multimethod mkdocs build
