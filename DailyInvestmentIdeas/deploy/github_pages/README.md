# Deploying ALLMBA Daily Investment Ideas to GitHub Pages

This guide explains how to run and deploy the ALLMBA Daily Investment Ideas system to GitHub Pages.

## Overview

The ALLMBA Daily Investment Ideas system collects financial data, analyzes it, and generates investment ideas. These ideas can be displayed on a GitHub Pages website.

There are two deployment options:

1. **Static Site Deployment**: Generate investment ideas locally and publish them as static JSON files
2. **API Deployment**: Deploy the FastAPI server to a cloud platform and connect your GitHub Pages site to it

This guide focuses on the first option, which is simpler and doesn't require running a separate API server.

## Prerequisites

- Python 3.8 or higher
- Git
- A GitHub Pages website
- API keys for:
  - Alpha Vantage (for stock and forex data)
  - FRED (for bond data)
  - News API (for news sentiment)
  - Finnhub (for additional stock data)

## Setup Steps

### 1. Install Required Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Edit the API keys in `src/collect_data.py` or set them as environment variables.

```python
# Set your API keys here
ALPHA_VANTAGE_API_KEY = "YOUR_ALPHA_VANTAGE_API_KEY"
FRED_API_KEY = "YOUR_FRED_API_KEY"
NEWS_API_KEY = "YOUR_NEWS_API_KEY"
FINNHUB_API_KEY = "YOUR_FINNHUB_API_KEY"
```

### 3. Run Data Collection and Analysis

The provided deployment script will run the data collection and analysis:

```bash
bash deploy/github_pages/deploy.sh
```

This will:
- Collect financial data using the APIs
- Analyze the data and generate investment ideas
- Save the ideas as JSON files in the `data/processed` directory

### 4. Deploy to GitHub Pages

To copy the necessary files to your GitHub Pages site:

```bash
bash deploy/github_pages/deploy.sh --deploy
```

This will:
- Copy the integration files to your GitHub Pages directory
- Create static JSON API files
- Set up everything needed for GitHub Pages integration

### 5. Update the HTML and JavaScript

In your GitHub Pages repository:

1. Add the investment ideas section to your webpage by copying the content from `integration/investment_ideas_template.html`

2. Update the API URL in `github_pages_integration.js`:

```javascript
// For static site deployment:
const API_BASE_URL = '/api'; // Relative path to the static JSON files

// OR for API deployment:
// const API_BASE_URL = 'https://YOUR_CLOUD_RUN_URL.a.run.app/api';
```

### 6. Commit and Push to GitHub

Commit all the changes and push to your GitHub repository:

```bash
cd /path/to/your/github/pages/repo
git add .
git commit -m "Add ALLMBA Daily Investment Ideas integration"
git push origin main
```

## Automatic Updates

To automatically update your investment ideas daily, you can set up a GitHub Action or other automation tool to run the deployment script and push the changes to your GitHub Pages repository.

## Testing Locally

To test the FastAPI server locally:

```bash
python src/api.py
```

Then access the API at `http://localhost:8080/api/ideas`.

## Troubleshooting

- **API Rate Limits**: If you hit rate limits, try reducing the number of tickers in `collect_data.py`
- **CORS Issues**: If you deploy the API separately, ensure CORS is properly configured in `api.py`
- **Integration Problems**: Check the browser console for errors and verify that the HTML IDs match between your webpage and the JavaScript file