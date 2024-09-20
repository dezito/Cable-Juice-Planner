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

# Ensure base directories exist
mkdir -p "$REPO_DIR/packages"
mkdir -p "$REPO_DIR/Cable-Juice-Planner"
mkdir -p "$REPO_DIR/scripts"
mkdir -p "$REPO_DIR/pyscript"

# Clone the repo if it doesn't exist, otherwise pull latest changes
if [ ! -d "$REPO_DIR/Cable-Juice-Planner/.git" ]; then
  echo -e "\nCloning repository from $REPO_URL (branch: $BRANCH) to $REPO_DIR/Cable-Juice-Planner"
  git clone --branch $BRANCH $REPO_URL $REPO_DIR/Cable-Juice-Planner
else
  echo -e "\nPulling latest changes from branch $BRANCH in $REPO_DIR/Cable-Juice-Planner"
  cd $REPO_DIR/Cable-Juice-Planner
  git fetch --all && git reset --hard origin/$BRANCH
  git checkout $BRANCH
  git pull --force origin $BRANCH
fi

# Create necessary directories for pyscript based on relative paths
echo -e "\nCreating necessary directories for pyscript..."
cd "$REPO_DIR/Cable-Juice-Planner/pyscript"
find . -type d | while read -r dir; do
  # Ensure there is no leading './' in the directory path
  relative_dir=$(echo "$dir" | sed 's|^\./||')
  echo "Creating directory: $REPO_DIR/pyscript/$relative_dir"
  mkdir -p "$REPO_DIR/pyscript/$relative_dir"
done

# Create necessary directories for scripts based on relative paths
echo -e "\nCreating necessary directories for scripts..."
cd "$REPO_DIR/Cable-Juice-Planner/scripts"
find . -type d | while read -r dir; do
  # Ensure there is no leading './' in the directory path
  relative_dir=$(echo "$dir" | sed 's|^\./||')
  echo "Creating directory: $REPO_DIR/scripts/$relative_dir"
  mkdir -p "$REPO_DIR/scripts/$relative_dir"
done

# Create hardlinks for all pyscript files
echo "Creating hardlinks for all pyscript files..."
cd "$REPO_DIR/Cable-Juice-Planner/pyscript"
find . -type f | while read -r src_file; do
  # Ensure there is no leading './' in the file path
  dest_file="$REPO_DIR/pyscript/$(echo "$src_file" | sed 's|^\./||')"

  # Check if the destination file exists and is not a hardlink
  if [ -e "$dest_file" ] && [ "$(stat -c %i "$PWD/$src_file")" != "$(stat -c %i "$dest_file")" ]; then
    echo "Removing old file: $dest_file (not a hardlink)"
    rm "$dest_file"
  fi

  # Create the hardlink
  ln -f "$PWD/$src_file" "$dest_file"
done

# Create hardlinks for scripts
echo "Creating hardlinks for scripts..."
cd "$REPO_DIR/Cable-Juice-Planner/scripts"
find . -type f | while read -r src_file; do
  # Ensure there is no leading './' in the file path
  dest_file="$REPO_DIR/scripts/$(echo "$src_file" | sed 's|^\./||')"

  # Check if the destination file exists and is not a hardlink
  if [ -e "$dest_file" ] && [ "$(stat -c %i "$PWD/$src_file")" != "$(stat -c %i "$dest_file")" ]; then
    echo "Removing old file: $dest_file (not a hardlink)"
    rm "$dest_file"
  fi

  # Create the hardlink
  ln -f "$PWD/$src_file" "$dest_file"
done

echo "All directories and hardlinks have been created successfully."
