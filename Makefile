.PHONY: init up down logs check smoke admin origin frontend
init:
	python3 scripts/stack.py init
up:
	python3 scripts/stack.py up
down:
	python3 scripts/stack.py down
logs:
	python3 scripts/stack.py logs
check:
	python3 scripts/stack.py check
smoke:
	python3 scripts/smoke.py
admin:
	python3 scripts/stack.py admin
origin:
	python3 scripts/stack.py origin "$(URL)"

frontend:
	python3 scripts/stack.py frontend "$(KIND)"

# Import/inspection only; execution commands are intentionally explicit in the guide.
backend-import:
	python3 scripts/backend.py import "$(SOURCE)" --name "$(NAME)"
backend-inspect:
	python3 scripts/backend.py inspect "$(NAME)"

backend-test:
	python3 -m unittest discover -s tests -v
backend-test-integration:
	python3 tests/integration_backend.py
