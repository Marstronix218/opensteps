.PHONY: up down test demo migrate seed

up:
	docker compose up -d --build --wait

down:
	docker compose down

test:
	docker compose run --rm backend pytest -q

migrate:
	docker compose run --rm backend alembic upgrade head

demo: up
	docker compose exec backend python /app/examples/python_agent_client/demo.py

seed: up
	docker compose exec backend python /app/examples/python_agent_client/demo.py --seed-only
