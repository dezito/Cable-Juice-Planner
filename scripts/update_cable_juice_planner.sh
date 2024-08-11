#!/bin/bash

# Define the local directory where the repository will be cloned
REPO_DIR="/config"
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