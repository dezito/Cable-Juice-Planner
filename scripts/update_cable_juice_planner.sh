#!/bin/bash

# Check if /config directory exists, if not, use /mnt/data/supervisor/homeassistant
if [ -d "/config" ]; then
  REPO_DIR="/config"
  FOLDER_NAME="config"
else
  REPO_DIR="/mnt/data/supervisor/homeassistant"
  FOLDER_NAME="homeassistant"
fi

# Define the GitHub repository URL
REPO_URL="https://github.com/dezito/Cable-Juice-Planner.git"

cd $REPO_DIR

git $FOLDER_NAME --global --add safe.directory $REPO_DIR

# Clone the repo if it doesn't exist
if [ ! -d "$REPO_DIR/.git" ]; then
  echo "Cloning repository from $REPO_URL to $REPO_DIR"
  git clone $REPO_URL $REPO_DIR/cjp_temp
  mv cjp_temp/.git $REPO_DIR/.git
  rm -rf cjp_temp
  git pull --force
else
  # Pull the latest changes if the repo already exists
  echo "Pulling latest changes in $REPO_DIR"
  git fetch --all && git reset --hard
  git pull --force
fi