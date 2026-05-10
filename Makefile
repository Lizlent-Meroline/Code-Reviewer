#Repo Analyzer — Makefile 
PORT := 8000

.PHONY: help install run dev clean

help:                ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'


install:             ## Install Python dependencies into a virtual environment
	python3 -m venv venv
	venv/bin/pip install --upgrade pip
	venv/bin/pip install -r requirements.txt

run:                 ## Start the server (production mode)
	uvicorn api:app --host 0.0.0.0 --port $(PORT)

dev:                 ## Start the server with hot-reload (development mode)
	uvicorn api:app --reload \
		--reload-dir analyzer \
		--reload-dir utils \
		--reload-dir src \
		--reload-include "api.py" \
		--reload-include "main.py" \
		--reload-include "auth.py" \
		--port $(PORT)

# Cleanup

clean:               ## Remove cloned repos, cache, and compiled Python files
	rm -rf repos/ cache/ __pycache__/ analyzer/__pycache__/ utils/__pycache__/
	find . -name "*.pyc" -delete
