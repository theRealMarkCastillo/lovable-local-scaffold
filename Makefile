PYTHON ?= .venv-tools/bin/python

.PHONY: init up down logs check smoke admin origin frontend
init: tools
	$(PYTHON) scripts/stack.py init
up: tools
	$(PYTHON) scripts/stack.py up
down: tools
	$(PYTHON) scripts/stack.py down
logs: tools
	$(PYTHON) scripts/stack.py logs
check: tools
	$(PYTHON) scripts/stack.py check
smoke: tools
	$(PYTHON) scripts/smoke.py
admin: tools
	$(PYTHON) scripts/stack.py admin
origin: tools
	$(PYTHON) scripts/stack.py origin "$(URL)"

frontend: tools
	$(PYTHON) scripts/stack.py frontend "$(KIND)"

# Import/inspection only; execution commands are intentionally explicit in the guide.
backend-import: tools
	$(PYTHON) scripts/backend.py import "$(SOURCE)" --name "$(NAME)"
backend-inspect: tools
	$(PYTHON) scripts/backend.py inspect "$(NAME)"

backend-test: tools
	$(PYTHON) -m unittest discover -s tests -v
backend-test-integration: tools
	$(PYTHON) tests/integration_backend.py

frontend-test: tools
	node --test web/tests/session-state.test.mjs

.PHONY: tools frontend-test browser-test
tools:
	python3 scripts/setup_tools.py

browser-test: tools
	node tests/browser-account-switch.mjs

.PHONY: tunnel tunnel-set
tunnel:
	python3 scripts/tunnel.py
tunnel-set: origin

.PHONY: email-config email-test email-smoke
email-config: tools
	$(PYTHON) scripts/email_checks.py config
email-test: tools
	$(PYTHON) scripts/email_checks.py test
email-smoke: tools
	$(PYTHON) scripts/email_checks.py smoke
