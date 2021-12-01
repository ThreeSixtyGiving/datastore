# DataStore for [360 Giving](https://threesixtygiving.org) data

[![Build Status](https://travis-ci.com/ThreeSixtyGiving/datastore.svg?branch=master)](https://travis-ci.com/ThreeSixtyGiving/datastore)
[![Coverage Status](https://coveralls.io/repos/github/ThreeSixtyGiving/datastore/badge.svg?branch=master)](https://coveralls.io/github/ThreeSixtyGiving/datastore?branch=master)

## Postgres setup

Example:

In this example we create a user test and password test for dev usage.

```
$ sudo apt-get install postgresql-10 postgresql-server-dev-10
$ sudo -u postgres createuser -P -e test  --interactive
$ createdb -U test -W 360givingdatastore

```

(In development you can also set the `DATABASE_HOST`, `DATABASE_NAME`,`DATABASE_USER` and `DATABASE_PASSWORD` environmental variables.)

## Python setup

```
$ virtualenv --python=python3 ./.ve/
$ source ./.ve/bin/activate
$ pip install -r requirements.txt
```

## Run the dev server

```
$ manage.py migrate
$ manage.py createsuperuser
$ manage.py runserver
```

## Loading grant data

_Note: before loading grant data you may wish to load additional_data sources_

```
$ manage.py load_datagetter_data ../path/to/data/dir/from/datagetter/
```

## Loading data for additional data

A number of the sources for additional_data have their own local caches these can be loaded via:

```
$ manage.py load_code_names
$ manage.py load_geolookups
$ manage.py load_nspl
$ manage.py load_org_data
$ manage.py loaddata default_tsg_org_types
```

## Other useful commands

There are many useful management commands see:

```
$ manage.py --help # !
```


# Dev with Docker Compose

Developers can also use Docker Compose to get a local development environment.

## Running

    docker-compose -f docker-compose.dev.yml up

The website should be available at http://localhost:8000

Use Ctrl-C to exit.


## Loading grant data & additional data

Whilst leaving the up command running, you should use `docker-compose run` with the commands from the above sections.

eg; instead of running:

```
$ manage.py load_code_names
```

Run:

```
$ docker-compose -f docker-compose.dev.yml run datastore-web python datastore/manage.py load_code_names
```

## Getting database CLI

Run:

```
$ docker-compose -f docker-compose.dev.yml run -e PGPASSWORD=postgres postgres psql -h postgres -U postgres 
```

# Testing

## Requirements

```
$ pip install -r ./requirements_dev.txt
```

You will also need the chromedriver for your machine's chromimum based browser.
see https://chromedriver.chromium.org/downloads

Alternatively edit the selenium test setup in test_browser to use your preferred selenium setup.

### Run tests

```
$ ./manage.py test tests
$ flake8
$ black --check ./
```

### Running specific tests

You can run any particular tests individually e.g.:

```
$ manage.py test tests.test_additional_data_tsgorgtype
```

_see `manage.py test --help` for more info_

# Updating requirements

We target python3.8 for our requirements.

Use `pip-compile` provided by `pip-tools` package to process requirements .in files.

# Key modules in the datastore

## db

This module is the central datastore for 360 Giving data. It contains the models which define the database and the ORM for accessing, creating and updating the grant data.

A key function is managing the `Latest` data which represent the created datasets that are built from `datagetter` grant data. These datasets are used in GrantNav.

Management commands here allow for loading and managing datasets as well as a mechanism for external scripts to update the current status of the system (status is used in the UI and for GrantNav API).

## api

This contains the API endpoints that are used to control the system from the UI, indicate the status and data download url for GrantNav updates as well as an experimental REST API built using django-rest-framework.

## ui

Templates and staic html/js live here, there is a basic dashboard which shows the current status of the system as well as a mechanism to trigger a full datarun (fetch and load).

## additional_data

During the load of grant data (`datagetter` data) that is done by the `db` module command `load_datagetter_data` each grant is passed to the `create` method of the `AdditionalDataGenerator`, here various sources are used to add to an `additional_data` object that is available on the `Grant` model.

`additional_data` data sources come in various forms, static files which are loaded, as well as caches of data in our local database (for example postcode lookups).

The `generator` ensures a particular order to additional_data fields being added which allows for dependencies of one source to another.

## prometheus

Provides a [prometheus](https://prometheus.io/) endpoint to monitor vital metrics on the datastore

## tools

An example datarun script. This is an orchestrator of running a datagetter, updating the statuses and loading the data into the datastore.

## settings

Django Settings for the datastore. Includes location for data run logs, the data run script / pid

## tests

Various cross-module tests.
