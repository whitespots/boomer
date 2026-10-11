# Generated reports

Run `make scan-examples` from the repository root to regenerate every report.

## Poetry

These reports are generated from `tests/fixtures/python-poetry` and demonstrate
the difference between scanning a Poetry manifest and its lockfile.

- `python-poetry-pyproject.json` is generated from `pyproject.toml`. It contains
  direct dependencies with their declared version constraints.
- `python-poetry-lock.json` is generated with `--prefer-locks`. It contains the
  exact resolved package versions and their dependency graph from `poetry.lock`.

Commands:

```shell
.venv/bin/python boomer.py scan tests/fixtures/python-poetry \
  --output examples/python-poetry-pyproject.json

.venv/bin/python boomer.py scan tests/fixtures/python-poetry \
  --prefer-locks \
  --output examples/python-poetry-lock.json
```

## Go

- `go-mod.json` is generated from the standard `go.mod` fixture.
- `go-lock.json` is generated from the legacy Go dep lockfile `Gopkg.lock`.
  Go Modules use `go.sum` for checksums; it is not a lockfile.

Commands:

```shell
.venv/bin/python boomer.py scan tests/fixtures/go \
  --output examples/go-mod.json

.venv/bin/python boomer.py scan tests/fixtures/go-lock-only \
  --output examples/go-lock.json
```

## npm

- `npm-package.json` is generated from `package.json` and contains declared
  dependency constraints.
- `npm-lock.json` is generated with `--prefer-locks` from `package-lock.json`
  and contains exact versions, package metadata, and the dependency graph.

Commands:

```shell
.venv/bin/python boomer.py scan tests/fixtures/javascript \
  --output examples/npm-package.json

.venv/bin/python boomer.py scan tests/fixtures/javascript \
  --prefer-locks \
  --output examples/npm-lock.json
```

## Maven

- `maven-pom.json` is generated from `pom.xml` and contains declared direct
  dependencies.
- `maven-lock.json` is generated with `--prefer-locks` from the Maven Lockfile
  plugin's `lockfile.json`. It contains resolved versions and the transitive
  dependency graph.

Commands:

```shell
.venv/bin/python boomer.py scan tests/fixtures/java-maven-lock \
  --output examples/maven-pom.json

.venv/bin/python boomer.py scan tests/fixtures/java-maven-lock \
  --prefer-locks \
  --output examples/maven-lock.json
```

## PHP / Composer

- `php-composer.json` is generated from `composer.json` and contains declared
  dependency constraints.
- `php-composer-lock.json` is generated with `--prefer-locks` from
  `composer.lock`. It contains exact package versions and dependency relations.

Commands:

```shell
.venv/bin/python boomer.py scan tests/fixtures/php \
  --output examples/php-composer.json

.venv/bin/python boomer.py scan tests/fixtures/php \
  --prefer-locks \
  --output examples/php-composer-lock.json
```
