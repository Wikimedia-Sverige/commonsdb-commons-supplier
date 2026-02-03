# commonsdb-commons-supplier

Version: 0.1.2

## Requirements

Python 3.12. May work with other versions, but not guaranteed.

`openssl` is required to generat TSA files.

## Running

Run src/make_declaration.py to process files and make requests to the declaration API.

### Config

Environment variables are used as config. If a file named .env exists variables specified there will be used.

```
API_ENDPOINT=<url to the declaration API endpoint>
API_KEY=<key for the declaration API>
MEMBER_CREDENTIALS_FILE=<path to credential files used by the declaration api>
PRIVATE_KEY_FILE=<path to the private key used to generate signatures for the declaration api>
PUBLIC_KEY_FILE=<path to the public key used to generate signatures for the declaration api>
DECLARATION_JOURNAL_URL=<URL to the database used by the declaration journal, for more info see https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls>
```

## Development

It's recommended to do development with [Venv](https://docs.python.org/3/library/venv.html). To set up the environment run:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Testing

To install test modules run:

```
pip install -r requirements-test.txt
```

Testing is done by [Tox](https://tox.wiki). Run `tox` for all tests. Settings can be changed in tox.ini.

Unit tests are run with [Pytest](https://docs.pytest.org). Test files live in tests/.

Style is checked by [Flake8](https://flake8.pycqa.org/).

Module import order is handled by [Isort](https://pycqa.github.io/isort/).

### CI

Github actions are specified in .github/workflows/python.yml. By deafult Tox will run when code is pushed.

### Database

When the tables change create a new version:

```
alembic revision --autogenerate -m "..."
```
