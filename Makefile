.PHONY: scan-examples scan-fixtures test-parsers

PYTHON ?= .venv/bin/python

scan-examples:
	mkdir -p examples
	$(PYTHON) boomer.py scan tests/fixtures/python-poetry --output examples/python-poetry-pyproject.json
	$(PYTHON) boomer.py scan tests/fixtures/python-poetry --prefer-locks --output examples/python-poetry-lock.json
	$(PYTHON) boomer.py scan tests/fixtures/go --output examples/go-mod.json
	$(PYTHON) boomer.py scan tests/fixtures/go-lock-only --output examples/go-lock.json
	$(PYTHON) boomer.py scan tests/fixtures/javascript --output examples/npm-package.json
	$(PYTHON) boomer.py scan tests/fixtures/javascript --prefer-locks --output examples/npm-lock.json
	$(PYTHON) boomer.py scan tests/fixtures/java-maven-lock --output examples/maven-pom.json
	$(PYTHON) boomer.py scan tests/fixtures/java-maven-lock --prefer-locks --output examples/maven-lock.json
	$(PYTHON) boomer.py scan tests/fixtures/php --output examples/php-composer.json
	$(PYTHON) boomer.py scan tests/fixtures/php --prefer-locks --output examples/php-composer-lock.json

scan-fixtures:
	mkdir -p tests/reports
	$(PYTHON) boomer.py scan tests/fixtures/python --output tests/reports/python.json
	$(PYTHON) boomer.py scan tests/fixtures/python-manifests --output tests/reports/python-manifests.json
	$(PYTHON) boomer.py scan tests/fixtures/javascript --prefer-locks --output tests/reports/javascript.json
	$(PYTHON) boomer.py scan tests/fixtures/javascript-yarn --prefer-locks --output tests/reports/javascript-yarn.json
	$(PYTHON) boomer.py scan tests/fixtures/java --output tests/reports/java.json
	$(PYTHON) boomer.py scan tests/fixtures/cpp --output tests/reports/cpp.json
	$(PYTHON) boomer.py scan tests/fixtures/csharp --output tests/reports/csharp.json
	$(PYTHON) boomer.py scan tests/fixtures/go --output tests/reports/go.json
	$(PYTHON) boomer.py scan tests/fixtures/go-manifests --output tests/reports/go-manifests.json
	$(PYTHON) boomer.py scan tests/fixtures/rust --output tests/reports/rust.json
	$(PYTHON) boomer.py scan tests/fixtures/php --prefer-locks --output tests/reports/php.json
	$(PYTHON) boomer.py scan tests/fixtures/ruby --output tests/reports/ruby.json

test-parsers:
	$(PYTHON) -m unittest tests.test_parsers -v
