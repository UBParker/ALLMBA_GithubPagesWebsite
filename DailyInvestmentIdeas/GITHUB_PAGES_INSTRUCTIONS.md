# ALLMBA Daily Investment Ideas - GitHub Pages Integration

## Overview

This project is now set up to run on Google Cloud Platform with the `alan-banking-assistant` project ID. The Daily Investment Ideas API collects financial data, analyzes it, and generates investment ideas that are displayed on your GitHub Pages website.

## Integration Setup

### Step 1: Deploy the API to Google Cloud Run

1. Make sure you have the Google Cloud SDK installed and configured:
   ```bash
   gcloud auth login
   gcloud config set project alan-banking-assistant
   ```

2. Run the deployment script:
   ```bash
   cd /Users/ashhome/Downloads/ALLMBAGithubPagesWebsite/DailyInvestmentIdeas
   ./deploy/gcp/deploy_to_cloud_run.sh
   ```

3. The script will:
   - Build and deploy the API to Cloud Run
   - Set up a Cloud Storage bucket for data storage
   - Configure the API to use the bucket
   - Optionally set up a Cloud Scheduler job to update data daily

4. After deployment, you'll receive a service URL that looks like:
   ```
   https://investment-ideas-api-alan-banking-assistant.uc.a.run.app
   ```

### Step 2: Add the Investment Ideas Section to Your GitHub Pages Site

1. Copy the integration files to your GitHub Pages repository:
   ```bash
   cp integration/investment_ideas_template.html /path/to/your/github/pages/repo/investment.html
   cp integration/github_pages_integration.js /path/to/your/github/pages/repo/js/
   ```

2. The API URL is already configured in `github_pages_integration.js` to use your Cloud Run service.

3. If you need to modify the HTML template, edit the `investment_ideas_template.html` file.

### Step 3: Commit and Push Changes to GitHub

1. Commit the changes to your GitHub Pages repository:
   ```bash
   cd /path/to/your/github/pages/repo
   git add investment.html js/github_pages_integration.js
   git commit -m "Add ALLMBA Daily Investment Ideas integration"
   git push
   ```

2. Once pushed, your GitHub Pages site will be updated with the investment ideas integration.

## Data Updates

The system is configured to update the investment ideas data automatically:

1. **Daily Updates**: A Cloud Scheduler job is set up to trigger the API's update endpoint every day at 5:00 AM UTC.

2. **Manual Updates**: You can manually trigger an update by calling:
   ```
   https://investment-ideas-api-alan-banking-assistant.uc.a.run.app/api/tasks/update
   ```

## Customization

### Styling

You can customize the appearance of the investment ideas display by modifying the CSS in `investment.html`.

### Data Sources

The system uses these data sources:
- Alpha Vantage API for stock and forex data
- FRED API for bond data
- News API for news sentiment
- Finnhub API for additional stock data

If you want to modify the data sources or analysis logic, you can update the files in the `src` directory and redeploy.

## Troubleshooting

If the integration doesn't work as expected:

1. Check the browser's developer console for errors
2. Verify the API is accessible by visiting:
   ```
   https://investment-ideas-api-alan-banking-assistant.uc.a.run.app/api/ideas
   ```
3. If you see CORS errors, make sure the API's CORS settings are properly configured
4. Check Cloud Run logs for any API errors:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=investment-ideas-api" --limit 50
   ```

## Next Steps

1. Consider setting up a CI/CD pipeline to automatically deploy changes to the API
2. Add monitoring and alerts to ensure the data updates run successfully
3. Explore additional data sources or analysis techniques
4. Create different visualizations or filters for the investment ideas