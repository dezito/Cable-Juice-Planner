#!/bin/bash

# Define colors for echo output
RESET="\e[0m"
GREEN="\e[32m"
YELLOW="\e[33m"
BLUE="\e[34m"
RED="\e[31m"

# Determine REPO_DIR based on the existence of /config
if [ -d "/config" ]; then
  REPO_DIR="/config"
else
  REPO_DIR="/mnt/data/supervisor/homeassistant"
fi

# Function to prompt for yes/no or y/n
prompt_user() {
  local prompt_message=$1
  local response
  while true; do
    read -p "$prompt_message (yes/y or no/n): " response
    case "$response" in
      [Yy] | [Yy][Ee][Ss]) return 0 ;; # Return 0 for yes/y
      [Nn] | [Nn][Oo]) return 1 ;; # Return 1 for no/n
      *) echo -e "${YELLOW}Invalid input. Please enter yes/y or no/n.${RESET}" ;;
    esac
  done
}

# Ask the user if they want to uninstall Cable-Juice-Planner
echo -e "${BLUE}------------------------------------------${RESET}"
echo -e "${BLUE}        Cable-Juice-Planner Uninstall     ${RESET}"
echo -e "${BLUE}------------------------------------------${RESET}"
if ! prompt_user "Are you sure you want to uninstall Cable-Juice-Planner?"; then
  echo -e "${YELLOW}Operation aborted. No changes were made.${RESET}"
  exit 0
fi

# Function to delete matching files and subdirectories from pyscript
delete_pyscript_files() {
  local source_dir="$REPO_DIR/Cable-Juice-Planner/pyscript"
  local target_dir="$REPO_DIR/pyscript"
  
  if [ -d "$source_dir" ]; then
    echo -e "${BLUE}Checking files and subdirectories in $source_dir for deletion in $target_dir...${RESET}"
    find "$source_dir" -type f | while read -r file; do
      relative_path="${file#$source_dir/}"  # Get the relative path
      target_file="$target_dir/$relative_path"
      if [ -f "$target_file" ]; then
        echo -e "${GREEN}Deleting file: $target_file${RESET}"
        rm "$target_file"
      else
        echo -e "${YELLOW}[INFO] No matching file found for: $relative_path${RESET}"
      fi
    done
  else
    echo -e "${RED}[WARNING] Source directory $source_dir does not exist.${RESET}"
  fi
}

# Function to delete matching files from scripts
delete_script_files() {
  local source_dir="$REPO_DIR/Cable-Juice-Planner/scripts"
  local target_dir="$REPO_DIR/scripts"
  
  if [ -d "$source_dir" ]; then
    echo -e "${BLUE}Checking files in $source_dir for deletion in $target_dir...${RESET}"
    for file in "$source_dir"/*; do
      filename=$(basename "$file")
      target_file="$target_dir/$filename"
      if [ -f "$target_file" ]; then
        echo -e "${GREEN}Deleting: $target_file${RESET}"
        rm "$target_file"
      else
        echo -e "${YELLOW}[INFO] No matching file found for: $filename${RESET}"
      fi
    done
  else
    echo -e "${RED}[WARNING] Source directory $source_dir does not exist.${RESET}"
  fi
}

# Function to prompt and delete a file
ask_and_delete_file() {
  local file=$1
  local prompt=$2
  if [ -f "$file" ]; then
    if prompt_user "$prompt"; then
      echo -e "${GREEN}Deleting: $file${RESET}"
      rm "$file"
    else
      echo -e "${YELLOW}[INFO] Skipped deletion of: $file${RESET}"
    fi
  else
    echo -e "${RED}[WARNING] File $file does not exist.${RESET}"
  fi
}

# Function to prompt and delete databases
ask_and_delete_databases() {
  local databases=(
    "$REPO_DIR/ev_charging_history_db.yaml"
    "$REPO_DIR/ev_drive_efficiency_db.yaml"
    "$REPO_DIR/ev_error_log.yaml"
    "$REPO_DIR/ev_km_kwh_efficiency_db.yaml"
    "$REPO_DIR/ev_kwh_avg_prices_db.yaml"
    "$REPO_DIR/ev_solar_production_available_db.yaml"
  )
  
  if prompt_user "Do you want to delete all databases?"; then
    for db in "${databases[@]}"; do
      if [ -f "$db" ]; then
        echo -e "${GREEN}Deleting: $db${RESET}"
        rm "$db"
      else
        echo -e "${YELLOW}[INFO] Database $db does not exist.${RESET}"
      fi
    done
  else
    echo -e "${YELLOW}[INFO] No databases were deleted.${RESET}"
  fi
}

# Start of the script
echo -e "${BLUE}------------------------------------------${RESET}"
echo -e "${BLUE}       Starting Uninstall Process         ${RESET}"
echo -e "${BLUE}------------------------------------------${RESET}"

# Delete matching files in pyscript
delete_pyscript_files

# Delete matching files in scripts
delete_script_files

# Prompt and delete specific files
ask_and_delete_file "$REPO_DIR/packages/ev.yaml" "Do you want to delete $REPO_DIR/packages/ev.yaml and its entities?"
ask_and_delete_file "$REPO_DIR/ev_config.yaml" "Do you want to delete $REPO_DIR/ev_config.yaml and its configuration?"

# Prompt and delete databases
ask_and_delete_databases

echo -e "${BLUE}------------------------------------------${RESET}"
echo -e "${BLUE}       Uninstall Process Completed        ${RESET}"
echo -e "${BLUE}------------------------------------------${RESET}"
