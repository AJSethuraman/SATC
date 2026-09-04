# SAT-C document pipeline. Run from client-documents/.
#
#   make doctor   what is blocking a real render
#   make check    does the demo package agree with itself?
#   make demo     the whole chain, lead -> PDFs, in one command
#   make price    set the firm's fees from hours x your rate
#   make hours    what each price buys, in hours, at that rate
#   make web      the browser front door: interview, and the wording editor
#   make fast     everything except the ones that open a document
#   make test     everything
.PHONY: help install doctor check demo price hours web fast test clean
help:
	@echo "make install   deps, including the Chromium PDF engine"
	@echo "make doctor    what is blocking a real render"
	@echo "make check     does the demo package agree with itself?"
	@echo "make demo      lead -> record -> the opening package as PDFs"
	@echo "make price     set the firm's fees from hours x your rate"
	@echo "make web       the browser front door, on http://127.0.0.1:5051"
	@echo "               -- run an interview, or edit the wording at /templates"
	@echo "make fast      the inner loop: everything but the nine that"
	@echo "               open a document. ~4 min instead of ~11."
	@echo "make test      the whole suite. Run this before you push."

install:
	pip install -r requirements.txt
	playwright install chromium

doctor:
	python cli.py doctor

# The other question. `doctor` says what is missing; this renders the
# package and asks whether the documents tell one story.
check:
	python cli.py check samples/tax-opening-package.json

web:
	python web.py

price:
	python cli.py price

hours:
	python cli.py hours

demo:
	python cli.py demo --out out/demo
	@echo
	@echo "Open the PDFs in out/demo/."

# THE INNER LOOP. Leaves out the nine `renders` tests, which are 64% of
# the wall clock and the ones that prove a client can read what this
# produces. The run says so at the end, in the place the result is read.
fast:
	python -m pytest -q -m "not renders"

# EVERYTHING, and the default. This is what CI runs.
test:
	python -m pytest -q

clean:
	rm -rf out .pytest_cache **/__pycache__
