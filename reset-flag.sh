#!/bin/bash

. /etc/default/submitter

export SCORES_DB

python reset_flag.py "$@"