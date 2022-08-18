.EXPORT_ALL_VARIABLES:

PYTHONPATH := $(shell pwd)/src

# --[ Python ]------------------------------------------------------------------

python-init:
	@echo "Creating virtual environment ..."
	poetry env use python3
	@echo "Installing project into the virtual environment ..."
	poetry install --verbose

python-update:
	@echo "Update project dependencies ..."
	poetry update

init:
	pip install -r requirements.txt

test:
	nosetests tests

run: 
	poetry run run-client
