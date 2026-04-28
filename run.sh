#!/bin/bash
# Watch only source files — ignores repos/, venv/, cache/, history/
uvicorn api:app --reload \
  --reload-dir analyzer \
  --reload-dir utils \
  --reload-dir src \
  --reload-include "api.py" \
  --reload-include "main.py" \
  --reload-include "auth.py"
