# Regenerate every figure. `make` after editing a scene script.
FIGURES := $(wildcard figures/*.py)
SVGS := $(patsubst figures/%.py,out/%.svg,$(FIGURES))

.PHONY: all png clean
all: $(SVGS)

out/%.svg: figures/%.py $(wildcard csi/*.py)
	python3 $<

# PNG previews, for eyeballing a change or dropping into a slide.
png: all
	for f in out/*.svg; do inkscape --export-type=png --export-dpi=150 \
	  --export-filename=$${f%.svg}.png $$f >/dev/null 2>&1; done

clean:
	rm -f out/*.svg out/*.png
