#!/bin/bash

. /etc/default/submitter

export SCORES_DB

python3 reset_flag.py "$@"
