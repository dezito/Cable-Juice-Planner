#!/bin/bash

# Forsøg først at bruge den normale sti
if [ -d "/config" ]; then
  REPO_DIR="/config"
else
  echo "🔍 Søger efter Home Assistant-mappe..."
  # Find alle forekomster af .HA_VERSION under /mnt
  while IFS= read -r HA_FILE; do
    DIR_PATH=$(dirname "$HA_FILE")
    if [ -f "$DIR_PATH/configuration.yaml" ]; then
      REPO_DIR="$DIR_PATH"
      break
    fi
  done < <(find /mnt -type f -name ".HA_VERSION" 2>/dev/null)

  # Hvis intet blev fundet
  if [ -z "$REPO_DIR" ]; then
    echo "Kunne ikke finde en Home Assistant-mappe med både .HA_VERSION og configuration.yaml."
    exit 1
  fi
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
