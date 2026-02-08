#!/bin/bash
docker run --rm --name openmetadata-migrate --network local_one-data-network \
  -e DB_DRIVER_CLASS=org.postgresql.Driver \
  -e DB_SCHEME=postgresql \
  -e DB_HOST=openmetadata-postgresql \
  -e DB_PORT=5432 \
  -e DB_USER=openmetadata \
  -e DB_USER_PASSWORD=openmetadata_password \
  -e OM_DATABASE=openmetadata_db \
  -e ELASTICSEARCH_HOST=elasticsearch \
  -e ELASTICSEARCH_PORT=9200 \
  openmetadata/server:latest \
  /opt/openmetadata/bootstrap/openmetadata-ops.sh migrate
