#!/usr/bin/env sh

. .venv/bin/activate
python -m mypy ./src/omotes_sdk ./unit_test/
