#!/bin/bash -xe
# Example data_run.sh with optional proxy

CONFIG_FILE=~/data_run_config.sh

if [ -e $CONFIG_FILE ]; then
  source $CONFIG_FILE
else
  ### Start CONFIG ###
  SOCKS5_PORT=1337
  SSH_SERVER=example.com
  DOWNLOAD_DIR=~/latest_datagetter/
  GRANTNAV_DATA_DIR=~/grantnav_data/
  GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR=/var/www/grantnav_packages/
  DATAGETTER_THREADS=16
  export DJANGO_SETTINGS_MODULE=settings.settings_examlple
  DATASTORE=~/datastore/
  MAX_TOTAL_RUNS_IN_DB=31
  # Based on running this script each day and Keep a few extra for safety
  MAX_PACKAGE_AGE_DAYS=`expr $MAX_TOTAL_RUNS_IN_DB + 2`
  ### End CONFIG ###
fi

source $DATASTORE/.ve/bin/activate

mkdir -p $DOWNLOAD_DIR
mkdir -p $GRANTNAV_DATA_DIR
mkdir -p $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR

# Clear out old download dir contents
rm -rf $DOWNLOAD_DIR/*

if [[ $SOCKS5_PORT && $SSH_SERVER ]]; then
  echo "Start the proxy"
  ssh -D $SOCKS5_PORT -q -C -N $SSH_SERVER &
  PROXY_PID=$!
fi

cd $DATASTORE
./datastore/manage.py set_status --what datagetter --status IN_PROGRESS

echo "Running the datagetter"
if [ $PROXY_PID ]; then
  datagetter.py --threads $DATAGETTER_THREADS --socks5 socks5://localhost:$SOCKS5_PORT --data-dir $DOWNLOAD_DIR/data
else
  datagetter.py --threads $DATAGETTER_THREADS --data-dir $DOWNLOAD_DIR/data
fi

# Comment for quick TESTING!!
#cp -r ~/data $DOWNLOAD_DIR/data

./datastore/manage.py set_status --what datagetter --status IDLE

if [ $PROXY_PID ]; then
  echo "Shutting down proxy"
  kill -HUP $PROXY_PID
fi


echo "Load the downloaded datagetter data into datastore"
./datastore/manage.py set_status --what datastore --status LOADING_DATA

./datastore/manage.py load_datagetter_data $DOWNLOAD_DIR/data

./datastore/manage.py set_status --what datastore --status IDLE

echo "Create GrantNav package"
./datastore/manage.py set_status --what grantnav_data_package --status LOADING_DATA


# Tidy up

# Delete datagetter runs if we have reached the max
TOTAL_RUNS=`./datastore/manage.py list_datagetter_runs --total`

if [ $TOTAL_RUNS -gt $MAX_TOTAL_RUNS_IN_DB ]; then
    echo "Delete oldest datagetter data"
    ./datastore/manage.py delete_datagetter_data --oldest --no-prompt
fi

echo "Deleting old GrantNav packages"
find $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR -name "data_*.tar.gz" -mtime +$MAX_PACKAGE_AGE_DAYS | xargs rm -f

# Remove old data dump
rm -rf $GRANTNAV_DATA_DIR/data || true

./datastore/manage.py create_data_package --dir $GRANTNAV_DATA_DIR/data

NEW_PACKAGE_NAME=data_$(date +%F).tar.gz

cd $GRANTNAV_DATA_DIR
tar -czf $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/$NEW_PACKAGE_NAME data
# go back to original dir
cd $DATASTORE

# Create latest_grantnav_data.tar.gz symlink
rm $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/latest_grantnav_data.tar.gz
ln -s  $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/$NEW_PACKAGE_NAME  $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/latest_grantnav_data.tar.gz

./datastore/manage.py set_status --what grantnav_data_package --status READY

