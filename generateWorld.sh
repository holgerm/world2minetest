#!/bin/bash

# === Konfiguration ===
GENERATOR_IMAGE=w2mt-generator
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
W2MT_DIR="$SCRIPT_DIR/w2mt"
MINETEST_GAME_PATH="$SCRIPT_DIR"

# === Parameter lesen ===
if [[ -n "$1" && -n "$2" ]]; then
  WORLDNAME="$1"
  KOORDINATEN="$2"
  echo "📦 Starte mit Argumenten:"
  echo "   🌍 Welt:       $WORLDNAME"
  echo "   📍 Koordinaten: $KOORDINATEN"
else
  echo "🌍 Interaktive Weltgenerierung starten..."
  read -p "📝 Weltname (z. B. 20-testung): " WORLDNAME
  read -p "📍 Erste Koordinate (z. B. 360293, 5646989): " KOORDINATE1
  read -p "📍 Zweite Koordinate (z. B.  360802, 5647418): " KOORDINATE2
  KOORDINATEN="$KOORDINATE1,$KOORDINATE2"
fi

WORLDNUMBER="${WORLDNAME%%-*}"

# === Docker-Image bauen ===
echo "🐳 Baue Docker-Image '$GENERATOR_IMAGE'..."
docker build -t "$GENERATOR_IMAGE" "$W2MT_DIR"

# === Container starten ===
echo "🚀 Starte Weltgenerierung..."
docker run --rm \
  -e MINETEST_GAME_PATH="/mnt/projects" \
  -v "$SCRIPT_DIR":/mnt/projects \
  -v "$SCRIPT_DIR/worlds":/app/worlds \
  "$GENERATOR_IMAGE" \
  -w "$WORLDNUMBER" \
  -p "$WORLDNAME" \
  -d "/mnt/projects" \
  -a "$KOORDINATEN" \
  -g "antigrief" -m

echo "✅ Welt wurde generiert unter: $SCRIPT_DIR/worlds/$WORLDNAME"