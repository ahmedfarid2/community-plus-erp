# Odoo Community — task runner. `make help` to list targets.
# Usage examples:
#   make up
#   make https
#   make company name=acme
#   make company name=globex modules=base,crm,sale_management,stock
#   make backup db=acme
#   make logs

.DEFAULT_GOAL := help
.PHONY: help up down restart logs ps https hosts company isolated seed backup restore shell psql wipe

name    ?=
db      ?=
modules ?=

help: ## List available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## Start the stack (renders config, waits until reachable)
	./scripts/start.sh

down: ## Stop the stack (keeps data)
	./scripts/stop.sh

restart: down up ## Restart the stack

logs: ## Tail Odoo logs
	docker compose logs -f web

ps: ## Show container status
	docker compose ps

https: ## Generate local HTTPS certs with mkcert (*.odoo.local)
	./scripts/dev/setup-https.sh

hosts: ## Print the /etc/hosts line to add for local domains
	@echo "127.0.0.1 odoo.local acme.odoo.local globex.odoo.local"

company: ## Create a company DB:  make company name=acme [modules=...]
	@test -n "$(name)" || { echo "Usage: make company name=<db> [modules=a,b,c]"; exit 1; }
	./scripts/new-company.sh $(name) $(modules)

isolated: ## Create a fully separate per-company stack:  make isolated name=acme
	@test -n "$(name)" || { echo "Usage: make isolated name=<db>"; exit 1; }
	./scripts/new-company.sh $(name) --isolated

seed: ## Seed demo data into a company:  make seed db=acme [reset=1]
	@test -n "$(db)" || { echo "Usage: make seed db=<name> [reset=1]"; exit 1; }
	./scripts/dev/seed.sh $(db) $(if $(reset),--reset,)

backup: ## Back up one company:  make backup db=acme
	@test -n "$(db)" || { echo "Usage: make backup db=<name>"; exit 1; }
	./scripts/backup.sh $(db)

restore: ## Restore: make restore db=new dump=path [fs=path]
	@test -n "$(db)" -a -n "$(dump)" || { echo "Usage: make restore db=<name> dump=<file> [fs=<file>]"; exit 1; }
	./scripts/restore.sh $(db) $(dump) $(fs)

shell: ## Open an Odoo shell:  make shell db=acme
	@test -n "$(db)" || { echo "Usage: make shell db=<name>"; exit 1; }
	docker compose run --rm --no-deps web odoo shell -d $(db) --no-http

psql: ## Open psql on a company DB:  make psql db=acme
	@test -n "$(db)" || { echo "Usage: make psql db=<name>"; exit 1; }
	docker compose exec db psql -U odoo -d $(db)

wipe: ## DANGER: stop and delete ALL data volumes
	./scripts/stop.sh --wipe
