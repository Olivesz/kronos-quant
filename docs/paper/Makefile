# Build the preprint: figures (from research/*.json) then pdflatex twice.
# pdflatex: TinyTeX if present, else whatever is on PATH.
# Python: the repo venv (../../.venv); matplotlib is a paper-build-only dep.

PDFLATEX := $(firstword $(wildcard $(HOME)/Library/TinyTeX/bin/universal-darwin/pdflatex) pdflatex)
PYTHON   := $(firstword $(wildcard ../../.venv/bin/python) python3)

FIGS = figures/battery_scorecard.pdf figures/e9_bits_configs.pdf \
       figures/deca3_inversion.pdf figures/deca4_wildfacts.pdf \
       figures/leverage_triangle.pdf figures/gate_schematic.pdf

.PHONY: all figures clean

all: paper.pdf

paper.pdf: paper.tex $(FIGS)
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error paper.tex
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error paper.tex

$(FIGS): make_figures.py $(wildcard ../../research/*.json)
	$(PYTHON) make_figures.py

figures: $(FIGS)

clean:
	rm -f paper.aux paper.log paper.out paper.toc paper.bbl paper.blg paper.pdf
