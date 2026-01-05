#!/bin/bash
# Add document start marker to YAML files
for file in .github/dependabot.yml .github/workflows/*.yml mkdocs/mkdocs.yml .pre-commit-config.yaml config.yml; do
    if [ -f "$file" ]; then
        # Check if file doesn't start with ---
        if ! head -n 1 "$file" | grep -q "^---"; then
            # Add --- to the beginning
            echo -e "---\n$(cat $file)" > "$file"
        fi
    fi
done
