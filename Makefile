
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip


.PHONY: help install dev run clean

help:
	@printf "Available targets:\n"
	@printf "  install      Install runtime dependencies from requirements.txt\n"
	@printf "  dev          Same as install but also shows extra dev steps (if any)\n"
	@printf "  run          Launch Streamlit application\n"
	@printf "  clean        Remove Python bytecode and caches\n"


$(VENV_DIR):
	python3 -m venv $(VENV_DIR)

install: $(VENV_DIR)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

dev: install
	@printf "No additional dev steps configured.\n"


run: install
	$(VENV_DIR)/bin/streamlit run app.py

clean:
	@find . -path "*/__pycache__" -prune -exec rm -rf {} +
	@find . -name "*.pyc" -delete
	@find . -name "*.pyo" -delete
