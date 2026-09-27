.PHONY: install test test-map demo schemas
install:
	bash scripts/install.sh
test:
	python -m pytest -q
test-map:
	node tests/test_map_links.cjs
demo:
	atlas demo --out demo-output
schemas:
	atlas schemas --out schemas
