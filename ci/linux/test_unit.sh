#!/bin/bash

if [[ "$OSTYPE" != "win32" && "$OSTYPE" != "msys" ]]; then
  . .venv/bin/activate
fi
PYTHONPATH='$PYTHONPATH:src/' pytest --junit-xml=test-results.xml unit_test/
