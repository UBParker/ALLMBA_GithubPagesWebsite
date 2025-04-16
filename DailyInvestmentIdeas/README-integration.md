# Integrating ALLMBA Daily Investment Ideas with GitHub Pages

## Overview

This document explains how to integrate the ALLMBA Daily Investment Ideas API with your GitHub Pages website. The integration allows your website to display AI-generated investment ideas directly on your website.

## Prerequisites

1. The DailyInvestmentIdeas API is deployed on Google Cloud Platform (following the instructions in the main README.md)
2. You have access to edit your GitHub Pages website

## Integration Steps

### 1. Get the API URL

After deploying the API to Google Cloud Platform, you'll receive an API URL in the format:

```
https://investment-ideas-api-xxxxxxxxxxxx-uc.a.run.app
```

You'll need this URL for the integration.

### 2. Add the HTML Template to Your Website

Add the investment ideas section to your website by copying the content from `integration/investment_ideas_template.html` into your webpage where you want the ideas to appear.

The template includes:
- HTML structure for the investment ideas display
- CSS styles for the components
- A template for the idea cards

### 3. Configure the JavaScript Integration

Copy the JavaScript integration file from `integration/github_pages_integration.js` to your website's JavaScript directory.

Update the API base URL in the script:

```javascript
// Configuration
const API_BASE_URL = 'https://YOUR_CLOUD_RUN_URL.a.run.app/api'; // Replace with your actual API URL
```

### 4. Include the JavaScript in Your Webpage

Add the following script tag to your webpage that includes the investment ideas section:

```html
<script src="path/to/github_pages_integration.js"></script>
```

## Testing the Integration

To test the integration without deploying the API, we've included a sample implementation in the updated `investment.html` file. This version simulates API responses using embedded sample data.

## Production Deployment

For the production deployment, you should:

1. Deploy the API following the instructions in the main README.md
2. Replace the embedded sample implementation with the actual API integration
3. Verify that the API is accessible from your GitHub Pages domain (CORS is configured to allow all origins by default)

## Customization

You can customize the appearance of the investment ideas display by modifying the CSS in the `<style>` section of the template or in your website's CSS files.

The JavaScript integration also provides several customization points:

- Change the date format display
- Customize how risk levels are displayed
- Change the metrics formatting
- Add additional filters

## Troubleshooting

If the integration doesn't work as expected:

1. Check the browser's developer console for errors
2. Verify that the API URL is correct and accessible
3. Ensure CORS is properly configured if you're facing cross-origin issues
4. Check if the HTML IDs match between your webpage and the JavaScript file
