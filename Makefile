SHELL = /bin/bash

.DEFAULT_GOAL := help

SERVICE_NAME := service-control

CURRENT_DIR := $(shell pwd)

# Docker metadata
GIT_HASH := $(shell git rev-parse HEAD)
GIT_HASH_SHORT := $(shell git rev-parse --short HEAD)
GIT_BRANCH := $(shell git symbolic-ref HEAD --short 2>/dev/null)
GIT_DIRTY := $(shell git status --porcelain)
GIT_TAG := $(shell git describe --tags || echo "no version info")
AUTHOR := $(USER)


# Django specific
APP_SRC_DIR := app
DJANGO_MANAGER := $(CURRENT_DIR)/$(APP_SRC_DIR)/manage.py
DJANGO_MANAGER_DEBUG := -m debugpy --listen localhost:5678 --wait-for-client $(CURRENT_DIR)/$(APP_SRC_DIR)/manage.py

# Commands
UV_RUN := uv run
PYTHON := $(UV_RUN) python3
TEST := $(UV_RUN) pytest
RUFF := $(UV_RUN) ruff
TY := $(UV_RUN) ty
PRE_COMMIT := $(UV_RUN) pre-commit

# Docker variables?
DOCKER_REGISTRY = 074597099015.dkr.ecr.eu-central-1.amazonaws.com
DOCKER_IMG_LOCAL_TAG := $(DOCKER_REGISTRY)/swissgeo/$(SERVICE_NAME):local-$(USER)-$(GIT_HASH_SHORT)

# AWS variables
AWS_DEFAULT_REGION = eu-central-1

# Env file for dockerrun, defaults to .env.local / .env
ENV_FILE ?= $(if $(wildcard .env.local),.env.local,.env)
# export the env file so that uv picks it up in all recipes below
export UV_ENV_FILE := $(ENV_FILE)

.env:
	cp .env.default .env

.PHONY: git-info
git-info:
	@echo "GIT_HASH=$(GIT_HASH)"
	@echo "GIT_HASH_SHORT=$(GIT_HASH_SHORT)"
	@echo "GIT_BRANCH=$(GIT_BRANCH)"
	@echo "GIT_DIRTY=$(GIT_DIRTY)"
	@echo "GIT_TAG=$(GIT_TAG)"
	@echo "AUTHOR=$(AUTHOR)"
	@echo "DOCKER_IMG_LOCAL_TAG=$(DOCKER_IMG_LOCAL_TAG)"


.PHONY: ci
ci: .env
	# Create virtual env with all packages for development using the Pipfile.lock
	uv sync --frozen


.PHONY: setup
setup:.env ## Create virtualenv with all packages for development
	uv sync
	$(PRE_COMMIT) install
	# Start a new shell with the virtualenv activated and the .env file loaded into the environment
	# variables. The later is required for django which reads the settings from the environment variables
	uv run $$SHELL


.PHONY: start-local-db
start-local-db: ## Run the local db
	docker compose up -d db
	$(PYTHON) $(DJANGO_MANAGER) init_db
	$(PYTHON) $(DJANGO_MANAGER) migrate


.PHONY: start-local-services
start-local-services: ## Run the the support services (cognito, otel)
	docker compose up -d


.PHONY: seed-local-testdata
seed-local-testdata: start-local-services start-local-db ## Seed local organizations/users/roles in db + cognito
	USE_LOCAL_VERIFIED_PERMISSIONS=true $(PYTHON) $(DJANGO_MANAGER) seed_local_testdata
	$(PYTHON) $(DJANGO_MANAGER) loaddata app/fixtures/dataservice.json


.PHONY: reset-local-testdata
reset-local-testdata: start-local-services start-local-db ## Reset local users/orgs and seed again
	USE_LOCAL_VERIFIED_PERMISSIONS=true $(PYTHON) $(DJANGO_MANAGER) seed_local_testdata --reset --recreate-cognito-users
	$(PYTHON) $(DJANGO_MANAGER) loaddata app/fixtures/dataservice.json


.PHONY: format
format: ## Call ruff format to make sure your code is easier to read and respects some conventions.
	$(RUFF) format
	$(RUFF) check --select I --fix


.PHONY: django-checks
django-checks: ## Run the django checks
	$(PYTHON) $(DJANGO_MANAGER) check --fail-level WARNING
	$(PYTHON) $(DJANGO_MANAGER) makemigrations --no-input --check


.PHONY: ci-check-format
ci-check-format: format ## Check the format (CI)
	@if [[ -n `git status --porcelain --untracked-files=no` ]]; then \
	 	>&2 echo "ERROR: the following files are not formatted correctly"; \
	 	>&2 echo "'git status --porcelain' reported changes in those files after a 'make format' :"; \
		>&2 git status --porcelain --untracked-files=no; \
		exit 1; \
	fi


.PHONY: serve
serve: start-local-services start-local-db ## Serve the application locally
	$(PYTHON) $(DJANGO_MANAGER) runserver


.PHONY: serve-debug
serve-debug: start-local-services start-local-db ## Serve the application locally for debugging
	$(PYTHON) $(DJANGO_MANAGER_DEBUG) runserver


.PHONY: gunicornserve
gunicornserve: start-local-services start-local-db ## Serve the application locally with gunicorn
	$(PYTHON) $(APP_SRC_DIR)/wsgi.py


.PHONY: dockerlogin
dockerlogin: ## Login to the AWS Docker Registry (ECR)
	aws --profile swisstopo-swissgeo-builder ecr get-login-password --region $(AWS_DEFAULT_REGION) | docker login --username AWS --password-stdin $(DOCKER_REGISTRY)


.PHONY: dockerbuild
dockerbuild: ## Create a docker image
	docker build \
		--build-arg GIT_HASH="$(GIT_HASH)" \
		--build-arg GIT_BRANCH="$(GIT_BRANCH)" \
		--build-arg GIT_DIRTY="$(GIT_DIRTY)" \
		--build-arg VERSION="$(GIT_TAG)" \
		--build-arg HTTP_PORT="$(HTTP_PORT)" \
		--build-arg AUTHOR="$(AUTHOR)" -t $(DOCKER_IMG_LOCAL_TAG) .


.PHONY: dockerpush
dockerpush: dockerbuild ## Push to the docker registry
	docker push $(DOCKER_IMG_LOCAL_TAG)


.PHONY: dockerrun
dockerrun: start-local-services start-local-db dockerbuild ## Run the locally built docker image
	docker run \
		-it -p $(HTTP_PORT):8080 \
		--env-file=${ENV_FILE} \
		--env DJANGO_SETTINGS_MODULE=config.settings_prod \
		--env ALLOWED_HOSTS=127.0.0.1 \
		--net=host \
		$(DOCKER_IMG_LOCAL_TAG) ./wsgi.py


.PHONY: lint
lint: ## Run the linter and type checker on the code base
	$(RUFF) check
	$(TY) check


.PHONY: test-ci
test-ci: ## Run tests in the CI
	$(TEST) --cov --cov-branch --cov-report=xml:coverage.xml


.PHONY: test
test: start-local-services start-local-db ## Run tests locally
	$(TEST) --cov --cov-branch --cov-report=html


.PHONY: help
help: ## Display this help
# automatically generate the help page based on the documentation after each make target
# from https://gist.github.com/prwhite/8168133
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m\033[0m\n"} /^[$$()% a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
