# DESIGN29 working paper. numbers.tex is generated from research/*.json;
# `make check` fails if it is stale or any reference does not resolve.
PDFLATEX := $(firstword $(wildcard $(HOME)/Library/TinyTeX/bin/universal-darwin/pdflatex) pdflatex)
BIBTEX   := $(firstword $(wildcard $(HOME)/Library/TinyTeX/bin/universal-darwin/bibtex) bibtex)
PYTHON   := $(firstword $(wildcard ../../../.venv/bin/python) python3)

.PHONY: all check clean
all: volalpha.pdf

numbers.tex: make_numbers.py ../../../research/volalpha.json ../../../research/volalpha_replication.json ../../../research/forensics.json
	$(PYTHON) make_numbers.py

volalpha.pdf: volalpha.tex volalpha.bib numbers.tex
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error volalpha.tex >/dev/null
	$(BIBTEX) volalpha >/dev/null
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error volalpha.tex >/dev/null
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error volalpha.tex >/dev/null

check:
	$(PYTHON) make_numbers.py --check
	$(PYTHON) ../check_references.py --bib volalpha.bib --tex volalpha.tex

clean:
	rm -f *.aux *.log *.out *.bbl *.blg *.toc
