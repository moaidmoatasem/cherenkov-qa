#!/usr/bin/env bash
# Git configuration for stacked PRs support

# Enable rerere (reuse recorded resolution) for automatic merge conflict resolution during stack cascading
if ! git config --get rerere.enabled > /dev/null 2>&1; then
    git config --global rerere.enabled true
    echo "✅ Enabled rerere for cascading stack rebases"
fi

# Set default push strategy to simple to avoid extra prompts
git config --global push.default simple

# Ensure short hashes for readability in stack logs
git config --global log.abbrev true

# Enable directory permissions for safe stack operations
if ! git config --get core.protectNTFS > /dev/null 2>&1; then
    git config --global core.protectNTFS warn
fi

echo "✅ Git stack configuration complete"
