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
  cd "$REPO_DIR/Cable-Juice-Planner"
  git fetch --all && git reset --hard origin/$BRANCH
  git checkout $BRANCH
  git pull --force origin $BRANCH
fi

# Create necessary directories for pyscript based on relative paths
echo -e "\nCreating necessary directories for pyscript..."
cd "$REPO_DIR/Cable-Juice-Planner/pyscript"
find . -type d | while read -r dir; do
  # Remove leading './' from directory path
  relative_dir="${dir#./}"
  mkdir -p "$REPO_DIR/pyscript/$relative_dir"
done

# Create necessary directories for scripts based on relative paths
echo -e "\nCreating necessary directories for scripts..."
cd "$REPO_DIR/Cable-Juice-Planner/scripts"
find . -type d | while read -r dir; do
  # Remove leading './' from directory path
  relative_dir="${dir#./}"
  mkdir -p "$REPO_DIR/scripts/$relative_dir"
done

# Create hardlinks for all pyscript files
echo "Creating hardlinks for all pyscript files..."
cd "$REPO_DIR/Cable-Juice-Planner/pyscript"
find . -type f | while read -r src_file; do
  # Remove leading './' from file path
  relative_file="${src_file#./}"
  dest_file="$REPO_DIR/pyscript/$relative_file"

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
  # Remove leading './' from file path
  relative_file="${src_file#./}"
  dest_file="$REPO_DIR/scripts/$relative_file"

  # Check if the destination file exists and is not a hardlink
  if [ -e "$dest_file" ] && [ "$(stat -c %i "$PWD/$src_file")" != "$(stat -c %i "$dest_file")" ]; then
    echo "Removing old file: $dest_file (not a hardlink)"
    rm "$dest_file"
  fi

  # Create the hardlink
  ln -f "$PWD/$src_file" "$dest_file"
done

echo "All directories and hardlinks have been created successfully."

# Check and update configuration.yaml
CONFIG_FILE="$REPO_DIR/configuration.yaml"

if [ -f "$CONFIG_FILE" ]; then
  echo "Checking $CONFIG_FILE for required configurations."

  # Backup the configuration file
  cp "$CONFIG_FILE" "${CONFIG_FILE}.bak"

  # Ensure 'homeassistant:' and 'packages:' are configured
  if grep -q '^homeassistant:' "$CONFIG_FILE"; then
    if ! awk '/^homeassistant:/{found=1} found && /^\s*packages: !include_dir_named packages\//{print; exit}' "$CONFIG_FILE" > /dev/null; then
      echo "Adding 'packages: !include_dir_named packages/' under 'homeassistant:'."
      awk '/^homeassistant:/ {print; print "  packages: !include_dir_named packages/"; next}1' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    fi
  else
    echo "'homeassistant:' section not found. Adding it with 'packages: !include_dir_named packages/'."
    echo -e "\nhomeassistant:\n  packages: !include_dir_named packages/" >> "$CONFIG_FILE"
  fi

  # Ensure 'shell_command:' and 'update_cable_juice_planner' are configured
  if grep -q '^shell_command:' "$CONFIG_FILE"; then
    if ! awk '/^shell_command:/{found=1} found && /^\s*update_cable_juice_planner:/{print; exit}' "$CONFIG_FILE" > /dev/null; then
      echo "Adding 'update_cable_juice_planner' under 'shell_command:'."
      awk -v repo_dir="$REPO_DIR" '/^shell_command:/ {print; print "  update_cable_juice_planner: \"bash {print repo_dir}/Cable-Juice-Planner/scripts/update_cable_juice_planner.sh\""; next}1' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    fi
  else
    echo "'shell_command:' section not found. Adding it with 'update_cable_juice_planner'."
    echo -e "\nshell_command:\n  update_cable_juice_planner: \"bash $REPO_DIR/Cable-Juice-Planner/scripts/update_cable_juice_planner.sh\"" >> "$CONFIG_FILE"
  fi

else
  echo "$CONFIG_FILE does not exist. Please add the following configurations to your Home Assistant configuration file:"
  echo -e "\nhomeassistant:\n  packages: !include_dir_named packages/\n\nshell_command:\n  update_cable_juice_planner: \"bash $REPO_DIR/Cable-Juice-Planner/scripts/update_cable_juice_planner.sh\""
fi

echo "Configuration updated successfully."
