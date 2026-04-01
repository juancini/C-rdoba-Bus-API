up:
	uvicorn app.main:app --reload
sca:
	black .
	ruff check app/ --fix