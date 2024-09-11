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

# Check if .git directory exists in REPO_DIR and contains the correct remote URL
if [ -f "$REPO_DIR/.git/config" ]; then
  if grep -q '\[remote "origin"\]' "$REPO_DIR/.git/config" && grep -q "url = $REPO_URL" "$REPO_DIR/.git/config"; then
    echo "Found .git/config with correct remote URL in $REPO_DIR. Moving .git to $REPO_DIR/Cable-Juice-Planner"
    mv $REPO_DIR/.git $REPO_DIR/Cable-Juice-Planner/.git
  else
    echo "No valid remote URL in .git/config. Skipping .git move."
  fi
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
find $REPO_DIR/Cable-Juice-Planner/pyscript -type f | while read -r src_file; do
  dest_file="$REPO_DIR/pyscript/${src_file#$REPO_DIR/Cable-Juice-Planner/pyscript/}"

  # Check if the destination file exists and is not a hardlink
  if [ -e "$dest_file" ] && [ "$(stat -c %i "$src_file")" != "$(stat -c %i "$dest_file")" ]; then
    echo "Removing old file: $dest_file (not a hardlink)"
    rm "$dest_file"
  fi

  # Create the hardlink
  ln -n "$src_file" "$dest_file"
done

# Create hardlinks for scripts
echo "Creating hardlinks for scripts..."
find $REPO_DIR/Cable-Juice-Planner/scripts -type f | while read -r src_file; do
  dest_file="$REPO_DIR/scripts/${src_file#$REPO_DIR/Cable-Juice-Planner/scripts/}"

  # Check if the destination file exists and is not a hardlink
  if [ -e "$dest_file" ] && [ "$(stat -c %i "$src_file")" != "$(stat -c %i "$dest_file")" ]; then
    echo "Removing old file: $dest_file (not a hardlink)"
    rm "$dest_file"
  fi

  # Create the hardlink
  ln -n "$src_file" "$dest_file"
done

echo "All directories and hardlinks have been created successfully."
