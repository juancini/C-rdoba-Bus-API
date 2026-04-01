up:
	uvicorn app.main:app --reload

sca:
	black .
	ruff check app/ --fix

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

test-watch:
	pytest-watch tests/