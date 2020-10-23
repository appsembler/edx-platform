#!/bin/bash

mkdir -p /data/db
mongod --fork --logpath /tmp/mongod.log

# Clear the mongo database
# Note that this prevents us from running jobs in parallel on a single worker.
mongo --quiet --eval 'db.getMongo().getDBNames().forEach(function(i){db.getSiblingDB(i).dropDatabase()})'

TOXENV=pep8 /edx/app/edxapp/venvs/edxapp/bin/tox
TOXENV=py35-django22-common /edx/app/edxapp/venvs/edxapp/bin/tox
# py38 is not yet working
