#!/bin/bash
set -e

# --- Locate Home Assistant config directory ---
if [ -d "/config" ]; then
  CONFIG_PATH="/config"
else
  echo "🔍 Searching for Home Assistant directory..."
  while IFS= read -r HA_FILE; do
    DIR_PATH=$(dirname "$HA_FILE")
    if [ -f "$DIR_PATH/configuration.yaml" ]; then
      CONFIG_PATH="$DIR_PATH"
      break
    fi
  done < <(find /mnt -type f -name ".HA_VERSION" 2>/dev/null)

  if [ -z "$CONFIG_PATH" ]; then
    echo "❌ Could not find a Home Assistant directory containing both .HA_VERSION and configuration.yaml."
    exit 1
  fi
fi

# --- Base repo path ---
REPO_PATH="$CONFIG_PATH/Cable-Juice-Planner"

if [ ! -d "$REPO_PATH" ]; then
  echo "❌ Cable-Juice-Planner folder not found in $CONFIG_PATH"
  exit 1
fi

# --- Ensure destination folders exist ---
mkdir -p "$CONFIG_PATH/pyscript" "$CONFIG_PATH/scripts"

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
  create_links "$REPO_PATH/pyscript" "$CONFIG_PATH/pyscript"
else
  echo "⚠️ No pyscript folder found in $REPO_PATH"
fi

if [ -d "$REPO_PATH/scripts" ]; then
  create_links "$REPO_PATH/scripts" "$CONFIG_PATH/scripts"
else
  echo "⚠️ No scripts folder found in $REPO_PATH"
fi

# --- Scan root pyscript files for Cable Juice Planner TITLE ---
echo -e "\n🔍 Scanning for additional pyscript modules containing Cable Juice Planner TITLE..."
MATCHED_FILES=$(grep -l 'TITLE = f"Cable Juice Planner ({__name__}.py)"' "$CONFIG_PATH/pyscript"/*.py 2>/dev/null || true)

# --- Remove ev.py from the list completely ---
MATCHED_FILES=$(echo "$MATCHED_FILES" | grep -v '/ev.py$' || true)

if [ -z "$MATCHED_FILES" ]; then
  echo "ℹ️ No other Cable Juice Planner pyscripts found with matching TITLE."
else
  for SRC_FILE in $MATCHED_FILES; do
    BASENAME=$(basename "$SRC_FILE")
    DST_FILE="$CONFIG_PATH/pyscript/$BASENAME"

    if [ -e "$DST_FILE" ] && [ "$(stat -c %i "$SRC_FILE")" = "$(stat -c %i "$DST_FILE")" ]; then
      echo "ℹ️ Relinking: $BASENAME"
    fi

    # Remove file if not a hardlink
    if [ -e "$DST_FILE" ]; then
      echo "🧹 Removing file: $DST_FILE"
      rm -f "$DST_FILE"
    fi

    # Create new hardlink
    ln -f "$REPO_PATH/pyscript/ev.py" "$DST_FILE"
    echo "🔗 Linked: $BASENAME"
  done
fi

echo -e "\n🎉 All hardlinks created successfully."
