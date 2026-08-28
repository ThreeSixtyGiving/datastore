#!/bin/bash
set -euo pipefail

# Replace all additional data i.e. delete the old, load in the new

manage_py="./manage.py"

set -x

# 360 CodeLists

$manage_py load_codelist_codes

# Geo data

$manage_py load_geocode_names # CHD Data
$manage_py load_geolookups    # DK's geo-lookups
$manage_py load_nspl

# Registry funders

$manage_py load_registry_funders

# Org data

$manage_py load_org_data --all-ftc-sources --replace

# $manage_py rewrite_additional_data
# $manage_py rewrite_quality_data
