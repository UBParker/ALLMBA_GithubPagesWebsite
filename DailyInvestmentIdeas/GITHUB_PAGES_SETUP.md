# Setting Up ALLMBA Daily Investment Ideas on GitHub Pages

## Step 1: Install Required Dependencies

Before running the system, install all required Python packages:

```bash
pip install requests pandas numpy scipy scikit-learn textblob nltk fastapi uvicorn pydantic python-dotenv newsapi-python pytrends finnhub-python
```

## Step 2: Run the Data Collection and Analysis Pipeline

The system consists of two main components:

1. **Data Collection** (`collect_data.py`): Gathers financial data from various APIs
2. **Data Analysis** (`analyze_data.py`): Processes the data and generates investment ideas

Run the following commands:

```bash
# First, run the data collection
python src/collect_data.py

# Then, run the data analysis
python src/analyze_data.py
```

This will:
- Collect financial data from Alpha Vantage, FRED, News API, and Finnhub
- Analyze the data to identify patterns and opportunities
- Generate investment ideas based on the analysis
- Save the ideas as JSON files in the `data/processed` directory

## Step 3: Set Up GitHub Pages Integration

### Option A: Using the FastAPI Backend (Production Setup)

1. Deploy the API to a cloud service (Google Cloud Run, AWS, etc.)
   ```bash
   # Example for Google Cloud Run
   gcloud run deploy investment-ideas-api --source . --region us-central1
   ```

2. Update the API URL in the JavaScript integration file
   ```javascript
   // In integration/github_pages_integration.js
   const API_BASE_URL = 'https://your-api-url.a.run.app/api';
   ```

3. Copy the HTML and JavaScript files to your GitHub Pages repository
   ```bash
   cp integration/investment_ideas_template.html /path/to/your/github/pages/repo/
   cp integration/github_pages_integration.js /path/to/your/github/pages/repo/js/
   ```

### Option B: Static Files Approach (Simpler Setup)

1. Create directories for the static API
   ```bash
   mkdir -p /path/to/your/github/pages/repo/api/ideas
   mkdir -p /path/to/your/github/pages/repo/api/dates
   mkdir -p /path/to/your/github/pages/repo/api/types
   ```

2. Copy the processed data to the API directory
   ```bash
   # Copy the latest ideas file
   cp data/processed/investment_ideas_*.json /path/to/your/github/pages/repo/api/ideas/

   # Create index.json for dates endpoint
   ls data/processed/investment_ideas_*.json | sed 's/.*investment_ideas_\(.*\)\.json/\1/' > /path/to/your/github/pages/repo/api/dates/index.json
   
   # Create index.json for types endpoint (requires a bit of Python)
   python -c "
   import json
   with open('data/processed/$(ls -t data/processed/investment_ideas_*.json | head -1)', 'r') as f:
       data = json.load(f)
       types = sorted(list(set(idea.get('type') for idea in data.get('ideas', []) if 'type' in idea)))
       with open('/path/to/your/github/pages/repo/api/types/index.json', 'w') as out:
           json.dump(types, out, indent=2)
   "
   ```

3. Use the static integration JavaScript file
   ```bash
   cp deploy/github_pages/github_pages_static_integration.js /path/to/your/github/pages/repo/js/github_pages_integration.js
   ```

4. Add the HTML template to your page
   ```bash
   cp integration/investment_ideas_template.html /path/to/your/github/pages/repo/
   ```

## Step 4: Add to Your GitHub Pages Website

1. Include the HTML template in your webpage (investment.html, index.html, etc.)

2. Link the JavaScript file in your HTML
   ```html
   <script src="js/github_pages_integration.js"></script>
   ```

3. Commit and push the changes to your GitHub repository
   ```bash
   cd /path/to/your/github/pages/repo
   git add .
   git commit -m "Add ALLMBA Daily Investment Ideas"
   git push
   ```

## Step 5: Automation (Optional)

For daily updates, consider setting up a GitHub Action in your repository:

1. Create a workflow file `.github/workflows/update-investment-ideas.yml`
   ```yaml
   name: Update Investment Ideas

   on:
     schedule:
       - cron: '0 5 * * *'  # Run daily at 5 AM UTC
     workflow_dispatch:  # Allow manual trigger

   jobs:
     update:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v2
         - name: Set up Python
           uses: actions/setup-python@v2
           with:
             python-version: '3.9'
         - name: Install dependencies
           run: |
             python -m pip install --upgrade pip
             pip install requests pandas numpy scipy scikit-learn textblob nltk fastapi uvicorn pydantic python-dotenv newsapi-python pytrends finnhub-python
         - name: Download NLTK data
           run: |
             python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
         - name: Run data collection
           run: python src/collect_data.py
         - name: Run data analysis
           run: python src/analyze_data.py
         - name: Update static API files
           run: |
             mkdir -p api/ideas api/dates api/types
             cp data/processed/investment_ideas_*.json api/ideas/
             ls data/processed/investment_ideas_*.json | sed 's/.*investment_ideas_\(.*\)\.json/\1/' > api/dates/index.json
             # Generate types index
             python deploy/github_pages/generate_types_index.py
         - name: Commit and push changes
           run: |
             git config --local user.email "action@github.com"
             git config --local user.name "GitHub Action"
             git add api/
             git commit -m "Update investment ideas for $(date +'%Y-%m-%d')" || echo "No changes to commit"
             git push
   ```

## Troubleshooting

- **Missing data**: Ensure all API keys are correctly set in `collect_data.py`
- **JavaScript errors**: Check the browser console for errors
- **API rate limits**: If you hit API rate limits, consider reducing the number of tickers or adding delays between requests
- **Missing Python modules**: Install any missing dependencies with pip

## Customization

You can customize the system by:

1. Editing the list of stocks, indices, and other assets in `collect_data.py`
2. Modifying the analysis criteria in `analyze_data.py`
3. Customizing the HTML/CSS for the investment ideas display
4. Adding additional features to the JavaScript integration