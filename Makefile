PYTHON ?= python3
VENV = .venv
BIN = $(VENV)/bin
PY = $(shell test -x $(BIN)/python3 && echo $(BIN)/python3 || echo $(PYTHON))
MAP ?=

.PHONY: install run run-text debug test clean fclean lint lint-strict help

install:
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install flake8 mypy pygame

run:
	$(PY) main.py $(MAP)

run-text:
	$(PY) main.py $(MAP) --no-gui

debug:
	$(PY) -m pdb main.py $(MAP)

test:
	$(PY) -m unittest discover -s tests -t .

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

fclean: clean
	rm -rf $(VENV)

lint:
	$(PY) -m flake8 .
	$(PY) -m mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	$(PY) -m flake8 .
	$(PY) -m mypy . --strict

help:
	@echo "make install      create .venv and install flake8, mypy, pygame"
	@echo "make run          run (MAP=<file>; without MAP you choose from a list)"
	@echo "make run-text     text only, no window (MAP=<file>)"
	@echo "make debug        run under pdb (MAP=<file>)"
	@echo "make test         run the unit tests (when the tests folder exists)"
	@echo "make lint         flake8 + mypy"
	@echo "make lint-strict  flake8 + mypy --strict"
	@echo "make clean        remove caches"
	@echo "make fclean       clean + remove .venv"
