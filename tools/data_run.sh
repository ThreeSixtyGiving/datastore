#!/bin/bash -xe
# Example data_run.sh with optional proxy

CONFIG_FILE=~/data_run_config.sh

function echo_stamp(){
  echo $(date +%F-%T) $@
}


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


# Cler out old download dir contents
rm -rf $DOWNLOAD_DIR/*

if [[ $SOCKS5_PORT && $SSH_SERVER ]]; then
  echo_stamp "Start the proxy"
  ssh -D $SOCKS5_PORT -q -C -N $SSH_SERVER &
  PROXY_PID=$!
fi

cd $DATASTORE
./datastore/manage.py set_status --what datagetter --status IN_PROGRESS

echo_stamp "Running the datagetter"
if [ $PROXY_PID ]; then
  datagetter.py --threads $DATAGETTER_THREADS --socks5 socks5://localhost:$SOCKS5_PORT --data-dir $DOWNLOAD_DIR/data
else
  datagetter.py --threads $DATAGETTER_THREADS --data-dir $DOWNLOAD_DIR/data
fi

# Comment for quick TESTING!!
#cp -r ~/data $DOWNLOAD_DIR/data

./datastore/manage.py set_status --what datagetter --status IDLE

if [ $PROXY_PID ]; then
  echo_stamp "Shutting down proxy"
  kill -HUP $PROXY_PID
fi


echo_stamp "Load the downloaded datagetter data into datastore"
./datastore/manage.py set_status --what datastore --status LOADING_DATA

./datastore/manage.py load_datagetter_data $DOWNLOAD_DIR/data

./datastore/manage.py set_status --what datastore --status IDLE

echo_stamp "Create GrantNav package"
./datastore/manage.py set_status --what grantnav_data_package --status LOADING_DATA


# Tidy up

echo_stamp "Deleting old unused datagetter data"
./datastore/manage.py delete_datagetter_data --all-not-in-use --older-than-days 90 --force-delete-in-use-data --no-prompt

echo_stamp "Deleting old GrantNav packages"
find $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR -name "data_*.tar.gz" -mtime +$MAX_PACKAGE_AGE_DAYS | xargs rm -f

# Remove old data dump
rm -rf $GRANTNAV_DATA_DIR/data || true

echo_stamp "Creating data package"
./datastore/manage.py create_data_package --dir $GRANTNAV_DATA_DIR/data

NEW_PACKAGE_NAME=data_$(date +%F).tar.gz

echo_stamp "Compressing package into tar gz"
cd $GRANTNAV_DATA_DIR
tar -czf $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/$NEW_PACKAGE_NAME data
# go back to original dir
cd $DATASTORE

# Create latest_grantnav_data.tar.gz symlink
rm $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/latest_grantnav_data.tar.gz
ln -s  $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/$NEW_PACKAGE_NAME  $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/latest_grantnav_data.tar.gz

echo_stamp "Data package ready"

./datastore/manage.py set_status --what grantnav_data_package --status READY

