#!/bin/bash

# Check if /config directory exists, if not, use /mnt/data/supervisor/homeassistant
if [ -d "/config" ]; then
  REPO_DIR="/config"
else
  REPO_DIR="/mnt/data/supervisor/homeassistant"
fi

# Define the GitHub repository URL
REPO_URL="https://github.com/dezito/Cable-Juice-Planner.git"

cd $REPO_DIR/Cable-Juice-Planner

# Check if branch argument is passed, otherwise use default branch (master)
BRANCH=${1:-master}

# Fetch den seneste branch info fra fjernrepository
git fetch origin $BRANCH

# Sammenlign den lokale HEAD med den fjernede HEAD for den specifikke branch
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/$BRANCH)

if [ $LOCAL = $REMOTE ]; then
    echo "No updates available on branch $BRANCH"
else
    echo "Updates available on branch $BRANCH"
fi
