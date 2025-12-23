check:
	uv run pytest -s --cov

bench:
	uv run pytest --codspeed

lint:
	uvx ruff check
	uvx ruff format --check
	uvx ty check multimethod
	uvx mypy tests/static.py | grep -qv Any

html:
	uv run --group docs -w . mkdocs build
