#!/bin/bash
set -e

# --- Locate Home Assistant config directory ---
if [ -d "/config" ]; then
  REPO_DIR="/config"
else
  echo "🔍 Searching for Home Assistant directory..."
  while IFS= read -r HA_FILE; do
    DIR_PATH=$(dirname "$HA_FILE")
    if [ -f "$DIR_PATH/configuration.yaml" ]; then
      REPO_DIR="$DIR_PATH"
      break
    fi
  done < <(find /mnt -type f -name ".HA_VERSION" 2>/dev/null)

  if [ -z "$REPO_DIR" ]; then
    echo "❌ Could not find a Home Assistant directory containing both .HA_VERSION and configuration.yaml."
    exit 1
  fi
fi

REPO_URL="https://github.com/dezito/Cable-Juice-Planner.git"
TARGET_TAG=${1:-latest}  # Example: ./update_cable_juice_planner.sh v1.3.0

# --- Ensure base directories exist ---
mkdir -p "$REPO_DIR/packages" "$REPO_DIR/pyscript" "$REPO_DIR/scripts" "$REPO_DIR/Cable-Juice-Planner"

# --- Clone or update the repository ---
if [ ! -d "$REPO_DIR/Cable-Juice-Planner/.git" ]; then
  echo "🧩 Cloning repository from $REPO_URL"
  git clone "$REPO_URL" "$REPO_DIR/Cable-Juice-Planner"
fi

cd "$REPO_DIR/Cable-Juice-Planner"
git config --global --add safe.directory "$PWD"
git fetch --tags >/dev/null 2>&1

# --- Determine which tag to install ---
if [ "$TARGET_TAG" = "latest" ]; then
  TARGET_TAG=$(curl -s https://api.github.com/repos/dezito/Cable-Juice-Planner/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
fi

if [ -z "$TARGET_TAG" ]; then
  echo "❌ Could not determine a valid release tag."
  exit 1
fi

# --- Get current local tag ---
LOCAL_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")

echo "📦 Updating from $LOCAL_TAG → $TARGET_TAG"

# --- Checkout the selected tag ---
git fetch --all >/dev/null 2>&1
git checkout -f "$TARGET_TAG"

# --- Create hardlinks (sync pyscript & scripts) ---
echo "🔗 Creating hardlinks..."
link_tree() {
  SRC="$1"
  DST="$2"
  cd "$SRC"
  find . -type d -exec mkdir -p "$DST/{}" \;
  find . -type f | while read -r f; do
    ln -f "$SRC/$f" "$DST/$f"
  done
}

link_tree "$REPO_DIR/Cable-Juice-Planner/pyscript" "$REPO_DIR/pyscript"
link_tree "$REPO_DIR/Cable-Juice-Planner/scripts" "$REPO_DIR/scripts"

echo "✅ All hardlinks created successfully."

# --- Display release notes ---
BODY=$(curl -s "https://api.github.com/repos/dezito/Cable-Juice-Planner/releases/tags/$TARGET_TAG" | jq -r '.body')
echo
echo "📋 What's Changed in $TARGET_TAG:"
echo "${BODY:-No release notes found.}"
echo
echo "🎉 Repository updated to $TARGET_TAG!"
