# PromptPay Monitoring Dashboard — Makefile
# Usage: make <target>
# Requires: DOCKER_USERNAME env var for push/pull commands
#   export DOCKER_USERNAME=yourname

DOCKER_USERNAME ?= eakkaluk1987
IMAGE_TAG ?= latest

# ── Local development ────────────────────────────────────────────────────────

dev:
	## Run locally without Docker (requires venv)
	venv/bin/uvicorn backend.main:app --port 8000 --reload &
	venv/bin/streamlit run frontend/dashboard.py --server.port 8501

# ── Docker (build & run locally) ─────────────────────────────────────────────

up:
	## Build images and start all containers
	docker compose up --build

down:
	## Stop and remove containers
	docker compose down

logs:
	## Follow container logs
	docker compose logs -f

restart:
	## Restart all containers
	docker compose restart

# ── Docker Hub (publish & distribute) ────────────────────────────────────────

build:
	## Build images with Docker Hub tags
	DOCKER_USERNAME=$(DOCKER_USERNAME) IMAGE_TAG=$(IMAGE_TAG) \
	docker compose build

push: build
	## Build and push images to Docker Hub
	@if [ -z "$(DOCKER_USERNAME)" ]; then echo "ERROR: set DOCKER_USERNAME=yourname"; exit 1; fi
	docker push $(DOCKER_USERNAME)/promptpay-backend:$(IMAGE_TAG)
	docker push $(DOCKER_USERNAME)/promptpay-frontend:$(IMAGE_TAG)
	@echo ""
	@echo "✅ Pushed to Docker Hub:"
	@echo "   $(DOCKER_USERNAME)/promptpay-backend:$(IMAGE_TAG)"
	@echo "   $(DOCKER_USERNAME)/promptpay-frontend:$(IMAGE_TAG)"
	@echo ""
	@echo "Share with team:"
	@echo "   DOCKER_USERNAME=$(DOCKER_USERNAME) docker compose -f docker-compose.hub.yml up"

pull:
	## Pull latest images from Docker Hub
	@if [ -z "$(DOCKER_USERNAME)" ]; then echo "ERROR: set DOCKER_USERNAME=yourname"; exit 1; fi
	docker pull $(DOCKER_USERNAME)/promptpay-backend:$(IMAGE_TAG)
	docker pull $(DOCKER_USERNAME)/promptpay-frontend:$(IMAGE_TAG)

run-hub:
	## Run from Docker Hub images (no build needed)
	@if [ -z "$(DOCKER_USERNAME)" ]; then echo "ERROR: set DOCKER_USERNAME=yourname"; exit 1; fi
	DOCKER_USERNAME=$(DOCKER_USERNAME) IMAGE_TAG=$(IMAGE_TAG) \
	docker compose -f docker-compose.hub.yml up

# ── Tests ─────────────────────────────────────────────────────────────────────

test:
	## Run full test suite
	venv/bin/pytest backend/tests/ -v

.PHONY: dev up down logs restart build push pull run-hub test
