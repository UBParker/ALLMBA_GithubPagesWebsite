/**
 * ALLMBA Daily Investment Ideas - Static GitHub Pages Integration
 * 
 * This script fetches and displays investment ideas from static JSON files
 * stored in your GitHub Pages repository.
 */

// Configuration
// Dynamic API URL detection (works both locally and on GitHub Pages)
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? '/api' // Local development
  : '/ALLMBA_GithubPagesWebsite/api'; // GitHub Pages

// Elements
let ideaContainer;
let ideaTemplate;
let loadingIndicator;
let errorContainer;
let dateSelectorEl;
let typeSelectorEl;

// Data
let currentDate = null;
let availableDates = [];
let ideaTypes = [];

/**
 * Initialize the investment ideas display
 */
function initInvestmentIdeas() {
  // Get DOM elements
  ideaContainer = document.getElementById('investment-ideas-container');
  ideaTemplate = document.getElementById('idea-template');
  loadingIndicator = document.getElementById('ideas-loading');
  errorContainer = document.getElementById('ideas-error');
  dateSelectorEl = document.getElementById('date-selector');
  typeSelectorEl = document.getElementById('type-selector');
  
  if (!ideaContainer || !ideaTemplate) {
    console.error('Required DOM elements not found');
    return;
  }
  
  // Get available dates
  fetchAvailableDates().then(() => {
    // Initialize date selector
    if (dateSelectorEl && availableDates.length > 0) {
      populateDateSelector();
      
      dateSelectorEl.addEventListener('change', (e) => {
        currentDate = e.target.value;
        fetchAndDisplayIdeas();
      });
    }
    
    // Get available idea types
    fetchIdeaTypes().then(() => {
      // Initialize type selector
      if (typeSelectorEl && ideaTypes.length > 0) {
        populateTypeSelector();
        
        typeSelectorEl.addEventListener('change', (e) => {
          fetchAndDisplayIdeas();
        });
      }
      
      // Load initial ideas
      fetchAndDisplayIdeas();
    });
  });
}

/**
 * Fetch available dates from static JSON file
 */
async function fetchAvailableDates() {
  try {
    showLoading(true);
    const response = await fetch(`${API_BASE_URL}/dates/index.json`);
    
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }
    
    availableDates = await response.json();
    
    if (availableDates.length > 0) {
      currentDate = availableDates[0]; // Most recent date
    }
  } catch (error) {
    console.error('Error fetching available dates:', error);
    showError('Unable to fetch available dates. Please try again later.');
  } finally {
    showLoading(false);
  }
}

/**
 * Fetch available idea types from static JSON file
 */
async function fetchIdeaTypes() {
  try {
    const response = await fetch(`${API_BASE_URL}/types/index.json`);
    
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }
    
    ideaTypes = await response.json();
  } catch (error) {
    console.error('Error fetching idea types:', error);
  }
}

/**
 * Populate date selector dropdown
 */
function populateDateSelector() {
  dateSelectorEl.innerHTML = '';
  
  availableDates.forEach(date => {
    const option = document.createElement('option');
    option.value = date;
    
    // Format date for display (YYYY-MM-DD to Month DD, YYYY)
    const dateObj = new Date(date);
    const formattedDate = dateObj.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    });
    
    option.textContent = formattedDate;
    dateSelectorEl.appendChild(option);
  });
}

/**
 * Populate type selector dropdown
 */
function populateTypeSelector() {
  typeSelectorEl.innerHTML = '';
  
  // Add "All Types" option
  const allOption = document.createElement('option');
  allOption.value = '';
  allOption.textContent = 'All Types';
  typeSelectorEl.appendChild(allOption);
  
  ideaTypes.forEach(type => {
    const option = document.createElement('option');
    option.value = type;
    option.textContent = type;
    typeSelectorEl.appendChild(option);
  });
}

/**
 * Fetch and display investment ideas
 */
async function fetchAndDisplayIdeas() {
  try {
    showLoading(true);
    clearIdeas();
    
    // Default to getting all ideas from index.json
    let url = `${API_BASE_URL}/ideas/index.json`;
    
    // If a specific date is selected, use that date's file
    if (currentDate) {
      url = `${API_BASE_URL}/ideas/investment_ideas_${currentDate}.json`;
    }
    
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }
    
    const data = await response.json();
    let ideas = data.ideas || [];
    
    // Apply type filter if selected
    if (typeSelectorEl && typeSelectorEl.value) {
      ideas = ideas.filter(idea => idea.type === typeSelectorEl.value);
    }
    
    if (ideas.length === 0) {
      showError('No investment ideas found for the selected criteria.');
      return;
    }
    
    // Update the data source disclaimer based on data sources used
    updateDataSourceDisclaimer(data);
    
    // Display ideas
    displayIdeas(ideas);
    
    // Update date display if available
    const dateDisplay = document.getElementById('ideas-date-display');
    if (dateDisplay) {
      const dateObj = new Date(data.date);
      const formattedDate = dateObj.toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric'
      });
      dateDisplay.textContent = formattedDate;
    }
  } catch (error) {
    console.error('Error fetching investment ideas:', error);
    showError('Unable to fetch investment ideas. Please try again later.');
  } finally {
    showLoading(false);
  }
}

/**
 * Update the data source disclaimer based on the data actually used for this report
 */
function updateDataSourceDisclaimer(data) {
  const disclaimerContent = document.getElementById('disclaimer-content');
  if (!disclaimerContent) return;
  
  // Extract data sources from ideas
  const markets = new Set();
  const sectors = new Set();
  const assetTypes = new Set();
  const dataTypes = new Set();
  
  // Extract markets, sectors, and types from ideas
  if (data.ideas && data.ideas.length > 0) {
    data.ideas.forEach(idea => {
      if (idea.market) markets.add(idea.market);
      if (idea.sector) sectors.add(idea.sector);
      if (idea.type) assetTypes.add(idea.type);
      
      // Check metrics for data types
      if (idea.metrics) {
        if (idea.metrics.rsi !== undefined) dataTypes.add('Technical Indicators');
        if (idea.metrics.finnhub_score !== undefined) dataTypes.add('Alternative Data');
        if (idea.metrics.net_buys !== undefined) dataTypes.add('Insider Trading');
        if (idea.metrics.sentiment !== undefined) dataTypes.add('News Sentiment');
        if (idea.metrics.yield_change !== undefined) dataTypes.add('Bond Yields');
      }
    });
  }
  
  // Extract data sources from meta information if available
  const dataSources = data.data_sources || {
    "Stock Data": "Alpha Vantage, Twelve Data, and Finnhub APIs",
    "Market Indices": data.indices_used ? data.indices_used.join(", ") : "S&P 500, NASDAQ, FTSE 100",
    "Economic Data": "FRED (Federal Reserve Economic Data)",
    "News": "News API",
    "Insider Trading": "Finnhub API"
  };
  
  // Generate dynamic disclaimer content
  let html = `
    <h4>Data Source Information - ${data.date}</h4>
    <p>These investment ideas were generated using data from the following sources:</p>
    <ul>
  `;
  
  // Add data sources
  for (const [sourceType, sourceDesc] of Object.entries(dataSources)) {
    html += `<li><strong>${sourceType}:</strong> ${sourceDesc}</li>`;
  }
  
  html += `</ul>
    <p><strong>Markets analyzed:</strong> ${Array.from(markets).join(', ') || "Various global markets"}</p>
    <p><strong>Sectors covered:</strong> ${Array.from(sectors).join(', ') || "Various sectors"}</p>
    <p><strong>Data types used:</strong> ${Array.from(dataTypes).join(', ') || "Market prices, performance metrics"}</p>
    <p><strong>Investment idea types:</strong> ${Array.from(assetTypes).join(', ') || "Various types"}</p>
    <p><strong>Note:</strong> Some data sources may return partial data due to API rate limits or connectivity issues. In these cases, the system may use simulated data for demonstration purposes.</p>
    <p>The investment ideas shown are generated for educational purposes only. Always consult with a financial advisor before making investment decisions.</p>
  `;
  
  disclaimerContent.innerHTML = html;
}

/**
 * Display investment ideas in the container, grouped by market
 */
function displayIdeas(ideas) {
  if (!ideas || ideas.length === 0) return;
  
  // Group ideas by market
  const marketGroups = {};
  
  // Create an "Other" group for ideas without a market
  marketGroups["Other"] = [];
  
  // Group ideas by market
  ideas.forEach(idea => {
    const market = idea.market || 'Other';
    if (!marketGroups[market]) {
      marketGroups[market] = [];
    }
    marketGroups[market].push(idea);
  });
  
  // For each market group, create a section
  for (const [market, marketIdeas] of Object.entries(marketGroups)) {
    // Skip empty markets
    if (marketIdeas.length === 0) continue;
    
    // Create market header
    const marketHeader = document.createElement('div');
    marketHeader.className = 'market-header';
    marketHeader.innerHTML = `<h3>${market}</h3>`;
    ideaContainer.appendChild(marketHeader);
    
    // Create ideas container for this market
    const marketIdeasContainer = document.createElement('div');
    marketIdeasContainer.className = 'market-ideas';
    
    // Add ideas to this market's container
    marketIdeas.forEach(idea => {
      const ideaElement = ideaTemplate.content.cloneNode(true);
      
      // Set idea content
      ideaElement.querySelector('.idea-title').textContent = idea.title;
      ideaElement.querySelector('.idea-type').textContent = idea.type;
      ideaElement.querySelector('.idea-asset').textContent = idea.asset;
      ideaElement.querySelector('.idea-rationale').textContent = idea.rationale;
      ideaElement.querySelector('.idea-risk').textContent = idea.risk_level;
      ideaElement.querySelector('.idea-horizon').textContent = idea.time_horizon;
      
      // Set risk level color
      const riskElement = ideaElement.querySelector('.idea-risk');
      if (riskElement) {
        riskElement.classList.add(
          idea.risk_level === 'Low' ? 'risk-low' :
          idea.risk_level === 'Medium' ? 'risk-medium' :
          idea.risk_level === 'Medium-High' ? 'risk-medium-high' :
          idea.risk_level === 'High' ? 'risk-high' :
          idea.risk_level === 'Very High' ? 'risk-very-high' :
          'risk-medium'
        );
      }
      
      // Add metrics if available
      const metricsContainer = ideaElement.querySelector('.idea-metrics');
      if (metricsContainer && idea.metrics) {
        let metricsHtml = '';
        
        if (idea.metrics.return !== undefined) {
          metricsHtml += `<div><span>Return:</span> ${idea.metrics.return.toFixed(2)}%</div>`;
        }
        
        if (idea.metrics.volatility !== undefined) {
          metricsHtml += `<div><span>Volatility:</span> ${idea.metrics.volatility.toFixed(2)}%</div>`;
        }
        
        if (idea.metrics.rsi !== undefined) {
          metricsHtml += `<div><span>RSI:</span> ${idea.metrics.rsi.toFixed(1)}</div>`;
        }
        
        if (idea.metrics.stocks_count !== undefined) {
          metricsHtml += `<div><span>Stocks:</span> ${idea.metrics.stocks_count}</div>`;
        }
        
        if (idea.metrics.avg_return !== undefined) {
          metricsHtml += `<div><span>Avg Return:</span> ${idea.metrics.avg_return.toFixed(2)}%</div>`;
        }
        
        if (idea.metrics.sentiment !== undefined) {
          const sentimentValue = (idea.metrics.sentiment * 100).toFixed(0);
          metricsHtml += `<div><span>Sentiment:</span> ${sentimentValue}%</div>`;
        }
        
        if (idea.metrics.yield_change !== undefined) {
          metricsHtml += `<div><span>Yield Change:</span> ${idea.metrics.yield_change.toFixed(2)}%</div>`;
        }
        
        if (idea.metrics.price !== undefined) {
          metricsHtml += `<div><span>Price:</span> $${idea.metrics.price.toFixed(2)}</div>`;
        }
        
        // Additional alternative data metrics
        if (idea.metrics.finnhub_score !== undefined) {
          metricsHtml += `<div><span>Alt Data Score:</span> ${idea.metrics.finnhub_score.toFixed(1)}</div>`;
        }
        
        if (idea.metrics.net_buys !== undefined) {
          metricsHtml += `<div><span>Net Insider Buys:</span> ${idea.metrics.net_buys}</div>`;
        }
        
        metricsContainer.innerHTML = metricsHtml;
      }
      
      // Append to market container
      marketIdeasContainer.appendChild(ideaElement);
    });
    
    // Append the market ideas container to the main container
    ideaContainer.appendChild(marketIdeasContainer);
  }
}

/**
 * Clear the ideas container
 */
function clearIdeas() {
  if (ideaContainer) {
    ideaContainer.innerHTML = '';
  }
  
  if (errorContainer) {
    errorContainer.style.display = 'none';
  }
}

/**
 * Show/hide the loading indicator
 */
function showLoading(isLoading) {
  if (loadingIndicator) {
    loadingIndicator.style.display = isLoading ? 'block' : 'none';
  }
}

/**
 * Show an error message
 */
function showError(message) {
  if (errorContainer) {
    errorContainer.textContent = message;
    errorContainer.style.display = 'block';
  }
}

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', initInvestmentIdeas);