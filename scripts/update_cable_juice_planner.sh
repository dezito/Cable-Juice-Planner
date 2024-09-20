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

# Ensure base directories exist
mkdir -p "$REPO_DIR/packages"
mkdir -p "$REPO_DIR/Cable-Juice-Planner"
mkdir -p "$REPO_DIR/scripts"

# Check if .git directory exists in REPO_DIR and contains the correct remote URL
if [ -f "$REPO_DIR/.git/config" ]; then
  if grep -q '\[remote "origin"\]' "$REPO_DIR/.git/config" && grep -q "url = $REPO_URL" "$REPO_DIR/.git/config"; then
    echo "Found .git/config with correct remote URL in $REPO_DIR. Moving .git to $REPO_DIR/Cable-Juice-Planner"
    mv $REPO_DIR/.git $REPO_DIR/Cable-Juice-Planner/.git
  fi
fi

# Remove 'cards', 'config_examples', and 'images' files if they exist in Cable-Juice-Planner, then remove the directories if they are empty
for folder in cards config_examples images; do
  if [ -d "$REPO_DIR/$folder" ]; then
    # Iterate through all files in the folder
    find "$REPO_DIR/$folder" -type f | while read -r file_path; do
      # Construct the corresponding file path in Cable-Juice-Planner
      relative_path="${file_path#$REPO_DIR/}"
      corresponding_file="$REPO_DIR/Cable-Juice-Planner/$relative_path"

      # Check if the file exists in Cable-Juice-Planner
      if [ -f "$corresponding_file" ]; then
        echo "Removing file: $file_path (exists in Cable-Juice-Planner)"
        rm "$file_path"
      fi
    done

    # After removing the files, check if the folder is empty and remove it if so
    if [ -z "$(find "$REPO_DIR/$folder" -type f)" ]; then
      echo "Removing empty folder: $REPO_DIR/$folder"
      rm -rf "$REPO_DIR/$folder"
    fi
  fi
done

# Git configuration
git config --global --add safe.directory $REPO_DIR/Cable-Juice-Planner

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

# Automatically create all directories in pyscript and scripts based on the repository structure
echo -e "\nCreating necessary directories for pyscript and scripts based on repository..."

# Find and create all directories in Cable-Juice-Planner/pyscript and Cable-Juice-Planner/scripts
find $REPO_DIR/Cable-Juice-Planner/pyscript -type d | while read -r dir; do
  # Remove the $REPO_DIR/Cable-Juice-Planner/pyscript part from the path to get the relative path
  relative_dir=$(realpath --relative-to="$REPO_DIR/Cable-Juice-Planner/pyscript" "$dir")
  echo "Creating directory: $REPO_DIR/pyscript/$relative_dir"
  mkdir -p "$REPO_DIR/pyscript/$relative_dir"
done

find $REPO_DIR/Cable-Juice-Planner/scripts -type d | while read -r dir; do
  # Remove the $REPO_DIR/Cable-Juice-Planner/scripts part from the path to get the relative path
  relative_dir=$(realpath --relative-to="$REPO_DIR/Cable-Juice-Planner/scripts" "$dir")
  echo "Creating directory: $REPO_DIR/scripts/$relative_dir"
  mkdir -p "$REPO_DIR/scripts/$relative_dir"
done

# Create hardlinks for all files in pyscript and its subdirectories
echo "Creating hardlinks for all pyscript files..."
find $REPO_DIR/Cable-Juice-Planner/pyscript -type f | while read -r src_file; do
  dest_file="$REPO_DIR/pyscript/$(realpath --relative-to="$REPO_DIR/Cable-Juice-Planner/pyscript" "$src_file")"

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
  dest_file="$REPO_DIR/scripts/$(realpath --relative-to="$REPO_DIR/Cable-Juice-Planner/scripts" "$src_file")"

  # Check if the destination file exists and is not a hardlink
  if [ -e "$dest_file" ] && [ "$(stat -c %i "$src_file")" != "$(stat -c %i "$dest_file")" ]; then
    echo "Removing old file: $dest_file (not a hardlink)"
    rm "$dest_file"
  fi

  # Create the hardlink
  ln -n "$src_file" "$dest_file"
done

echo "All directories and hardlinks have been created successfully."
