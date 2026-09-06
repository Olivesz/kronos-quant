# Build the preprint: figures (from research/*.json), then pdflatex + bibtex.
# pdflatex/bibtex: TinyTeX if present, else whatever is on PATH.
# Python: the repo venv (../../.venv); matplotlib is a paper-build-only dep.

PDFLATEX := $(firstword $(wildcard $(HOME)/Library/TinyTeX/bin/universal-darwin/pdflatex) pdflatex)
BIBTEX   := $(firstword $(wildcard $(HOME)/Library/TinyTeX/bin/universal-darwin/bibtex) bibtex)
PYTHON   := $(firstword $(wildcard ../../.venv/bin/python) python3)

FIGS = figures/battery_scorecard.pdf figures/e9_bits_configs.pdf \
       figures/deca3_inversion.pdf figures/deca4_wildfacts.pdf \
       figures/leverage_triangle.pdf figures/gate_schematic.pdf \
       figures/leverage_perasset.pdf figures/audit_matrix.pdf \
       figures/tuning_grid.pdf figures/score_se.pdf

.PHONY: all figures check arxiv clean

all: paper.pdf

# Three verification stages, all hard gates:
#   1. check_numbers.py     -- every derivable number vs research/*.json (derivation)
#   2. check_references.py  -- every bib entry vs its registered identifier
#   3. check_surfaces.py    -- every surface echoing a claim vs its source (propagation);
#                              also reads the GitHub description read-only unless hermetic
check:
	$(PYTHON) check_numbers.py
	$(PYTHON) check_references.py
	$(PYTHON) check_surfaces.py

# Clean arXiv submission tarball under dist/. Contents: paper.tex, the
# prebuilt figure PDFs, and paper.bbl (arXiv runs pdflatex, not bibtex, and
# consumes the shipped .bbl; paper.bib is deliberately not packed).
# The staged copy is smoke-built with two pdflatex passes before packing, so
# the tarball is known to compile standalone; the tarball itself contains
# only the pristine sources.
arxiv: paper.pdf check
	rm -rf dist
	mkdir -p dist/arxiv/figures
	cp paper.tex paper.bbl dist/arxiv/
	cp $(FIGS) dist/arxiv/figures/
	cd dist/arxiv && $(PDFLATEX) -interaction=nonstopmode -halt-on-error paper.tex >/dev/null \
		&& $(PDFLATEX) -interaction=nonstopmode -halt-on-error paper.tex >/dev/null
	@grep -qE "Warning.*(Citation|Reference).*undefined" dist/arxiv/paper.log \
		&& { echo "arxiv smoke build: undefined refs"; exit 1; } || true
	tar -C dist/arxiv -czf dist/arxiv.tar.gz paper.tex paper.bbl figures
	@echo "wrote dist/arxiv.tar.gz:"; tar -tzf dist/arxiv.tar.gz

paper.pdf: paper.tex paper.bib $(FIGS)
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error paper.tex
	$(BIBTEX) paper
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error paper.tex
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error paper.tex

$(FIGS): make_figures.py $(wildcard ../../research/*.json)
	$(PYTHON) make_figures.py

figures: $(FIGS)

clean:
	rm -f paper.aux paper.log paper.out paper.toc paper.bbl paper.blg paper.pdf
	rm -rf dist
