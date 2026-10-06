PY = .venv/bin/python
RUNS_DIR ?= runs/2026-10-06-SYNTHETIC

setup:
	python3 -m venv .venv
	$(PY) -m pip install -r requirements-dev.txt -r requirements-harness.txt
	test -f .env || cp .env.example .env

run:
	RUNS_DIR=$(RUNS_DIR) $(PY) -m uvicorn app.main:app --reload --port 8000

test:
	$(PY) -m ruff check app harness scripts tests
	RUNS_DIR=$(RUNS_DIR) PYTHONPATH=. $(PY) -m pytest -q

# regenerate the synthetic placeholder run and its summary (no GPU)
synthetic:
	PYTHONPATH=. $(PY) tests/make_synthetic_runs.py runs/2026-10-06-SYNTHETIC
	$(PY) scripts/build_runs_file.py runs/2026-10-06-SYNTHETIC

demo:
	RUNS_DIR=$(RUNS_DIR) PYTHONPATH=. $(PY) scripts/build_static_demo.py

.PHONY: setup run test synthetic demo
