.PHONY: install test demo schemas
install:
	bash scripts/install.sh
test:
	python -m pytest -q
demo:
	epiweekly demo --out demo-output
schemas:
	epiweekly schemas --out schemas
