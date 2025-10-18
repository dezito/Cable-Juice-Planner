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

# --- Base repo path ---
REPO_PATH="$REPO_DIR/Cable-Juice-Planner"

if [ ! -d "$REPO_PATH" ]; then
  echo "❌ Cable-Juice-Planner folder not found in $REPO_DIR"
  exit 1
fi

# --- Ensure destination folders exist ---
mkdir -p "$REPO_DIR/pyscript" "$REPO_DIR/scripts"

# --- Function to create hardlinks recursively ---
create_links() {
  SRC="$1"
  DST="$2"
  echo "🔗 Linking from $SRC → $DST"

  cd "$SRC"
  find . -type d -exec mkdir -p "$DST/{}" \;
  find . -type f | while read -r f; do
    SRC_FILE="$SRC/$f"
    DST_FILE="$DST/$f"

    # Check if destination exists but is not a hardlink
    if [ -e "$DST_FILE" ] && [ "$(stat -c %i "$SRC_FILE")" != "$(stat -c %i "$DST_FILE")" ]; then
      echo "🧹 Removing outdated file: $DST_FILE"
      rm -f "$DST_FILE"
    fi

    # Create hardlink
    ln -f "$SRC_FILE" "$DST_FILE"
  done
}

# --- Run for pyscript and scripts ---
if [ -d "$REPO_PATH/pyscript" ]; then
  create_links "$REPO_PATH/pyscript" "$REPO_DIR/pyscript"
else
  echo "⚠️ No pyscript folder found in $REPO_PATH"
fi

if [ -d "$REPO_PATH/scripts" ]; then
  create_links "$REPO_PATH/scripts" "$REPO_DIR/scripts"
else
  echo "⚠️ No scripts folder found in $REPO_PATH"
fi

echo "✅ All hardlinks created successfully."