#!/usr/bin/env python3
# Example poller script to be run periodically on grantnav server

import argparse
import datetime
import subprocess

import requests


def d_print(msg):
    print("%s: %s" % (datetime.datetime.now().strftime("%c"), msg))


def fetch_data_package(download_url, auth):
    d_print("Downloading data package %s" % download_url)
    with requests.get(download_url, stream=True, auth=auth) as r:
        r.raise_for_status()
        with open("latest_grantnav_data.tar.gz", "wb") as f:
            # 8 MiB chunks
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--url", dest="url", action="store", required=True)
    parser.add_argument("--username", dest="user", action="store")
    parser.add_argument("--password", dest="password", action="store")
    parser.add_argument(
        "--load-grantnav-script",
        dest="load_grantnav_script",
        action="store",
        required=True,
    )

    args = parser.parse_args()

    auth = None

    if args.user and args.password:
        auth = (args.user, args.password)

    # Fetch the datastore status json
    r = requests.get(args.url, auth=auth)
    r.raise_for_status()
    data = r.json()

    grantnav_dp_status = data.get("grantnav_data_package", None)

    if grantnav_dp_status is None:
        d_print("No grantnav_data_packages status yet")
        return

    if "ready" in grantnav_dp_status["status"]:
        try:
            with open("last_grantnav_fetch", "r") as last_fetchfp:
                last_data = last_fetchfp.read()
                # If the file contains a date we already have and is not blank then
                # skip it
                if len(last_data) > 0 and last_data in grantnav_dp_status["when"]:
                    d_print("Already got this package. Skipping")
                    return
        except FileNotFoundError:
            pass

        # Update the file with the last update date
        with open("last_grantnav_fetch", "w+") as last_fetchfp:
            last_fetchfp.write(grantnav_dp_status["when"])

        fetch_data_package(grantnav_dp_status["download"], auth)
        subprocess.check_call(["bash", args.load_grantnav_script])


if __name__ == "__main__":
    main()
