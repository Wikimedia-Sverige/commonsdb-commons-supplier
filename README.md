# commonsdb-commons-supplier

## Requirements

Python 3.12. May work with other versions, but not guaranteed.

`openssl` is required to generat TSA files.

## Development

It's recommended to do development with [Venv](https://docs.python.org/3/library/venv.html). To set up the environment run:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Testing

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
