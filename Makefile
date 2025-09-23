.PHONY: help api-run api-dev ingest-run app-run app-web clean

help:
	@echo "Available commands:"
	@echo "  make api-dev    - Run API in development mode"
	@echo "  make app-web    - Run Flutter app for web"
	@echo "  make clean      - Clean build files"

api-dev:
	cd api && source venv/bin/activate && python main.py

api-install:
	cd api && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

app-web:
	cd app && flutter run -d chrome

app-build-web:
	cd app && flutter build web

clean:
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	cd app && flutter clean
