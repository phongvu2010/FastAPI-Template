#! /usr/bin/env bash

set -e
set -x

# Let the DB start
# python app/backend_pre_start.py

# Create migrations
# alembic revision --autogenerate -m "initialize_models"

# Run migrations
alembic upgrade head

# Create initial data in DB
python -m app.initial_data
