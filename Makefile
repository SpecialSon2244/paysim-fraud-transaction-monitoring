VENV=.venv
PY=$(VENV)/bin/python
.PHONY: all setup data build evaluate charts tableau test dashboard clean
all: setup data build evaluate charts tableau test

setup: $(VENV)/.installed     ## virtual environment with the packages in requirements.txt
$(VENV)/.installed: requirements.txt
	python3 -m venv $(VENV) && $(VENV)/bin/pip install -q -r requirements.txt && touch $@

data:        ## download the PaySim CSV (494 MB, public Hugging Face mirror) to data/raw/, check size + sha256
	$(PY) src/download.py
build:       ## Polars CSV -> Parquet, then DuckDB runs sql/01..08 (rules) -> data/paysim.duckdb
	$(PY) src/build.py
evaluate:    ## precision / recall / alert volume per rule and rule set -> exports/*.csv, docs/findings.json
	$(PY) src/evaluate.py > /dev/null
charts:      ## static Plotly PNGs (kaleido) -> docs/charts/
	$(PY) src/charts.py
tableau:     ## tidy Excel extract for Tableau Public -> tableau/paysim_fraud_monitoring.xlsx
	$(PY) src/tableau_extract.py
test:        ## pytest: SQL rule logic on a fixture, full build, exports, doc numbers, xlsx, dashboard
	$(PY) -m pytest -q
dashboard:   ## Streamlit dashboard on http://localhost:8501
	$(VENV)/bin/streamlit run app.py
clean:
	rm -rf data/staging data/paysim.duckdb
