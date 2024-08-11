#!/bin/bash

# Check if /config directory exists, if not, use /mnt/data/supervisor/homeassistant
if [ -d "/config" ]; then
  REPO_DIR="/config"
else
  REPO_DIR="/mnt/data/supervisor/homeassistant"
fi

# Define the GitHub repository URL
REPO_URL="https://github.com/dezito/Cable-Juice-Planner.git"

# Clone the repo if it doesn't exist
if [ ! -d "$REPO_DIR/.git" ]; then
  echo "Cloning repository from $REPO_URL to $REPO_DIR"
  git clone $REPO_URL $REPO_DIR
else
  # Pull the latest changes if the repo already exists
  echo "Pulling latest changes in $REPO_DIR"
  cd $REPO_DIR
  git pull
fi