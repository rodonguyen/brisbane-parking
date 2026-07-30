.PHONY: help ingest api web dev install-web install-api

help:
	@echo "Targets: ingest | api | web | dev | install-web | install-api"

install-api:
	cd api && python -m pip install -r requirements.txt

install-web:
	cd web && npm install

ingest:
	cd api && python -m py.ingest

api:
	cd api && python -m py.server

web:
	cd web && npm run dev

dev:
	bash api/run-dev.sh
