#!/usr/bin/env bash

./.venv/bin/uwsgi --http 127.0.0.1:5000 --master -w IBU_dashboard:app 