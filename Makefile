PYTHON ?= .venv/bin/python

.PHONY: install test demo keygen

install:
	$(PYTHON) -m pip install -e '.[dev]'

test:
	$(PYTHON) -m pytest -q

demo:
	$(PYTHON) demo/run_demo.py

keygen:
	$(PYTHON) -m opensteps keygen --out-dir keys
