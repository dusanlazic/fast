#!/bin/bash
CONTAINER_NAME="fast_database_container"
DB_NAME="fast"
POSTGRES_USER="admin"
POSTGRES_PASSWORD="admin"
POSTGRES_PORT=5432

docker pull postgres:alpine
docker run --name $CONTAINER_NAME -e POSTGRES_DB=$DB_NAME -e POSTGRES_USER=$POSTGRES_USER -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD -p $POSTGRES_PORT:5432 -d postgres

echo "Postgres is now running."
