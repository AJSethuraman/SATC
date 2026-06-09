# Convenience targets. `make` alone sets up the venv and runs the self-test.
#
# Usage:
#   make                 # install + self-test
#   make install         # create venv and install the tool
#   make selftest        # end-to-end pipeline check against known CIKs
#   make test            # run the offline unit test suite
#   make run ARGS="--sic 5140 --years 7 --out food_dist"
#   make clean           # remove venv, caches, generated outputs

PYTHON ?= python3
VENV   := .venv
PY     := $(VENV)/bin/python

.DEFAULT_GOAL := all
.PHONY: all install selftest test run clean

all: install selftest

$(VENV)/.installed:
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet -e ".[test]"
	touch $(VENV)/.installed

install: $(VENV)/.installed ## Create venv and install the tool
	@echo "Installed. Next: 'make selftest' or 'make run ARGS=\"--sic 5140 --out food_dist\"'"

selftest: install ## Verify the pipeline end-to-end (needs a contact email)
	./run.sh --self-test

test: install ## Run the offline unit test suite
	$(PY) -m pytest -q

run: install ## Run the tool: make run ARGS="--sic 5140 --years 7 --out food_dist"
	./run.sh $(ARGS)

clean: ## Remove venv, caches, and generated outputs
	rm -rf $(VENV) .edgar_cache .pytest_cache **/__pycache__ *.egg-info
	rm -f *.csv *.summary.md .edgar_contact
