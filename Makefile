.PHONY: help install dev up down test lint format migrate

help:
	@echo "AdaptiveDocAI Management Commands:"
	@echo "  make install     Install backend and frontend dependencies"
	@echo "  make up          Start all infrastructure services with Docker Compose"
	@echo "  make down        Stop all Docker Compose services"
	@echo "  make test        Run backend test suite with pytest"
	@echo "  make backend-dev Start FastAPI backend in reload mode"
	@echo "  make frontend-dev Start Next.js development server"

install:
	cd backend && pip install -r requirements.txt -r requirements-dev.txt
	cd frontend && npm install

up:
	docker compose -f infrastructure/docker-compose.yml up -d

down:
	docker compose -f infrastructure/docker-compose.yml down

test:
	cd backend && pytest -v

lint:
	cd backend && ruff check .
	cd frontend && npm run lint

format:
	cd backend && ruff format .

migrate:
	cd backend && alembic upgrade head

