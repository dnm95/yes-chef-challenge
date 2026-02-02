# ==========================================
# CONFIGURATION & VARIABLES
# ==========================================

# Backend Paths
BACKEND_DIR = backend
VENV_DIR = venv
# Explicit path to binaries to avoid system conflicts
PYTHON_BIN = ./$(VENV_DIR)/bin/python3
PIP_BIN = ./$(VENV_DIR)/bin/pip
UVICORN_BIN = ./$(VENV_DIR)/bin/uvicorn

# Frontend Paths
FRONTEND_DIR = frontend

# Colors for terminal output
BOLD=\033[1m
RESET=\033[0m
GREEN=\033[32m
CYAN=\033[36m

# ==========================================
# COMMANDS
# ==========================================

.PHONY: help setup install install-backend install-frontend run-backend run-frontend test clean

help:
	@echo "$(BOLD)Project Commands:$(RESET)"
	@echo "  $(CYAN)make setup$(RESET)          - Create Python Virtual Environment (backend)"
	@echo "  $(CYAN)make install$(RESET)        - Install BOTH Backend and Frontend dependencies"
	@echo "  $(CYAN)make run-backend$(RESET)    - Start FastAPI Server (localhost:8000)"
	@echo "  $(CYAN)make run-frontend$(RESET)   - Start Next.js App (localhost:3000)"
	@echo "  $(CYAN)make test$(RESET)           - Run Backend Tests"
	@echo "  $(CYAN)make clean$(RESET)          - Remove all artifacts and environments"

# --- 1. SETUP ---
setup:
	@echo "$(BOLD)🐍 Setting up Python Virtual Environment...$(RESET)"
	# We perform a clean setup to ensure no conflicts
	rm -rf $(BACKEND_DIR)/$(VENV_DIR)
	cd $(BACKEND_DIR) && python3 -m venv $(VENV_DIR)
	@echo "$(GREEN)✅ Environment created at $(BACKEND_DIR)/$(VENV_DIR)$(RESET)"

# --- 2. INSTALLATION (Monorepo Style) ---
install: install-backend install-frontend
	@echo "$(GREEN)✅ All dependencies (Python & Node) installed successfully.$(RESET)"

install-backend:
	@echo "$(BOLD)⬇️  Installing Backend dependencies (Python)...$(RESET)"
	cd $(BACKEND_DIR) && $(PIP_BIN) install --upgrade pip
	cd $(BACKEND_DIR) && $(PIP_BIN) install -r requirements.txt

install-frontend:
	@echo "$(BOLD)⬇️  Installing Frontend dependencies (Node)...$(RESET)"
	cd $(FRONTEND_DIR) && npm install

# --- 3. RUNTIME ---
run-backend:
	@echo "$(BOLD)🚀 Starting FastAPI Server...$(RESET)"
	cd $(BACKEND_DIR) && $(UVICORN_BIN) main:app --reload

run-frontend:
	@echo "$(BOLD)⚛️  Starting Next.js Frontend...$(RESET)"
	cd $(FRONTEND_DIR) && npm run dev

# --- 4. TESTING ---
test:
	@echo "$(BOLD)🧪 Running Backend Tests...$(RESET)"
	cd $(BACKEND_DIR) && $(PYTHON_BIN) -m pytest
	@echo "$(GREEN)✅ Tests Passed.$(RESET)"

# --- 5. CLEANUP ---
clean:
	@echo "$(BOLD)🧹 Cleaning up project...$(RESET)"
	# Clean Backend
	rm -rf $(BACKEND_DIR)/__pycache__
	rm -rf $(BACKEND_DIR)/src/__pycache__
	rm -rf $(BACKEND_DIR)/tests/__pycache__
	rm -rf $(BACKEND_DIR)/$(VENV_DIR)
	# Clean Frontend
	rm -rf $(FRONTEND_DIR)/.next
	rm -rf $(FRONTEND_DIR)/node_modules
	@echo "$(GREEN)✅ Full cleanup complete.$(RESET)"
