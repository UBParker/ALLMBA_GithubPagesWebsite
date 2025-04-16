#!/bin/bash
# GitHub Pages Deployment Script for ALLMBA Daily Investment Ideas

# Ensure we're in the project root directory
cd "$(dirname "$0")/../.." || exit 1

echo "=== ALLMBA Daily Investment Ideas - GitHub Pages Deployment ==="
echo "This script runs the data collection, analysis, and deploys to GitHub Pages."
echo ""

# 1. Set up directories
echo "Setting up directories..."
mkdir -p data/raw
mkdir -p data/processed

# 2. Run data collection
echo "Running data collection..."
python src/collect_data.py
if [ $? -ne 0 ]; then
    echo "Error: Data collection failed!"
    exit 1
fi

# 3. Run data analysis
echo "Running data analysis..."
python src/analyze_data.py
if [ $? -ne 0 ]; then
    echo "Error: Data analysis failed!"
    exit 1
fi

# 4. Check if we're deploying to GitHub Pages
if [ "$1" != "--deploy" ]; then
    echo "Data collection and analysis completed successfully."
    echo "Run with --deploy to continue with GitHub Pages deployment."
    exit 0
fi

# 5. Copy integration files to GitHub Pages directory
echo "Copying integration files to GitHub Pages directory..."
cp -r integration/* ../

# 6. Update API URL in JavaScript file
echo "Updating API URL in JavaScript integration file..."
# This is a local setup - you'd replace this with your actual API URL when deploying to production
sed -i.bak 's|const API_BASE_URL = .*|const API_BASE_URL = "https://YOUR_CLOUD_RUN_URL.a.run.app/api"; // Update with your actual API URL|' ../github_pages_integration.js
rm -f ../github_pages_integration.js.bak

# 7. Copy generated data to a location accessible by GitHub Pages
echo "Copying generated data..."
mkdir -p ../data
cp -r data/processed/* ../data/

# 8. Create a static JSON API for GitHub Pages
echo "Creating static JSON API files..."
mkdir -p ../api/ideas
mkdir -p ../api/dates
mkdir -p ../api/types

# Generate dates API response
ls data/processed/investment_ideas_*.json | sed 's/.*investment_ideas_\(.*\)\.json/\1/' | sort -r > ../api/dates/index.json

# Generate types API response
LATEST_FILE=$(ls -t data/processed/investment_ideas_*.json | head -1)
if [ -n "$LATEST_FILE" ]; then
    python -c "
import json
with open('$LATEST_FILE', 'r') as f:
    data = json.load(f)
    types = sorted(list(set(idea.get('type') for idea in data.get('ideas', []) if 'type' in idea)))
    print(json.dumps(types, indent=2))
" > ../api/types/index.json
fi

# Copy latest ideas file to API directory
if [ -n "$LATEST_FILE" ]; then
    cp "$LATEST_FILE" ../api/ideas/index.json
    
    # Create individual idea files
    python -c "
import json
import os
with open('$LATEST_FILE', 'r') as f:
    data = json.load(f)
    date = data.get('date', 'unknown')
    for i, idea in enumerate(data.get('ideas', [])):
        idea_id = f'{date}-{i+1}'
        idea['id'] = idea_id
        idea['date'] = date
        with open(f'../api/ideas/{idea_id}.json', 'w') as idea_file:
            json.dump(idea, idea_file, indent=2)
"
fi

echo "GitHub Pages deployment completed successfully!"
echo "Your investment ideas are now available in the GitHub Pages directory."
echo ""
echo "IMPORTANT: Remember to update the API_BASE_URL in github_pages_integration.js"
echo "with your actual API URL when deploying to production."
echo ""
echo "To test locally, you can run the FastAPI server with:"
echo "python src/api.py"
echo ""