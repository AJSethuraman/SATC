# SAT-C document pipeline. Run from client-documents/.
#
#   make doctor   what is blocking a real render
#   make demo     the whole chain, lead -> PDFs, in one command
#   make price    set the firm's fees from hours x your rate
#   make test     everything
.PHONY: help install doctor demo price test clean
help:
	@echo "make install   deps, including the Chromium PDF engine"
	@echo "make doctor    what is blocking a real render"
	@echo "make demo      lead -> record -> the opening package as PDFs"
	@echo "make price     set the firm's fees from hours x your rate"
	@echo "make test      the whole suite"

install:
	pip install -r requirements.txt
	playwright install chromium

doctor:
	python cli.py doctor

price:
	python cli.py price

demo:
	python cli.py demo --out out/demo
	@echo
	@echo "Open the PDFs in out/demo/."

test:
	python -m pytest -q

clean:
	rm -rf out .pytest_cache **/__pycache__
