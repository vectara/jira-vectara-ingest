#!/bin/bash
# Setup script for jira-vectara-ingest (macOS/Linux)

set -e

echo "🚀 Setting up jira-vectara-ingest..."
echo ""

# Check Python version
echo "✓ Checking Python version..."
python3 --version || { echo "❌ Python 3 not found. Please install Python 3.8+"; exit 1; }

# Create virtual environment
echo "✓ Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "✓ Installing dependencies (this takes ~5 seconds)..."
pip install --upgrade pip
pip install -r requirements.txt

# Copy config if needed
if [ ! -f config.yaml ]; then
    echo "✓ Creating config.yaml from sample..."
    cp config.sample.yaml config.yaml
    echo ""
    echo "⚠️  Please edit config.yaml with your credentials:"
    echo "   - vectara.api_key"
    echo "   - vectara.corpus_key"
    echo "   - jira.base_url"
    echo "   - jira.username"
    echo "   - jira.api_token"
    echo "   - jira.jql"
else
    echo "✓ config.yaml already exists"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit config.yaml with your credentials"
echo "  2. Run: source venv/bin/activate"
echo "  3. Run: python jira_ingest.py --config config.yaml"
echo ""
