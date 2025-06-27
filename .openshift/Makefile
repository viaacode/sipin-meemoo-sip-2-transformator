.ONESHELL:
SHELL = /bin/bash

.PHONY: all test

test:
	pip install -e . --extra-index-url http://do-prd-mvn-01.do.viaa.be:8081/repository/pypi-all/simple --trusted-host do-prd-mvn-01.do.viaa.be
	pip install '.[dev]'
	export $(shell grep -v '^#' .env.example | xargs)
	ruff check
	python -m  pytest -vvv --cov=./app --junit-xml=./tests/test_results.xml --ignore=tests/test_service.py