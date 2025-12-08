#!/usr/bin/env bash

crond
./.venv/bin/uwsgi --http 0.0.0.0:5000 --master --enable-threads --lazy-apps -w IBU_dashboard:app