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

cd "$REPO_DIR/Cable-Juice-Planner"

# --- Ensure repo safety and fetch tags ---
git config --global --add safe.directory "$PWD"
git fetch --tags >/dev/null 2>&1

# --- Get local tag (fallback to v0.0.0) ---
LOCAL_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")

# --- Get latest release tag from GitHub ---
LATEST_TAG=$(curl -fsSL "https://api.github.com/repos/dezito/Cable-Juice-Planner/releases/latest" | jq -r '.tag_name // empty' || echo "")

if [ -z "$LATEST_TAG" ]; then
  echo "⚠️ Could not retrieve the latest release tag from GitHub."
  exit 1
fi

# --- Compare versions ---
echo "📦 Local version:   $LOCAL_TAG"
echo "📦 Latest release:  $LATEST_TAG"

if [ "$LOCAL_TAG" = "$LATEST_TAG" ]; then
  echo "✅ No updates available (you are on $LOCAL_TAG)"
  exit 0
else
  echo "🚀 Update available: $LATEST_TAG"
  echo
  echo "📋 What's Changed:"
  BODY=$(curl -fsSL "https://api.github.com/repos/dezito/Cable-Juice-Planner/releases/latest" | jq -r '.body // empty' || echo "")
  if [ -n "$BODY" ]; then
    echo "$BODY"
  else
    echo "✅ No release notes found."
  fi
  exit 2
fi
