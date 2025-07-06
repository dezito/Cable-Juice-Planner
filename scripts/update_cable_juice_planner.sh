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

# Definer GitHub repository URL
REPO_URL="https://github.com/dezito/Cable-Juice-Planner.git"

# Tjekker om branch-argumentet er givet, ellers brug standardbranchen (master)
BRANCH=${1:-master}

# Sikrer at basismapper eksisterer
mkdir -p "$REPO_DIR/packages"
mkdir -p "$REPO_DIR/Cable-Juice-Planner"
mkdir -p "$REPO_DIR/scripts"
mkdir -p "$REPO_DIR/pyscript"

# Kloner repoet, hvis det ikke eksisterer, ellers henter seneste ændringer
if [ ! -d "$REPO_DIR/Cable-Juice-Planner/.git" ]; then
  echo -e "\nKloner repository fra $REPO_URL (branch: $BRANCH) til $REPO_DIR/Cable-Juice-Planner"
  git clone --branch $BRANCH $REPO_URL $REPO_DIR/Cable-Juice-Planner
else
  echo -e "\nHenter seneste ændringer fra branch $BRANCH i $REPO_DIR/Cable-Juice-Planner"
  cd "$REPO_DIR/Cable-Juice-Planner"
  git config --global --add safe.directory $REPO_DIR/Cable-Juice-Planner
  git fetch --all && git reset --hard origin/$BRANCH
  git checkout $BRANCH
  git pull --force origin $BRANCH
fi

# Opretter nødvendige mapper for pyscript baseret på relative stier
echo -e "\nOpretter nødvendige mapper for pyscript..."
cd "$REPO_DIR/Cable-Juice-Planner/pyscript"
find . -type d | while read -r dir; do
  # Fjerner indledende './' fra mappestien
  relative_dir="${dir#./}"
  mkdir -p "$REPO_DIR/pyscript/$relative_dir"
done

# Opretter nødvendige mapper for scripts baseret på relative stier
echo -e "\nOpretter nødvendige mapper for scripts..."
cd "$REPO_DIR/Cable-Juice-Planner/scripts"
find . -type d | while read -r dir; do
  # Fjerner indledende './' fra mappestien
  relative_dir="${dir#./}"
  mkdir -p "$REPO_DIR/scripts/$relative_dir"
done

# Opretter hardlinks for alle pyscript-filer
echo "Opretter hardlinks for alle pyscript-filer..."
cd "$REPO_DIR/Cable-Juice-Planner/pyscript"
find . -type f | while read -r src_file; do
  # Fjerner indledende './' fra filstien
  relative_file="${src_file#./}"
  dest_file="$REPO_DIR/pyscript/$relative_file"

  # Tjekker om destinationsfilen eksisterer og ikke er et hardlink
  if [ -e "$dest_file" ] && [ "$(stat -c %i "$PWD/$src_file")" != "$(stat -c %i "$dest_file")" ]; then
    echo "Fjerner gammel fil: $dest_file (ikke et hardlink)"
    rm "$dest_file"
  fi

  # Opretter hardlinket
  ln -f "$PWD/$src_file" "$dest_file"
done

# Opretter hardlinks for scripts
echo "Opretter hardlinks for scripts..."
cd "$REPO_DIR/Cable-Juice-Planner/scripts"
find . -type f | while read -r src_file; do
  # Fjerner indledende './' fra filstien
  relative_file="${src_file#./}"
  dest_file="$REPO_DIR/scripts/$relative_file"

  # Tjekker om destinationsfilen eksisterer og ikke er et hardlink
  if [ -e "$dest_file" ] && [ "$(stat -c %i "$PWD/$src_file")" != "$(stat -c %i "$dest_file")" ]; then
    echo "Fjerner gammel fil: $dest_file (ikke et hardlink)"
    rm "$dest_file"
  fi

  # Opretter hardlinket
  ln -f "$PWD/$src_file" "$dest_file"
done

echo "Alle mapper og hardlinks er oprettet med succes."

# Tjekker og opdaterer configuration.yaml
CONFIG_FILE="$REPO_DIR/configuration.yaml"

CONFIG_CHANGED=0

if [ -f "$CONFIG_FILE" ]; then
  # Sikkerhedskopierer konfigurationsfilen
  cp "$CONFIG_FILE" "${CONFIG_FILE}.bak"

  # Sikrer at 'homeassistant:' og 'packages:' er konfigureret
  if ! grep -q '^homeassistant:' "$CONFIG_FILE"; then
    echo "Tilføjer 'homeassistant:' sektion med 'packages: !include_dir_named packages/'."
    echo -e "\nhomeassistant:\n  packages: !include_dir_named packages/" >> "$CONFIG_FILE"
    CONFIG_CHANGED=1
  else
    if ! awk '/^homeassistant:/{found=1} found && /^\s*packages: !include_dir_named packages\//{print; exit}' "$CONFIG_FILE" > /dev/null; then
      echo "Tilføjer 'packages: !include_dir_named packages/' under 'homeassistant:'."
      awk '/^homeassistant:/ {print; print "  packages: !include_dir_named packages/"; next}1' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
      CONFIG_CHANGED=1
    fi
  fi

  # Sikrer at 'shell_command:' og 'update_cable_juice_planner' er konfigureret
  if ! grep -q '^shell_command:' "$CONFIG_FILE"; then
    echo "Tilføjer 'shell_command:' sektion med 'update_cable_juice_planner'."
    echo -e "\nshell_command:\n  update_cable_juice_planner: \"bash $REPO_DIR/Cable-Juice-Planner/scripts/update_cable_juice_planner.sh\"" >> "$CONFIG_FILE"
    CONFIG_CHANGED=1
  else
    if ! awk '/^shell_command:/{found=1} found && /^\s*update_cable_juice_planner:/{print; exit}' "$CONFIG_FILE" > /dev/null; then
      echo "Tilføjer 'update_cable_juice_planner' under 'shell_command:'."
      awk -v repo_dir="$REPO_DIR" '/^shell_command:/ {print; print "  update_cable_juice_planner: \"bash " repo_dir "/Cable-Juice-Planner/scripts/update_cable_juice_planner.sh\""; next}1' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
      CONFIG_CHANGED=1
    fi
  fi

  if [ "$CONFIG_CHANGED" -eq 1 ]; then
    echo "Konfigurationen er opdateret med succes."
  fi
else
  echo "$CONFIG_FILE findes ikke. Opretter den med nødvendige konfigurationer."
  cat <<EOL > "$CONFIG_FILE"
homeassistant:
  packages: !include_dir_named packages/

shell_command:
  update_cable_juice_planner: "bash $REPO_DIR/Cable-Juice-Planner/scripts/update_cable_juice_planner.sh"
EOL
  echo "Konfigurationsfil oprettet og opdateret med succes."
fi
