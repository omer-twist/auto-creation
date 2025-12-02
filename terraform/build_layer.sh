#!/bin/bash
# Build Lambda layer with dependencies
# Run this before terraform apply

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Building Lambda layer..."

# Clean up
rm -rf python layer.zip

# Create directory structure
mkdir -p python

# Install dependencies
pip install -r ../requirements.txt -t python/ --quiet

# Create zip
zip -r layer.zip python -q

# Clean up
rm -rf python

echo "Layer built: $SCRIPT_DIR/layer.zip"
