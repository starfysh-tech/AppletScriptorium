#!/usr/bin/env bash

REQUIREMENTS_FILE="Summarizer/requirements.txt"
REQUIRED_PACKAGES=()

while IFS= read -r line; do
    if [[ ! "$line" =~ ^# ]] && [[ -n "$line" ]] && [[ ! "$line" =~ ^pytest ]]; then
        pkg_name=$(echo "$line" | sed -E 's/[><=].*//' | xargs)
        if [ -n "$pkg_name" ]; then
            REQUIRED_PACKAGES+=("$pkg_name")
        fi
    fi
done < "$REQUIREMENTS_FILE"

echo "Parsed ${#REQUIRED_PACKAGES[@]} packages:"
for pkg in "${REQUIRED_PACKAGES[@]}"; do
    echo "  - $pkg"
done
