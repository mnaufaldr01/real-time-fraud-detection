.PHONY: up down logs seed test demo train-model profile install wait

up:
	docker compose up -d
	@echo "Waiting for services..."
	@powershell -ExecutionPolicy Bypass -File scripts/wait-for.ps1

down:
	docker compose down -v

logs:
	docker compose logs -f

install:
	pip install -e ".[api,consumer,producer,analysis,dashboard,dev]"

wait:
	powershell -ExecutionPolicy Bypass -File scripts/wait-for.ps1

profile:
	python analysis/profile_data.py

train-model:
	python scripts/train_anomaly.py

seed:
	python scripts/seed_users.py

consumer:
	python -m consumer.main

generator:
	python -m producer.generator

api:
	uvicorn producer.api.main:app --host 0.0.0.0 --port 8000 --reload

dashboard:
	streamlit run dashboard/app.py --server.port 8501

test:
	pytest tests/ -v

demo: up
	@echo "Starting demo components..."
	@echo "1. Run 'make consumer' in one terminal"
	@echo "2. Run 'make generator' in another terminal"
	@echo "3. Open http://localhost:8080 for Kafka UI"
	@echo "4. Open http://localhost:8081 for Airflow (admin/admin)"
	@echo "5. POST to http://localhost:8000/transactions for manual events"
