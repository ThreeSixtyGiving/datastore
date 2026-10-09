# DataStore for [360 Giving](https://threesixtygiving.org) data

[![Coverage Status](https://coveralls.io/repos/github/ThreeSixtyGiving/datastore/badge.svg?branch=live)](https://coveralls.io/github/ThreeSixtyGiving/datastore?branch=live)

## Running the DataStore

### Database

The DataStore requires a Postgres database running via Docker or locally.

_Note: Special Postgresql extensions are used for indexes, if you don't want to have these installed in the database or the database user doesn't have permissions to install extensions then set environment variable `SKIP_SPECIAL_DB_INDEX=true` before you run migrate. In development you can also set the `DATABASE_HOST`, `DATABASE_NAME`,`DATABASE_USER` and `DATABASE_PASSWORD` environmental variables._

#### Local installation

```
$ sudo apt-get install postgresql-16 postgresql-server-dev-16
$ sudo -u postgres createuser -P -e test  --interactive
$ createdb -U test -W 360givingdatastore

```

#### Docker

```
docker run --name datastorepostgres  -p 5432:5432 -e POSTGRES_PASSWORD=test -e POSTGRES_USER=test -e POSTGRES_DB=360givingdatastore -d postgres # Will set it up and start it
docker start datastorepostgres # If already set up, will start it
docker stop datastorepostgres # Stop it running
```

### Python

Dependencies are in `requirements.txt`.  We recommend setting up a virtual environment in which to run the application.

```
$ virtualenv --python=python3.12 ./.ve/
$ source ./.ve/bin/activate
$ pip install -r requirements.txt
```

### Starting the server for local development

Note that if you don't want to have the special PSQL extensions for indices you should also set the `SKIP_SPECIAL_DB_INDEX=true` before running `migrate`.

```
$ export DJANGO_SETTINGS_MODULE=settings.settings_dev
$ manage.py migrate
$ manage.py createsuperuser
$ manage.py runserver
```

### Other useful commands

There are many useful management commands see:

```
$ manage.py --help
```

### Running via Docker Compose

Local developers can also use Docker Compose to get a local development environment.

    docker-compose -f docker-compose.dev.yml up

The website should be available at http://localhost:8000

Use Ctrl-C to exit.

#### Running commands in the container

When the container is up and running you should use `docker-compose run` with the relevant commands, for example, instead of running `manage.py load_geocode_names` run:

```
$ docker-compose -f docker-compose.dev.yml run datastore-web python datastore/manage.py load_geocode_names
```

To get to the database CLI run:

``` 
$ docker-compose -f docker-compose.dev.yml run -e PGPASSWORD=postgres postgres psql -h postgres -U postgres
```

## Populating the DataStore

The DataStore can be run just be loading data from the [datagetter](https://github.com/ThreeSixtyGiving/datagetter).  But, generally the DataStore should be populated with additional data before loading data from the [datagetter](https://github.com/ThreeSixtyGiving/datagetter).  Complete steps are:

1. Load additional data.
2. Load grant data.
3. Update entities data.

### Loading additional data

A number of the sources for `additional_data` have their own local caches which need to be kept up-to-date.

To better understand additional data, refer to [360Giving Datastore - additional data](https://docs.google.com/document/d/1ZhGDhkRnjeyK3dgycO6SdOrwPiwPytp-a2ekIXSqUKo/view).

For a script which combines all the steps, see `datastore/additional_data/sources/update_all_sources.sh`

Occasionally we also need to update the upstream URLs where data is fetched from, found in `datastore/additional_data/sources/*.py`.

#### 360G CodeLists

Downloads codelists from the ThreeSixtyGiving/standard GitHub repo.

```bash
./manage.py load_codelist_codes
```

#### Geo Data

Look at the `datastore_num_current_grants_with_beneficiary_location_geocode_without_lookup` metric of the getter run before and after updating geodata, it should go down.

```bash
./manage.py load_geocode_names # CHD Data
./manage.py load_geolookups    # from https://github.com/drkane/geo-lookups
./manage.py load_nspl
```

#### Organisation Data

```bash
# Got to delete the old org data before loading in the new
./manage.py delete_org_data --no-prompt

./additional_data/sources/load_all_org_data.sh
```

### Loading grant data

```
$ manage.py load_datagetter_data ../path/to/data/dir/from/datagetter/
```

### Updating entities data

Create/update the Recipient/Funder model entries from grant data.

```
$ python manage.py manage_entities_data --update
```

## Tools and scripts

The `tools/` folder contains various scripts and tools to support operation of the datastore.

### Pipeline

The `data_run.sh` script runs the 360Giving pipeline.  The configuration is stored in `data_run_config.sh` with the following variables:

| Variable                             | Description                                                  |
| ------------------------------------ | ------------------------------------------------------------ |
| `DOWNLOAD_DIR`                       | Directory to which the DataGetter data will be downloaded.   |
| `GRANTNAV_DATA_DIR`                  | Directory in which the GrantNav data dump will be generated. |
| `GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR` | Directory in which the GrantNav package will be generated for download by GrantNav. |
| `DATAGETTER_THREADS`                 | Number of threads used by the DataGetter                     |
| `DJANGO_SETTINGS_MODULE`             | Django settings module path.                                 |
| `DATASTORE`                          | Path to the DataStore installation.                          |
| `DATAGETTER`                         | Path to the DataGetter installation.                         |
| `MAX_TOTAL_RUNS_IN_DB`               | Maximum number of DataGetter runs to store in the database.  |
| `MAX_PACKAGE_AGE_DAYS`               | Maximum age of the GrantNav data package.                    |
| `PERFORMANCE_CSV`                    | Path to the CSV file storing pipeline profiling/performance data. |

### GrantNav package check

The `check_data_package.py` script supports the pipeline and runs on a cron job (on the monitor server) and checks that the GrantNav package has been generated and sends an email if it hasn't.

### DataStore polling

The `poll_datastore.py` scripts runs on the GrantNav server and checks for new data packages in the DataStore.

## Development

### Testing

#### Requirements

```
$ pip install -r ./requirements_dev.txt
```

You will also need the chromedriver for your machine's chromimum based browser.
see https://chromedriver.chromium.org/downloads

Alternatively edit the selenium test setup in test_browser to use your preferred selenium setup.

#### Run tests

```
$ ./manage.py test tests
$ flake8
$ black --check ./
```

_Note: You may want to run this with `SKIP_SPECIAL_DB_INDEX=true` to avoid the need for the test database user to have permissions for installing postgresql extensions when running the tests._

#### Running specific tests

You can run any particular tests individually e.g.:

```
$ manage.py test tests.test_additional_data_tsgorgtype
```

_see `manage.py test --help` for more info_

#### Updating the test data fixture

Note that the OrgInfoCache entries for the test funders/recipients also needs to be included in the test data fixture.

```shell
./manage.py dumpdata --output db/fixtures/test_data.json db additional_data.OrgInfoCache
```

### Updating requirements

We target python3.12 for our requirements.

Use `pip-compile` provided by `pip-tools` package to process requirements .in files.

### Linting

Black is used for formatting and the configuration is in `setup.cfg`.

### Updating the JSON Schema / OpenAPI docs

Our API docs / schema are based on OpenAPI 3.0 (as generated by drf-spectacular), which is incompatible with plain JSON Schema, so `datastore/static/` keeps JSON Schema + OpenAPI 3.0 copies of two schemas:

- **360G grant schema** - authored upstream in `ThreeSixtyGiving/standard`
- **Additional data schema** - describes fields this datastore itself computes and adds to grants (codelist lookups, geo lookups, org matches, etc.), so it's authored here at `datastore/additional_data/schema/additional-data-schema.json`, not upstream

`datastore/static/update_schemas.sh` regenerates both:

```bash
cd datastore/static/
./update_schemas.sh          # refreshes the additional data schema only
./update_schemas.sh 1.4      # also fetches & refreshes the 360G grant schema at version 1.4
```

It uses `npx` to run the `@openapi-contrib/json-schema-to-openapi-schema` CLI, so no global install is needed. When fetching a new 360G schema version, also update the `TSG_OPENAPI_SCHEMA_STATICFILE` setting in `settings.py` to point at the new version.

## Design

### Key modules in the datastore

#### db

This module is the central datastore for 360 Giving data. It contains the models which define the database and the ORM for accessing, creating and updating the grant data.

A key function is managing the `Latest` data which represent the created datasets that are built from `datagetter` grant data. These datasets are used in GrantNav.

Management commands here allow for loading and managing datasets as well as a mechanism for external scripts to update the current status of the system (status is used in the UI and for GrantNav API).

#### api

This contains the API endpoints that are used to control the system from the UI, indicate the status and data download url for GrantNav updates as well as an experimental REST API built using django-rest-framework.

#### ui

Templates and staic html/js live here, there is a basic dashboard which shows the current status of the system as well as a mechanism to trigger a full datarun (fetch and load).

#### additional_data

During the load of grant data (`datagetter` data) that is done by the `db` module command `load_datagetter_data` each grant is passed to the `create` method of the `AdditionalDataGenerator`, here various sources are used to add to an `additional_data` object that is available on the `Grant` model.

`additional_data` data sources come in various forms, static files which are loaded, as well as caches of data in our local database (for example postcode lookups).

The `generator` ensures a particular order to additional_data fields being added which allows for dependencies of one source to another.

#### monitoring

The `monitoring` module keeps a timeseries history of snapshots of statistics and metrics about the grant data.
It exports a management command `create_monitoring_snapshot` which creates a new snapshot of the current state of grants, as well as `list_monitoring_snapshots` and `delete_monitoring_snapshot` helper commands.
These snapshots can be used both on a daily basis to monitor for changes or power live dashboards, or for historical analysis of changes over time.
An API is exposed from the `api` module.

#### prometheus

Provides a [prometheus](https://prometheus.io/) endpoint to monitor vital metrics on the datastore

#### tools

An example datarun script. This is an orchestrator of running a datagetter, updating the statuses and loading the data into the datastore.

#### settings

Django Settings for the datastore. Includes location for data run logs, the data run script / pid

#### tests

Various cross-module tests.