#!/bin/bash -x
# Example data_run.sh with proxy
# Assumes git repo is cloned in ~/datastore/

### Start CONFIG ###
SOCKS5_PORT=1337
SSH_SERVER=SETME
DOWNLOAD_DIR=~/latest_datagetter/
GRANTNAV_DATA_DIR=~/grant_nav_data/
GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR=~/grant_nav_packages/
DATAGETTER_THREADS=16
MAX_TOTAL_RUNS_IN_DB=20

### End CONFIG ###

mkdir -p $DOWNLOAD_DIR
mkdir -p $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR

source ~/datastore/.ve/bin/activate

echo "Start the proxy"
ssh -D $SOCKS5_PORT -q -C -N $SSH_SERVER &
PROXY_PID=$!

cd ~/datastore/
./datastore/manage.py set_status --what datagetter --status IN_PROGRESS

echo "Running the datagetter"
datagetter.py --threads $DATAGETTER_THREADS --socks5 socks5://localhost:$SOCKS5_PORT --data-dir $DOWNLOAD_DIR

./datastore/manage.py set_status --what datagetter --status IDLE

echo "Shutting down proxy"
kill -HUP $PROXY_PID


echo "Load the downloaded datagetter data into datastore"
./datastore/manage.py set_status --what datastore --status LOADING_DATA

./datastore/manage.py load_datagetter_data $DOWNLOAD_DIR

./datastore/manage.py set_status --what datastore --status IDLE

echo "Create grant nav package"
./datastore/manage.py set_status --what grantnav_data_package --status LOADING_DATA

# Remove old data dump
rm -rf $GRANTNAV_DATA_DIR || true
./datastore/manage.py create_datagetter_data --dir $GRANTNAV_DATA_DIR

NEW_PACKAGE_NAME=data_$(date +%F).tar.gz

tar -czf $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/$NEW_PACKAGE_NAME $GRANTNAV_DATA_DIR

# Create latest_grantnav_data.tar.gz symlink
rm $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/latest_grantnav_data.tar.gz
ln -s  $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/$NEW_PACKAGE_NAME  $GRANTNAV_DATA_PACKAGE_DOWNLOAD_DIR/latest_grantnav_data.tar.gz

./datastore/manage.py set_status --what grantnav_data_package --status READY

# Delete datagetter runs if we have reached the max
TOTAL_RUNS=`./datastore/manage.py list_datagetter_runs --total`

if [ $TOTAL_RUNS -gt $MAX_TOTAL_RUNS_IN_DB ]; then
    echo "Deleteing oldest datagetter data"
    ./datastore/manage.py delete_datagetter_data --oldest --no-prompt
fi