/**
 * ALLMBA Daily Investment Ideas - GitHub Pages Integration
 * 
 * This script fetches and displays investment ideas from the ALLMBA API
 * and integrates them into the GitHub Pages website.
 */

// Configuration
const API_BASE_URL = 'https://investment-ideas-api-alan-banking-assistant.uc.a.run.app/api'; // Cloud Run API URL

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
 * Fetch available dates from the API
 */
async function fetchAvailableDates() {
  try {
    showLoading(true);
    const response = await fetch(`${API_BASE_URL}/dates`);
    
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
 * Fetch available idea types from the API
 */
async function fetchIdeaTypes() {
  try {
    const response = await fetch(`${API_BASE_URL}/types`);
    
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
    
    // Build URL with query parameters
    let url = `${API_BASE_URL}/ideas`;
    const params = new URLSearchParams();
    
    if (currentDate) {
      params.append('date', currentDate);
    }
    
    if (typeSelectorEl && typeSelectorEl.value) {
      params.append('type', typeSelectorEl.value);
    }
    
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }
    
    const data = await response.json();
    
    if (data.count === 0) {
      showError('No investment ideas found for the selected criteria.');
      return;
    }
    
    // Display ideas
    displayIdeas(data.ideas);
    
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
 * Display investment ideas in the container
 */
function displayIdeas(ideas) {
  if (!ideas || ideas.length === 0) return;
  
  ideas.forEach(idea => {
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
      
      metricsContainer.innerHTML = metricsHtml;
    }
    
    // Append to container
    ideaContainer.appendChild(ideaElement);
  });
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
