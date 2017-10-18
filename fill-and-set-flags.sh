#!/bin/bash

sqlite3 /var/lib/submitter/db/scores.db < flags.sql
./reset-flag.sh