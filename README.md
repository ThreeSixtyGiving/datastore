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

## Run the dev server

```
$ manage.py migrate
$ manage.py createsuperuser
$ manage.py runserver
```

## Loading data

$ manage.py load_datagetter_data ../path/to/data/dir/from/datagetter/

## Other useful commands

$ manage.py --help # !
