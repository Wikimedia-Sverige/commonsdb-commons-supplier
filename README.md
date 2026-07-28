# commonsdb-commons-supplier

Version: 0.1.18

This program makes declarations of files from [Wikimedia Commons](https://commons.wikimedia.org/) ("Commons") to [CommonsDB](https://www.commonsdb.org/).

## License

For license see [LICENSE](./LICENSE).

## Requirements

Python 3.12. May work with other versions, but not guaranteed.

`openssl` is required to generate TSA files.

It's recommended to use [Venv](https://docs.python.org/3/library/venv.html) both fo running and development. To set up the environment run:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Status

This program was developed as part of a project that ran between 2025 and 2026. The project has [a Phabricator project](https://phabricator.wikimedia.org/project/view/7708/) that has tasks for further development of the program.

During the project it was used to make more than 5 million declarations. As such it has been tested, but there is still room for improvements:

- More metadata could be added. What's included now are what was most relevant and what was easiest to extract.
- Performance can be improved. A lot of data is retrieved from Commons and Wikidata. This uses [Pywikibot](https://www.mediawiki.org/wiki/Manual:Pywikibot) and should be fairly efficient, but there are probably ways to make more so. Database handling could also probably be made more efficient.
- Code restructuring. The code grew during development and could use some clean up. This is most true for [make_declarations.py](./src/make_declaration.py). The main block at the end of the file could be split into functions, if not modules, to make it easier to work with.
- Tests. About half the files lack coverage.

## Running

Run [make_declaration.py](./src/make_declaration.py) to process files and make requests to the declaration API. For a full list of arguments run `src/make_declaration.py -h`.

make_declaration.py requires one argument that specifies input. It can be one of three things:

1. List file. If the argument is a file it will process each line as a file name on Commons. They should include namespace ("File:").
2. Commons category. If the argument starts with "Category:" files from that category on Commons will be processed. It will not look in subcategories by default. This can be changed with `--recurse-categories`.
3. [Tags](#tags). If the argument matches a tag in the journal, files with that tag will be processed.

You'll need verifiable credentials to make declarations. See [the CommonsDB documentation](https://docs.commonsdb.org/verifiable-credentials) for instructions on how to obtain them. You also need a keypair to create signatures. Instructions for this can also be found in [the documentation](https://docs.commonsdb.org/metadata-signature#approach-2-keypair-based-signing-with-embedded-jwk).

Each file will then be processed as follows:

1. Create a new declaration if there isn't one in [the journal](#journal) for that file. This is checked by comparing the page ID to those of declarations in the journals.
  1. If `--prepare` is used declarations will be prepared instead.
2. Update the declaration if is's already in the journal. This requires `--update` to be set.
3. Download the file. To limit file size, a version of the file with a maximum of 330 px wide is used.
4. Generate ISCC from the downloaded file.
5. Generate thumbnail.
6. Gather metadata from Commons. Location, name and license are required. If any of these could not be retrieved, no declaration is made for the file.
7. Create signatures and timestamps from the data.
8. Make request to the registry.
9. Save the ID in the response in the journal. This is used to determine if a declaration was successful.

For more information about the metadata format see [the declaration API documentation](https://docs.commonsdb.org/declaration-api/declare).

### Config

Environment variables are used as config. If a file named .env its content will be used as config.

```
API_ENDPOINT=<URL to the declaration API endpoint>
API_KEY=<Key for the declaration API>
RAW_API_KEY=<Used to bypass the normal API. Only use this if you're instructed by the registry maintainer to do so.>
MEMBER_CREDENTIALS_FILE=<Path to credential files used by the declaration API>
PRIVATE_KEY_FILE=<Path to the private key used to generate signatures for the declaration API>
PUBLIC_KEY_FILE=<path to the public key used to generate signatures for the declaration API>
DECLARATION_JOURNAL_URL=<URL to the database used by the declaration journal. For more info see https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls.>
TSA_URL=<URL to the TSA service>
TSA_SKIP_VERIFY=<Set to skip HTTPS verification of the TSA service>
```

### Journal

The journal keeps track of declarations as they're processed. It's used to make sure duplicate declarations aren't made for the same file. It also supports preparing declarations before making them.

The journal is stored as a database. This is specified by the `DECLARATION_JOURNAL_URL` variable in [the config](#config).

🚧 Some of the fields in the journal were used during development and may no longer be needed or accurate.

#### Tags

Tags are arbitrary strings that are used to categorise declarations. They can be used to filter the database and to specify what files to use as input.

Each declaration receives a tag with the batch name. This starts with "batch:" followed by the stem of the file if the input is a list file or the category's page ID if it is a category.

Custom tags can be added with `--tag`.

### Logging

Logs are written to stdout and stderr.

The stdout log reports when a the program starts, ends. It logs a line for each file and another line if the declaration wasn't made. This can be either "SKIP", if it was already declared, or "ERROR" if there was an error. Then it prints how long it took to process the file. At the end it prints a summary of the whole run that includes total time and how many files were skipped or failed.

The stderr log reports more information including timestamps. The level of detail depends on whether `--verbose` is set or not. Many steps of the file process are logged. This gives more information and makes it possible to measure how much time they take. If an error is encountered, it's logged even if the program doesn't quit. Some libraries also write to this log and the they may have different log formats.

Logs can become quite large when `--verbose` is used since each request is logged.

## Development

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

Github actions are specified in .github/workflows/python.yml. By default Tox will run when code is pushed.

### Database

When the tables change create a new version:

```
alembic revision --autogenerate -m "..."
```
