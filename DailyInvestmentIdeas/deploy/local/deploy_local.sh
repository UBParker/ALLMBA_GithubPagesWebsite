#!/bin/bash
# Local deployment script for GitHub Pages integration

# Ensure we're in the project root directory
cd "$(dirname "$0")/../.." || exit 1

echo "=== ALLMBA Daily Investment Ideas - Local Deployment ==="
echo "This script runs the data collection and analysis locally,"
echo "and prepares files for manual upload to GitHub Pages."
echo ""

# Step 1: Create directories
echo "Setting up directories..."
mkdir -p data/raw
mkdir -p data/processed
mkdir -p deploy/output/api/ideas
mkdir -p deploy/output/api/dates
mkdir -p deploy/output/api/types
mkdir -p deploy/output/js
mkdir -p deploy/output/css

# Step 2: Run data collection (using test mode with real APIs)
echo "Running data collection with Twelve Data API in test mode..."
python src/collect_data.py --test
if [ $? -ne 0 ]; then
    echo "Error: Data collection failed!"
    exit 1
fi
echo "Data collection completed with mock data."
echo "Note: For live API data, register for a free API key at:"
echo "- Twelve Data: https://twelvedata.com/pricing" 
echo "- FRED API: https://fred.stlouisfed.org/docs/api/api_key.html"
echo "- News API: https://newsapi.org/"
echo "- Finnhub: https://finnhub.io/"

# Step 3: Run data analysis
echo "Running data analysis..."
python src/analyze_data.py
if [ $? -ne 0 ]; then
    echo "Error: Data analysis failed!"
    exit 1
fi
echo "Data analysis completed."

# Step 4: Create static API files
echo "Creating static API files..."

# Copy the latest ideas file
latest_file=$(ls -t data/processed/investment_ideas_*.json | head -1)
if [ -z "$latest_file" ]; then
    echo "Error: No processed data files found!"
    exit 1
fi

cp "$latest_file" deploy/output/api/ideas/index.json
basename=$(basename "$latest_file")
cp "$latest_file" "deploy/output/api/ideas/$basename"

# Generate dates API response
ls data/processed/investment_ideas_*.json | sed 's/.*investment_ideas_\(.*\)\.json/\1/' | sort -r > deploy/output/api/dates/index.json

# Generate types API response
python -c "
import json
with open('$latest_file', 'r') as f:
    data = json.load(f)
    types = sorted(list(set(idea.get('type') for idea in data.get('ideas', []) if 'type' in idea)))
    with open('deploy/output/api/types/index.json', 'w') as out:
        json.dump(types, out, indent=2)
"

# Step 5: Prepare GitHub Pages integration files
echo "Preparing GitHub Pages integration files..."

# Copy integration files
cp integration/investment_ideas_template.html deploy/output/index.html
cp deploy/github_pages/github_pages_static_integration.js deploy/output/js/github_pages_integration.js

# Extract and copy CSS
python -c "
import re
with open('integration/investment_ideas_template.html', 'r') as f:
    content = f.read()
    css_match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
    if css_match:
        css = css_match.group(1)
        with open('deploy/output/css/investment_ideas.css', 'w') as out:
            out.write(css)
"

# Update HTML to reference external CSS and JS
sed -i.bak 's|<style>.*</style>|<link rel="stylesheet" href="css/investment_ideas.css">|' deploy/output/index.html
rm deploy/output/index.html.bak

# Step 6: Create ideas JSON files for each idea
echo "Creating individual idea JSON files..."
python -c "
import json
with open('$latest_file', 'r') as f:
    data = json.load(f)
    date = data.get('date', 'unknown')
    for i, idea in enumerate(data.get('ideas', [])):
        idea_id = f'{date}-{i+1}'
        idea['id'] = idea_id
        idea['date'] = date
        with open(f'deploy/output/api/ideas/{idea_id}.json', 'w') as idea_file:
            json.dump(idea, idea_file, indent=2)
"

echo "Deployment completed successfully!"
echo ""
echo "Your static files are ready in the deploy/output directory."
echo "To integrate with GitHub Pages:"
echo ""
echo "1. Copy the contents of deploy/output to your GitHub Pages repository:"
echo "   cp -r deploy/output/* /path/to/your/github/pages/repo/"
echo ""
echo "2. Add the following HTML to include the investment ideas in your page:"
echo "   <div id=\"investment-ideas-container\"></div>"
echo "   <script src=\"js/github_pages_integration.js\"></script>"
echo ""
echo "3. Commit and push the changes to GitHub:"
echo "   cd /path/to/your/github/pages/repo"
echo "   git add ."
echo "   git commit -m \"Add ALLMBA Daily Investment Ideas\""
echo "   git push"
echo ""