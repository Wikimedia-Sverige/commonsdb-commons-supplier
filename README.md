# commonsdb-commons-supplier

## Testing

Testing is done by [Tox](https://tox.wiki). Run `tox` for all tests. Settings can be changed in tox.ini.

Unit tests are run with [Pytest](https://docs.pytest.org). Test files live in tests/.

Style is checked by [Flake8](https://flake8.pycqa.org/).

Module import order is handled by [Isort](https://pycqa.github.io/isort/).

### CI

Github actions are specified in .github/workflows/python.yml. By deafult Tox will run when code is pushed.

