# Setting Up ALLMBA Daily Investment Ideas on GitHub Pages - Local Deployment

Since we encountered permission issues with Google Cloud deployment, this guide shows how to use a local deployment approach to add the Daily Investment Ideas to your GitHub Pages site.

## Step 1: Install Required Python Packages

First, install all required dependencies:

```bash
pip install requests pandas numpy scipy scikit-learn textblob nltk fastapi uvicorn pydantic python-dotenv newsapi-python pytrends finnhub-python
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
```

## Step 2: Run the Local Deployment Script

The local deployment script will:
1. Run data collection to gather financial data
2. Run data analysis to generate investment ideas
3. Create static API files that can be served by GitHub Pages
4. Prepare the HTML, CSS, and JavaScript integration files

```bash
cd /Users/ashhome/Downloads/ALLMBAGithubPagesWebsite/DailyInvestmentIdeas
./deploy/local/deploy_local.sh
```

This will create a `deploy/output` directory containing all necessary files.

## Step 3: Copy Files to Your GitHub Pages Repository

Copy all generated files to your GitHub Pages repository:

```bash
# Replace with your actual GitHub Pages repository path
cp -r deploy/output/* /path/to/your/github/pages/repo/
```

## Step 4: Add the Investment Ideas to Your Website

You have two options:

### Option 1: Use the standalone page

The `index.html` file in the output directory is a standalone page that displays the investment ideas. You can rename it (e.g., to `investment.html`) and link to it from your main page.

### Option 2: Integrate into an existing page

To add the investment ideas section to an existing page:

1. Add the CSS link to your HTML `<head>` section:
   ```html
   <link rel="stylesheet" href="css/investment_ideas.css">
   ```

2. Add this HTML where you want the investment ideas to appear:
   ```html
   <section class="ideas-section">
     <div class="container">
       <div class="ideas-header">
         <div>
           <h2>Daily Investment Ideas</h2>
           <p>AI-generated investment opportunities for <span id="ideas-date-display">today</span></p>
         </div>
         <div class="ideas-filters">
           <select id="date-selector" aria-label="Select date"></select>
           <select id="type-selector" aria-label="Filter by type"></select>
         </div>
       </div>
       
       <div id="ideas-error"></div>
       <div id="ideas-loading">Loading investment ideas...</div>
       
       <div id="investment-ideas-container" class="ideas-container"></div>
     </div>
   </section>

   <!-- Template for investment idea cards -->
   <template id="idea-template">
     <div class="idea-card">
       <div class="idea-header">
         <div class="idea-title"></div>
         <div class="idea-meta">
           <div class="idea-type"></div>
           <div class="idea-asset"></div>
         </div>
       </div>
       <div class="idea-content">
         <p class="idea-rationale"></p>
         <div class="idea-details">
           <div>
             <span>Risk:</span>
             <span class="idea-risk"></span>
           </div>
           <div>
             <span>Horizon:</span>
             <span class="idea-horizon"></span>
           </div>
         </div>
         <div class="idea-metrics"></div>
       </div>
     </div>
   </template>
   ```

3. Add the JavaScript at the end of your HTML body:
   ```html
   <script src="js/github_pages_integration.js"></script>
   ```

## Step 5: Commit and Push to GitHub

Commit all the changes to your GitHub repository:

```bash
cd /path/to/your/github/pages/repo
git add .
git commit -m "Add ALLMBA Daily Investment Ideas"
git push
```

## Step 6: Verify the Integration

Once your GitHub Pages site is deployed (usually within a few minutes after pushing), visit your site and verify that the investment ideas are displayed correctly.

## Updating the Data

To update the investment ideas data, simply run the local deployment script again and copy the updated files to your GitHub Pages repository.

You can automate this process with a cron job or scheduled task on your local machine or a CI/CD pipeline like GitHub Actions.