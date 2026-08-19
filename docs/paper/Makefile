# Build the preprint: figures (from research/*.json) then pdflatex twice.
# pdflatex: TinyTeX if present, else whatever is on PATH.
# Python: the repo venv (../../.venv); matplotlib is a paper-build-only dep.

PDFLATEX := $(firstword $(wildcard $(HOME)/Library/TinyTeX/bin/universal-darwin/pdflatex) pdflatex)
PYTHON   := $(firstword $(wildcard ../../.venv/bin/python) python3)

FIGS = figures/battery_scorecard.pdf figures/e9_bits_configs.pdf \
       figures/deca3_inversion.pdf figures/deca4_wildfacts.pdf \
       figures/leverage_triangle.pdf figures/gate_schematic.pdf

.PHONY: all figures check arxiv clean

all: paper.pdf

# Verify every derivable number in paper.tex against research/*.json and the
# battery code's thresholds. Exits nonzero on any mismatch.
check:
	$(PYTHON) check_numbers.py

# Clean arXiv submission tarball under dist/. Contents: paper.tex + the
# prebuilt figure PDFs (bibliography is inline thebibliography — no .bbl).
# The staged copy is smoke-built with two pdflatex passes before packing, so
# the tarball is known to compile standalone; the tarball itself contains
# only the pristine sources.
arxiv: paper.pdf check
	rm -rf dist
	mkdir -p dist/arxiv/figures
	cp paper.tex dist/arxiv/
	cp $(FIGS) dist/arxiv/figures/
	cd dist/arxiv && $(PDFLATEX) -interaction=nonstopmode -halt-on-error paper.tex >/dev/null \
		&& $(PDFLATEX) -interaction=nonstopmode -halt-on-error paper.tex >/dev/null
	@grep -qE "Warning.*(Citation|Reference).*undefined" dist/arxiv/paper.log \
		&& { echo "arxiv smoke build: undefined refs"; exit 1; } || true
	tar -C dist/arxiv -czf dist/arxiv.tar.gz paper.tex figures
	@echo "wrote dist/arxiv.tar.gz:"; tar -tzf dist/arxiv.tar.gz

paper.pdf: paper.tex $(FIGS)
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error paper.tex
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error paper.tex

$(FIGS): make_figures.py $(wildcard ../../research/*.json)
	$(PYTHON) make_figures.py

figures: $(FIGS)

clean:
	rm -f paper.aux paper.log paper.out paper.toc paper.bbl paper.blg paper.pdf
	rm -rf dist
