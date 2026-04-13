PYTHON       = backend/.venv/Scripts/python
PIP          = backend/.venv/Scripts/pip
UVICORN      = backend/.venv/Scripts/uvicorn
BACKEND_DIR  = backend
FRONTEND_DIR = frontend
NPM          = npm

.PHONY: help setup setup-all env-init install dev run frontend frontend-install frontend-build frontend-test frontend-lint full-dev stop-dev restart-dev keys invite register character ws sync-lore test backend-compile check e2e gm-eval-default gm-eval-core gm-eval-extended gm-eval-full clean clean-all

help:
	@$(info )
	@$(info   Aerus Game Master Platform)
	@$(info )
	@$(info   make setup            Create backend venv and install backend dependencies)
	@$(info   make setup-all        Backend + frontend install plus env scaffolding)
	@$(info   make env-init         Create local env files when missing)
	@$(info   make install          Update backend dependencies in the existing venv)
	@$(info   make dev              Start backend with hot reload)
	@$(info   make run              Start backend without hot reload)
	@$(info   make frontend         Start the Vite frontend)
	@$(info   make frontend-install Install frontend dependencies)
	@$(info   make frontend-build   Build the frontend)
	@$(info   make frontend-test    Run frontend tests)
	@$(info   make frontend-lint    Run frontend lint)
	@$(info   make full-dev         Start backend + frontend in separate terminals)
	@$(info   make stop-dev         Stop local processes on ports 5173 and 8000)
	@$(info   make restart-dev      Restart backend + frontend)
	@$(info   make keys             Generate FERNET_KEY and JWT_SECRET)
	@$(info   make invite           Create an invite code via API)
	@$(info   make register         Register a player (INVITE= USER= PASS=))
	@$(info   make character        Create a character (TOKEN= NAME= RACE= FACTION= BACKSTORY=))
	@$(info   make ws               Connect the test WebSocket client (TOKEN=))
	@$(info   make sync-lore        Sync lore/ to backend/config/ and invalidate ChromaDB)
	@$(info   make test             Run backend tests)
	@$(info   make backend-compile  Compile backend sources as a quick syntax check)
	@$(info   make check            Run backend tests, backend compile, frontend tests, lint, and build)
	@$(info   make e2e              Run Playwright end-to-end tests)
	@$(info   make gm-eval-default  Run the fast critical-path GM evaluation profile)
	@$(info   make gm-eval-core     Run the full core-tier GM evaluation profile)
	@$(info   make gm-eval-extended Run the extended GM evaluation profile)
	@$(info   make gm-eval-full     Run the full GM baseline evaluation)
	@$(info   make clean            Remove DB, caches, and ChromaDB artifacts)
	@$(info   make clean-all        clean + frontend dist cleanup)
	@$(info )
	@:

setup:
	python -m venv $(BACKEND_DIR)/.venv
	$(PIP) install --upgrade pip --quiet
	$(PIP) install chromadb --prefer-binary --quiet
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt --quiet
	@echo ""
	@echo "  Backend ready. Run 'make env-init' and then 'make keys'."
	@echo ""

env-init:
	@if [ ! -f "$(BACKEND_DIR)/.env" ]; then cp "$(BACKEND_DIR)/.env.example" "$(BACKEND_DIR)/.env"; echo "  Created $(BACKEND_DIR)/.env"; else echo "  $(BACKEND_DIR)/.env already exists"; fi
	@if [ -f "$(FRONTEND_DIR)/.env.local.example" ] && [ ! -f "$(FRONTEND_DIR)/.env.local" ]; then cp "$(FRONTEND_DIR)/.env.local.example" "$(FRONTEND_DIR)/.env.local"; echo "  Created $(FRONTEND_DIR)/.env.local"; elif [ -f "$(FRONTEND_DIR)/.env.local" ]; then echo "  $(FRONTEND_DIR)/.env.local already exists"; else echo "  No frontend env template found"; fi

setup-all: setup frontend-install env-init

install:
	$(PIP) install chromadb --prefer-binary --quiet
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt --quiet

dev:
	@echo "Starting backend in development mode..."
	cd $(BACKEND_DIR) && ../$(UVICORN) src.main:app --host 0.0.0.0 --port 8000 --reload --env-file .env

run:
	cd $(BACKEND_DIR) && ../$(UVICORN) src.main:app --host 0.0.0.0 --port 8000 --env-file .env

frontend-install:
	cd $(FRONTEND_DIR) && $(NPM) install

frontend:
	@echo "Starting frontend in development mode..."
	cd $(FRONTEND_DIR) && $(NPM) run dev -- --host 0.0.0.0 --port 5173

frontend-build:
	cd $(FRONTEND_DIR) && $(NPM) run build

build: frontend-build

serve:
	cd $(BACKEND_DIR) && ../$(UVICORN) src.main:app --host 0.0.0.0 --port 8000 --env-file .env

tunnel:
	@echo "Run in a separate terminal: ngrok http 8000"
	@echo "Or: cloudflared tunnel --url http://localhost:8000"

frontend-test:
	cd $(FRONTEND_DIR) && $(NPM) run test

frontend-lint:
	cd $(FRONTEND_DIR) && $(NPM) run lint

full-dev:
	@printf '#!/bin/bash\ncd "$(CURDIR)/backend"\nsource .venv/Scripts/activate\npython run.py\nexec bash\n' > .run-backend.sh
	@printf '#!/bin/bash\ncd "$(CURDIR)/frontend"\nnpm run dev -- --host 0.0.0.0 --port 5173\nexec bash\n' > .run-frontend.sh
	@echo "Opening separate terminals for backend (8000) and frontend (5173)..."
	mintty -t "Aerus Backend" bash .run-backend.sh &
	mintty -t "Aerus Frontend" bash .run-frontend.sh &

stop-dev:
	@echo "Stopping processes on ports 5173 and 8000..."
	@for port in 5173 8000; do \
		pid=$$(netstat -ano 2>/dev/null | grep ":$$port " | grep LISTENING | awk '{print $$5}' | head -n 1); \
		if [ -n "$$pid" ]; then \
			taskkill /PID $$pid /F >/dev/null 2>&1 || true; \
			echo "  Port $$port stopped (PID $$pid)."; \
		else \
			echo "  Port $$port was already free."; \
		fi; \
	done

restart-dev: stop-dev full-dev

keys:
	@echo ""
	@echo "FERNET_KEY=$$($(PYTHON) -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
	@echo "JWT_SECRET=$$($(PYTHON) -c 'import secrets; print(secrets.token_hex(32))')"
	@echo ""
	@echo "  Paste the values above into backend/.env"
	@echo ""

invite:
	@curl -s -X POST http://localhost:8000/admin/invite \
		-H "X-Admin-Secret: $(or $(ADMIN_SECRET),)" \
		| $(PYTHON) -c "import sys,json; d=json.load(sys.stdin); print('\n  Invite code:', d.get('invite_code', d), '\n')"

register:
	@if [ -z "$(INVITE)" ]; then echo "  Usage: make register INVITE=XXXX-YYYY USER=hero1 PASS=secret123"; exit 1; fi
	@if [ -z "$(USER)" ]; then echo "  USER is required"; exit 1; fi
	@if [ -z "$(PASS)" ]; then echo "  PASS is required"; exit 1; fi
	@curl -s -X POST http://localhost:8000/auth/redeem \
		-H "Content-Type: application/json" \
		-d "{\"invite_code\": \"$(INVITE)\", \"username\": \"$(USER)\", \"password\": \"$(PASS)\"}" \
		| $(PYTHON) -c "import sys,json; d=json.load(sys.stdin); t=d.get('access_token',''); print('\n  JWT:\n\n ', t, '\n') if t else print('\n  Error:', d, '\n')"

character:
	@if [ -z "$(TOKEN)" ]; then echo "  Usage: make character TOKEN=eyJ... NAME=Aric RACE=human FACTION=empire_valdrek BACKSTORY='Former city guard'"; exit 1; fi
	@if [ -z "$(NAME)" ]; then echo "  NAME is required"; exit 1; fi
	@if [ -z "$(RACE)" ]; then echo "  RACE is required"; exit 1; fi
	@if [ -z "$(FACTION)" ]; then echo "  FACTION is required"; exit 1; fi
	@if [ -z "$(BACKSTORY)" ]; then echo "  BACKSTORY is required"; exit 1; fi
	@curl -s -X POST http://localhost:8000/character \
		-H "Authorization: Bearer $(TOKEN)" \
		-H "Content-Type: application/json" \
		-d "{\"name\": \"$(NAME)\", \"race\": \"$(RACE)\", \"faction\": \"$(FACTION)\", \"backstory\": \"$(BACKSTORY)\"}" \
		| $(PYTHON) -c "import sys,json; print('\n', json.dumps(json.load(sys.stdin), ensure_ascii=False, indent=2), '\n')"

ws:
	@if [ -z "$(TOKEN)" ]; then echo "  Usage: make ws TOKEN=eyJ..."; exit 1; fi
	cd $(BACKEND_DIR) && ../$(PYTHON) ws_client.py $(TOKEN)

sync-lore:
	@bash scripts/sync_lore.sh

test:
	cd $(BACKEND_DIR) && ../$(PYTHON) -m pytest tests/ -v

backend-compile:
	cd $(BACKEND_DIR) && ../$(PYTHON) -m compileall src eval

check: test backend-compile frontend-test frontend-lint frontend-build

e2e:
	cd $(BACKEND_DIR) && ../$(PIP) install -r requirements-e2e.txt --quiet && ../$(PYTHON) -m pytest e2e/test_app_e2e_playwright.py -v -s

gm-eval-default:
	cd $(BACKEND_DIR) && AERUS_EVAL_PROFILE=default ../$(PYTHON) eval/gm_eval.py

gm-eval-core:
	cd $(BACKEND_DIR) && AERUS_EVAL_PROFILE=core-full ../$(PYTHON) eval/gm_eval.py

gm-eval-extended:
	cd $(BACKEND_DIR) && AERUS_EVAL_PROFILE=extended ../$(PYTHON) eval/gm_eval.py

gm-eval-full:
	cd $(BACKEND_DIR) && AERUS_EVAL_PROFILE=full-baseline ../$(PYTHON) eval/gm_eval.py

clean:
	@echo "Removing DB, ChromaDB, and Python caches..."
	rm -f $(BACKEND_DIR)/aerus.db
	rm -rf $(BACKEND_DIR)/chroma_db
	rm -rf chroma_db
	rm -rf $(BACKEND_DIR)/.pytest_cache $(BACKEND_DIR)/.pytest-tmp $(BACKEND_DIR)/.tmp_pytest
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Done."

clean-all: clean
	rm -rf $(FRONTEND_DIR)/dist
