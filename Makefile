PYTHON        = backend/.venv/Scripts/python
PIP           = backend/.venv/Scripts/pip
UVICORN       = backend/.venv/Scripts/uvicorn
ENV_FILE      = backend/.env
BACKEND_DIR   = backend
FRONTEND_DIR  = frontend
NPM           = npm

.PHONY: help setup install dev run frontend frontend-install frontend-build full-dev stop-dev restart-dev keys invite register character ws test clean sync-lore

# ── Ajuda ──────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  Aerus RPG"
	@echo ""
	@echo "  make setup      Cria venv e instala dependências"
	@echo "  make install    Instala/atualiza dependências no venv existente"
	@echo "  make dev        Inicia servidor com hot-reload"
	@echo "  make run        Inicia servidor sem hot-reload (produção local)"
	@echo "  make frontend   Inicia frontend Vite (http://localhost:5173)"
	@echo "  make frontend-install  Instala dependências do frontend"
	@echo "  make frontend-build    Gera build de produção do frontend"
	@echo "  make full-dev   Sobe backend + frontend em paralelo"
	@echo "  make stop-dev   Encerra frontend/backend (portas 5173 e 8000)"
	@echo "  make restart-dev Reinicia frontend/backend (stop-dev + full-dev)"
	@echo "  make keys       Gera FERNET_KEY e JWT_SECRET para o .env"
	@echo "  make invite     Cria um código de convite via API"
	@echo "  make register   Registra jogador  (INVITE= USER= PASS=)"
	@echo "  make character  Cria personagem   (TOKEN= NAME= FACTION=)"
	@echo "  make ws         Conecta WebSocket  (TOKEN=)"
	@echo "  make test       Executa testes"
	@echo "  make clean      Remove banco, chromadb e cache"
	@echo "  make sync-lore  Sync lore/ to backend/config/ and invalidate chroma_db"
	@echo ""

# ── Setup ──────────────────────────────────────────────────────────────────
setup:
	python -m venv backend/.venv
	$(PIP) install --upgrade pip --quiet
	$(PIP) install chromadb --prefer-binary --quiet
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt --quiet
	@echo ""
	@echo "  Pronto. Configure o .env antes de rodar:"
	@echo "  cp backend/.env.example backend/.env && make keys"
	@echo ""

install:
	$(PIP) install chromadb --prefer-binary --quiet
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt --quiet

# ── Servidor ───────────────────────────────────────────────────────────────
dev:
	@echo "Iniciando Aerus RPG em modo desenvolvimento..."
	cd $(BACKEND_DIR) && ../$(UVICORN) src.main:app --host 0.0.0.0 --port 8000 --reload --env-file .env

run:
	cd $(BACKEND_DIR) && ../$(UVICORN) src.main:app --host 0.0.0.0 --port 8000 --env-file .env

# ── Frontend ───────────────────────────────────────────────────────────────
frontend-install:
	cd $(FRONTEND_DIR) && $(NPM) install

frontend:
	@echo "Iniciando frontend em modo desenvolvimento..."
	cd $(FRONTEND_DIR) && $(NPM) run dev -- --host 0.0.0.0 --port 5173

frontend-build:
	cd $(FRONTEND_DIR) && $(NPM) run build

full-dev:
	@printf '#!/bin/bash\ncd "$(CURDIR)/backend"\nsource .venv/Scripts/activate\npython run.py\nexec bash\n' > .run-backend.sh
	@printf '#!/bin/bash\ncd "$(CURDIR)/frontend"\nnpm run dev -- --host 0.0.0.0 --port 5173\nexec bash\n' > .run-frontend.sh
	@echo "Abrindo terminais separados para backend (8000) e frontend (5173)..."
	mintty -t "Aerus Backend" bash .run-backend.sh &
	mintty -t "Aerus Frontend" bash .run-frontend.sh &

stop-dev:
	@echo "Encerrando processos nas portas 5173 (frontend) e 8000 (backend)..."
	@for port in 5173 8000; do \
		pid=$$(netstat -ano 2>/dev/null | grep ":$$port " | grep LISTENING | awk '{print $$5}' | head -n 1); \
		if [ -n "$$pid" ]; then \
			taskkill /PID $$pid /F >/dev/null 2>&1 || true; \
			echo "  Porta $$port finalizada (PID $$pid)."; \
		else \
			echo "  Porta $$port já estava livre."; \
		fi; \
	done

restart-dev: stop-dev full-dev

# ── Utilitários ────────────────────────────────────────────────────────────
keys:
	@echo ""
	@echo "FERNET_KEY=$$($(PYTHON) -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
	@echo "JWT_SECRET=$$($(PYTHON) -c 'import secrets; print(secrets.token_hex(32))')"
	@echo ""
	@echo "  Cole os valores acima no backend/.env"
	@echo ""

invite:
	@curl -s -X POST http://localhost:8000/admin/invite \
		-H "X-Admin-Secret: $(or $(ADMIN_SECRET),)" \
		| $(PYTHON) -c "import sys,json; d=json.load(sys.stdin); print('\n  Código de convite:', d.get('invite_code', d), '\n')"

register:
	@if [ -z "$(INVITE)" ]; then echo "  Uso: make register INVITE=XXXX-YYYY USER=heroi1 PASS=senha123"; exit 1; fi
	@curl -s -X POST http://localhost:8000/auth/redeem \
		-H "Content-Type: application/json" \
		-d "{\"invite_code\": \"$(INVITE)\", \"username\": \"$(USER)\", \"password\": \"$(PASS)\"}" \
		| $(PYTHON) -c "import sys,json; d=json.load(sys.stdin); t=d.get('access_token',''); print('\n  JWT:\n\n ', t, '\n') if t else print('\n  Erro:', d, '\n')"

character:
	@if [ -z "$(TOKEN)" ]; then echo "  Uso: make character TOKEN=eyJ... NAME=Aric FACTION=empire_valdrek"; exit 1; fi
	@curl -s -X POST http://localhost:8000/character \
		-H "Authorization: Bearer $(TOKEN)" \
		-H "Content-Type: application/json" \
		-d "{\"name\": \"$(NAME)\", \"faction\": \"$(FACTION)\"}" \
		| $(PYTHON) -c "import sys,json; print('\n', json.dumps(json.load(sys.stdin), ensure_ascii=False, indent=2), '\n')"

ws:
	@if [ -z "$(TOKEN)" ]; then echo "  Uso: make ws TOKEN=eyJ..."; exit 1; fi
	cd $(BACKEND_DIR) && ../$(PYTHON) ws_client.py $(TOKEN)

# ── Lore Sync ──────────────────────────────────────────────────────────────
sync-lore:
	@bash scripts/sync_lore.sh

# ── Testes ─────────────────────────────────────────────────────────────────
test:
	cd $(BACKEND_DIR) && ../$(PYTHON) -m pytest tests/ -v

# ── Limpeza ────────────────────────────────────────────────────────────────
clean:
	@echo "Removendo banco, chromadb e cache..."
	rm -f $(BACKEND_DIR)/aerus.db
	rm -rf $(BACKEND_DIR)/chroma_db
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Feito."
