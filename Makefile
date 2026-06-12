.PHONY: install run-sim run-server run-dashboard inject autopsy

install:
	pip install -r requirements.txt --break-system-packages
	cd frontend && npm install

run-sim:
	python demo/run_port.py

run-server:
	uvicorn server:app --reload --port 8000

run-dashboard:
	cd frontend && npm run dev

inject:
	python demo/inject_failure.py $(SCENARIO)

autopsy:
	python demo/run_autopsy.py
