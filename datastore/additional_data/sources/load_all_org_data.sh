#!/bin/bash
# Load all the different types of org data from Find That Charity.

# NOTE: This file is run from a cron job, defined in the deploy repo.

./manage.py load_org_data --all-ftc-sources --replace
