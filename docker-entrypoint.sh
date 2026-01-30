#!/bin/bash
set -e

# Fix ownership of data directory for bind mounts
# This runs as root before dropping to the 'may' user
if [ -d "/app/data" ]; then
    chown -R may:may /app/data
fi

# Create uploads directory if it doesn't exist
mkdir -p /app/data/uploads
chown -R may:may /app/data

# Drop to 'may' user and run the application
exec gosu may "$@"
