PYTHON ?= python3
MAP ?= maps/easy/01_linear_path.txt

.PHONY: install run run-text debug test clean lint lint-strict

install:
	$(PYTHON) -m pip install flake8 mypy pygame

run:
	$(PYTHON) main.py $(MAP)

run-text:
	$(PYTHON) main.py $(MAP) --no-gui

debug:
	$(PYTHON) -m pdb main.py $(MAP)

test:
	$(PYTHON) -m unittest discover -s tests -t .

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache venv

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict
