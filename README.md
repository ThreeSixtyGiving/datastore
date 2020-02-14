# Data storage tool for 360 Giving

This repo is in flux and very much a work in progress!

## Postgres setup

Example:

In this example we create a user test and password test for dev useage

```
$ sudo apt-get install postgresql-10 postgresql-server-dev-10
$ sudo -u postgres createuser -P -e test  --interactive
$ createdb -U test -W 360givingdatastore

```

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

## Loading data
```
$ manage.py load_datagetter_data ../path/to/data/dir/from/datagetter/
```
## Other useful commands
```
$ manage.py --help # !
```
## Testing

### Requirements

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
$ isort --check-only --recursive ./
$ black --check ./
```
