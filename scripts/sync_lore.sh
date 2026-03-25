#!/usr/bin/env bash
# sync_lore.sh — Syncs canonical lore/ to backend/config/ and invalidates ChromaDB cache.
#
# Usage:
#   bash scripts/sync_lore.sh           # from project root
#   make sync-lore                       # via Makefile shortcut
#
# What it does:
#   1. Copies changed lore files to backend/config/
#   2. If world.md or any bestiary_tN.md changed, deletes backend/chroma_db/
#   3. Logs every file that was updated

set -euo pipefail

LORE_DIR="lore"
CONFIG_DIR="backend/config"
CHROMA_DIR="backend/chroma_db"

CHROMA_INVALIDATED=false
FILES_UPDATED=0

# Files to sync: source relative to LORE_DIR → dest relative to CONFIG_DIR
# Format: "source_file:dest_file"
SYNC_MAP=(
    "world.md:world.md"
    "bestiary.md:bestiary.md"
    "bestiary_t1.md:bestiary_t1.md"
    "bestiary_t2.md:bestiary_t2.md"
    "bestiary_t3.md:bestiary_t3.md"
    "bestiary_t4.md:bestiary_t4.md"
    "bestiary_t5.md:bestiary_t5.md"
    "AUDIO_PROMPTS.md:AUDIO_PROMPTS.md"
)

# Files that trigger ChromaDB invalidation when changed
CHROMA_SENSITIVE=("world.md" "bestiary.md" "bestiary_t1.md" "bestiary_t2.md" "bestiary_t3.md" "bestiary_t4.md" "bestiary_t5.md")

echo ""
echo "  Aerus — Lore Sync"
echo "  ─────────────────────────────────────"

for entry in "${SYNC_MAP[@]}"; do
    src_file="${entry%%:*}"
    dst_file="${entry##*:}"
    src_path="${LORE_DIR}/${src_file}"
    dst_path="${CONFIG_DIR}/${dst_file}"

    if [ ! -f "$src_path" ]; then
        echo "  [SKIP]    ${src_file}  (not found in lore/)"
        continue
    fi

    # Check if files differ (or dest doesn't exist)
    if [ ! -f "$dst_path" ] || ! diff -q "$src_path" "$dst_path" > /dev/null 2>&1; then
        cp "$src_path" "$dst_path"
        echo "  [UPDATED] ${src_file}"
        FILES_UPDATED=$((FILES_UPDATED + 1))

        # Check if this file triggers ChromaDB invalidation
        for sensitive in "${CHROMA_SENSITIVE[@]}"; do
            if [ "$src_file" = "$sensitive" ]; then
                CHROMA_INVALIDATED=true
                break
            fi
        done
    else
        echo "  [OK]      ${src_file}  (no changes)"
    fi
done

echo "  ─────────────────────────────────────"

if [ "$FILES_UPDATED" -eq 0 ]; then
    echo "  All files are already in sync."
else
    echo "  ${FILES_UPDATED} file(s) updated."
fi

# Invalidate ChromaDB if needed
if [ "$CHROMA_INVALIDATED" = true ]; then
    if [ -d "$CHROMA_DIR" ]; then
        rm -rf "$CHROMA_DIR"
        echo "  [INVALIDATED] ${CHROMA_DIR}/ removed — re-ingestion will happen on next server startup."
    else
        echo "  [INFO] ${CHROMA_DIR}/ not present — nothing to invalidate."
    fi
fi

echo ""
