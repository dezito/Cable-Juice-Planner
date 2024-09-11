#!/bin/bash

# Check if /config directory exists, if not, use /mnt/data/supervisor/homeassistant
if [ -d "/config" ]; then
  REPO_DIR="/config"
else
  REPO_DIR="/mnt/data/supervisor/homeassistant"
fi

# Define the GitHub repository URL
REPO_URL="https://github.com/dezito/Cable-Juice-Planner.git"

# Check if branch argument is passed, otherwise use default branch (master)
BRANCH=${1:-master}

# Ensure Cable-Juice-Planner directory exists
cd $REPO_DIR

if [ ! -d "$REPO_DIR/Cable-Juice-Planner" ]; then
  mkdir -p $REPO_DIR/Cable-Juice-Planner
fi

# Git configuration
git config --global --add safe.directory $REPO_DIR/Cable-Juice-Planner

# Clone the repo if it doesn't exist, otherwise pull latest changes
if [ ! -d "$REPO_DIR/Cable-Juice-Planner/.git" ]; then
  echo "Cloning repository from $REPO_URL (branch: $BRANCH) to $REPO_DIR/Cable-Juice-Planner"
  git clone --branch $BRANCH $REPO_URL $REPO_DIR/Cable-Juice-Planner
else
  echo "Pulling latest changes from branch $BRANCH in $REPO_DIR/Cable-Juice-Planner"
  cd $REPO_DIR/Cable-Juice-Planner
  git fetch --all && git reset --hard origin/$BRANCH
  git checkout $BRANCH
  git pull --force origin $BRANCH
fi

# Automatically create all directories in pyscript/modules and pyscript/modules/mytime
echo "Creating necessary directories in pyscript/modules..."
find $REPO_DIR/Cable-Juice-Planner/pyscript -type d -exec mkdir -p $REPO_DIR/pyscript/{} \;

# Create hardlinks for all files in pyscript and its subdirectories
echo "Creating hardlinks for all pyscript files..."
find $REPO_DIR/Cable-Juice-Planner/pyscript -type f -exec ln -n $REPO_DIR/Cable-Juice-Planner/{} $REPO_DIR/pyscript/{} \;

# Create hardlinks for scripts
echo "Creating hardlinks for scripts..."
find $REPO_DIR/Cable-Juice-Planner/scripts -type f -exec ln -n $REPO_DIR/Cable-Juice-Planner/{} $REPO_DIR/scripts/{} \;

echo "All directories and hardlinks have been created successfully."
