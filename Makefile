# Variables
BACKEND_DIR = backend
VENV = $(BACKEND_DIR)/venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip
UVICORN = $(VENV)/bin/uvicorn

# Colors for pretty printing
BOLD=\033[1m
RESET=\033[0m
GREEN=\033[32m

# --- Main Commands ---

.PHONY: help setup install run clean test

help:
	@echo "$(BOLD)Available commands:$(RESET)"
	@echo "  make setup   - Create the Python virtual environment (venv)"
	@echo "  make install - Install project dependencies"
	@echo "  make run     - Run the development server (Hot Reload)"
	@echo "  make test    - Run unit and integration tests"
	@echo "  make clean   - Remove cache files and the virtual environment"

setup:
	@echo "$(BOLD)🐍 Creating virtual environment...$(RESET)"
	python3 -m venv $(VENV)
	@echo "$(GREEN)✅ Environment created.$(RESET)"

install:
	@echo "$(BOLD)⬇️  Installing dependencies...$(RESET)"
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt
	@echo "$(GREEN)✅ Dependencies installed.$(RESET)"

run:
	@echo "$(BOLD)🚀 Starting server...$(RESET)"
	# Enter backend directory and invoke uvicorn from the venv relative path
	cd $(BACKEND_DIR) && ../$(UVICORN) main:app --reload

test:
	@echo "$(BOLD)🧪 Running tests...$(RESET)"
	# Enter backend directory and invoke pytest using the venv python binary
	cd $(BACKEND_DIR) && ../$(PYTHON) -m pytest
	@echo "$(GREEN)✅ Tests passed.$(RESET)"

clean:
	@echo "$(BOLD)🧹 Cleaning up...$(RESET)"
	rm -rf $(BACKEND_DIR)/__pycache__
	rm -rf $(BACKEND_DIR)/src/__pycache__
	rm -rf $(BACKEND_DIR)/tests/__pycache__
	rm -rf $(VENV)
	@echo "$(GREEN)✅ Full cleanup complete (including venv).$(RESET)"
