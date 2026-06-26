# Odoo Community — task runner. `make help` to list targets.
# Usage examples:
#   make up
#   make https
#   make company name=acme
#   make company name=globex modules=base,crm,sale_management,stock
#   make backup db=acme
#   make logs

.DEFAULT_GOAL := help
.PHONY: help up down restart logs ps https hosts company isolated seed backup restore shell psql wipe \
        pack-test all-apps setup-accounting brand smoke client-init client-health client-upgrade client-export \
        pack-test prod-cert prod-deploy prod-logs prod-down prod-backup-all

name    ?=
db      ?=
modules ?=
pack    ?= sme_trading
country ?= EG

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

setup-accounting: ## Wire fiscal year + asset accounts:  make setup-accounting db=acme
	@test -n "$(db)" || { echo "Usage: make setup-accounting db=<name>"; exit 1; }
	./scripts/dev/setup-accounting.sh $(db)

all-apps: ## Install every Community app into a company:  make all-apps db=acme
	@test -n "$(db)" || { echo "Usage: make all-apps db=<name>"; exit 1; }
	./scripts/dev/install-all-apps.sh $(db)

brand: ## Set company name + country + logo:  make brand db=acme name="Acme Inc." cc=US
	@test -n "$(db)" -a -n "$(name)" || { echo 'Usage: make brand db=<db> name="<Name>" [cc=US]'; exit 1; }
	./scripts/dev/brand-company.sh $(db) "$(name)" $(if $(cc),$(cc),US)

seed: ## Seed demo data into a company:  make seed db=acme [reset=1]
	@test -n "$(db)" || { echo "Usage: make seed db=<name> [reset=1]"; exit 1; }
	./scripts/dev/seed.sh $(db) $(if $(reset),--reset,)

smoke: ## Smoke-test login + data on a company:  make smoke db=acme
	@./scripts/dev/smoke-test.sh $(if $(db),$(db),acme)

client-init: ## Create a sellable Community Plus client: make client-init name=acme [pack=sme_trading country=EG]
	@test -n "$(name)" || { echo "Usage: make client-init name=<db> [pack=sme_trading country=EG]"; exit 1; }
	./scripts/client-init.sh $(name) $(pack) $(country) "$(if $(company),$(company),$(name))"

client-health: ## Check a Community Plus client: make client-health db=acme
	@test -n "$(db)" || { echo "Usage: make client-health db=<name>"; exit 1; }
	./scripts/client-health.sh $(db)

client-upgrade: ## Upgrade Community Plus modules in a client DB: make client-upgrade db=acme
	@test -n "$(db)" || { echo "Usage: make client-upgrade db=<name>"; exit 1; }
	./scripts/client-upgrade.sh $(db)

client-export: ## Export one client DB + filestore + metadata: make client-export db=acme
	@test -n "$(db)" || { echo "Usage: make client-export db=<name>"; exit 1; }
	./scripts/client-export.sh $(db)

pack-test: ## Fresh-DB install test for Community Plus pack
	./scripts/dev/pack-test.sh

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

# ── Production (run on the server) ─────────────────────────────────────────
prod-cert: ## Issue the wildcard Let's Encrypt cert (run once)
	./scripts/prod/issue-cert.sh

prod-deploy: ## Render prod config + start the production stack
	./scripts/prod/deploy.sh

prod-logs: ## Tail production Odoo logs
	docker compose -f docker-compose.prod.yml logs -f web

prod-down: ## Stop the production stack (keeps data)
	docker compose -f docker-compose.prod.yml down

prod-backup-all: ## Back up every production client DB
	./scripts/prod/backup-all.sh
