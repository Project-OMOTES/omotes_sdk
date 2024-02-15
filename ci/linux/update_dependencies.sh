#!/bin/bash

if [[ "$OSTYPE" != "win32" && "$OSTYPE" != "msys" ]]; then
  . .venv/bin/activate
fi
pip-compile --output-file=requirements.txt pyproject.toml
pip-compile --extra=dev --output-file=dev-requirements.txt pyproject.toml
