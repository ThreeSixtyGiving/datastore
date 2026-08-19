#!/bin/bash -xe
# Example data_run.sh with optional proxy

CONFIG_FILE=~/data_run_config.sh

function echo_stamp(){
  echo $(date +%F-%T) $@
}

function profile_block_start() {
    _timer_start=$EPOCHREALTIME
}

function profile_block_stop() {
    local duration=$(awk "BEGIN {print $EPOCHREALTIME - $_timer_start}")
    local label=${1:-Block}
    local timestamp=$(date +%FT%T)
    echo  "${timestamp},${performance_run_id},${label},${duration}" >>$PERFORMANCE_CSV
}

# Use the start time of the run as an ID for the performance log.
performance_run_id=$(date +%s)

if [ -e $CONFIG_FILE ]; then
  source $CONFIG_FILE
else
  ### Start CONFIG ###
  DOWNLOAD_DIR=~/latest_datagetter/
  GRANTNAV_DATA_DIR=~/grantnav_data/
  GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR=/var/www/grantnav_packages/
  DATAGETTER_THREADS=16
  export DJANGO_SETTINGS_MODULE=settings.settings_examlple
  DATASTORE=~/datastore/
  DATAGETTER=~/datagetter/
  MAX_TOTAL_RUNS_IN_DB=31
  # Based on running this script each day and Keep a few extra for safety
  MAX_PACKAGE_AGE_DAYS=`expr $MAX_TOTAL_RUNS_IN_DB + 2`
  ### End CONFIG ###
  PERFORMANCE_CSV=~/data_run_profile.csv
fi


##
## Create directories and clear out old downloads before we run the pipeline.
##
profile_block_start
mkdir -p $DOWNLOAD_DIR
mkdir -p $GRANTNAV_DATA_DIR
mkdir -p $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR
rm -rf $DOWNLOAD_DIR/*
profile_block_stop "PREPARING_FOR_RUN"


##
## Run the datagetter.  Note the datagetter and datastore run on different virtualenvs.
##
profile_block_start
cd $DATASTORE
source $DATASTORE/.ve/bin/activate
./datastore/manage.py set_status --what datagetter --status IN_PROGRESS
deactivate

cd $DATAGETTER
source $DATAGETTER/.ve/bin/activate
echo_stamp "Running the datagetter"
./datagetter.py --threads $DATAGETTER_THREADS --data-dir $DOWNLOAD_DIR/data
deactivate
profile_block_stop "RUNNING_DATAGETTER"


# Uncomment for quick TESTING!!
#cp -r ~/data $DOWNLOAD_DIR/data


##
## Load the downloaded datagetter data into the datastore.
##
profile_block_start
cd $DATASTORE
source $DATASTORE/.ve/bin/activate
./datastore/manage.py set_status --what datagetter --status IDLE

echo_stamp "Load the downloaded datagetter data into datastore"
./datastore/manage.py set_status --what datastore --status LOADING_DATA

./datastore/manage.py load_datagetter_data $DOWNLOAD_DIR/data

./datastore/manage.py set_status --what datastore --status IDLE
profile_block_stop "LOADING_DATA_INTO_DATASTORE"


##
## Clean up before creating the GrantNav data package.
##
profile_block_start
echo_stamp "Create GrantNav package"
./datastore/manage.py set_status --what grantnav_data_package --status LOADING_DATA

echo_stamp "Deleting old unused datagetter data"
./datastore/manage.py delete_datagetter_data --all-not-in-use --older-than-days 90 --force-delete-in-use-data --no-prompt

echo_stamp "Deleting old GrantNav packages"
find $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR -name "data_*.tar.gz" -mtime +$MAX_PACKAGE_AGE_DAYS | xargs rm -f

# Remove old data dump
rm -rf $GRANTNAV_DATA_DIR/data || true
profile_block_stop "PREPARING_TO_MAKE_GRANTNAV_PACKAGE"


##
## Create GrantNav data package.
##
profile_block_start
echo_stamp "Creating data package"
./datastore/manage.py create_data_package --dir $GRANTNAV_DATA_DIR/data
profile_block_stop "CREATING_GRANTNAV_DATAPACKAGE_FILES"


##
## Compress data into tar gz and make it ready.
##
profile_block_start
NEW_PACKAGE_NAME=data_$(date +%F).tar.gz

echo_stamp "Compressing package into tar gz"
cd $GRANTNAV_DATA_DIR
tar -czf $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/$NEW_PACKAGE_NAME data

# Ensure the file is readable by all
chmod +r $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/$NEW_PACKAGE_NAME

# go back to original dir
cd $DATASTORE

# Create latest_grantnav_data.tar.gz symlink
rm -f $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/latest_grantnav_data.tar.gz
ln -s  $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/$NEW_PACKAGE_NAME  $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/latest_grantnav_data.tar.gz

echo_stamp "Data package ready"

./datastore/manage.py set_status --what grantnav_data_package --status READY
profile_block_stop "BUILDING_GRANTNAV_DATAPACKAGE"


##
## Create monitoring snapshot.
##
profile_block_start
echo_stamp "Create monitoring snapshot"
./datastore/manage.py set_status --what monitoring_snapshot --status IN_PROGRESS

./datastore/manage.py create_monitoring_snapshot || true # Allow to fail without bringing down the whole pipeline

./datastore/manage.py set_status --what monitoring_snapshot --status READY
profile_block_stop "CREATE_MONITORING_SNAPSHOT"
