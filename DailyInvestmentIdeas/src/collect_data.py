#!/usr/bin/env python3
"""
Data Collection Script

This script fetches data from various financial APIs and stores it locally
or in cloud storage for further processing.
"""

import os
import json
import datetime
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

# API clients
import requests
from newsapi import NewsApiClient
from pytrends.request import TrendReq
import finnhub
import pandas as pd
import numpy as np

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global debug mode flag
DEBUG_MODE = False

# API Keys
# Alpha Vantage free tier allows 5 API calls per minute and up to 500 calls per day
ALPHA_VANTAGE_API_KEY = "QVXM5SNGQ1K6WGPR"  # New key with higher limits
FRED_API_KEY = "fb670d7e87729f288ed7ffb40f986bb9"
NEWS_API_KEY = "b8851f0d4dc5462bbdddebc446bbfe89"
FINNHUB_API_KEY = "d000cm9r01qud9ql2jagd000cm9r01qud9ql2jb0"
TWELVE_DATA_API_KEY = "d1e3b5db8bfb42668c778ed9a7cd0b7b"  # Twelve Data API key

# EOD Historical Data API key
EODHD_API_KEY = "68003e8611ddd7.66051971"
EODHD_BASE_URL = "https://eodhd.com/api"

# Alpaca API Keys - These are free keys for paper trading account
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "AK29ALSFDKXMCNL88RJK")  # A new API key
ALPACA_SECRET_KEY = os.getenv("ALPACA_API_SECRET", "4sMx1qYDrlBZLP6DZJnPJ05m0hZZtfBSAjpBCnIc")  # A new secret key
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")  # Paper trading URL
ALPACA_DATA_URL = os.getenv("ALPACA_DATA_URL", "https://data.alpaca.markets")       # Market data URL

# Set up API clients
news_api = NewsApiClient(api_key=NEWS_API_KEY)
trend_api = TrendReq()
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

# Set up paths
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
TODAY = datetime.datetime.now().strftime("%Y-%m-%d")

# Define top stocks by market/index
markets = {
    "S&P500": {
        "index": "^GSPC",
        "stocks": [
            # Tech
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "ADBE", "CRM", "INTC",
            # Finance
            "JPM", "BAC", "GS", "MS", "WFC", "C", "BLK", "AXP", "V", "MA",
            # Healthcare
            "JNJ", "UNH", "PFE", "MRK", "ABBV", "LLY", "TMO", "ABT", "BMY", "AMGN"
        ]
    },
    "NASDAQ": {
        "index": "^IXIC",
        "stocks": [
            # Tech
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "ADBE", "PYPL", "INTC",
            # Biotech
            "GILD", "REGN", "BIIB", "VRTX", "ILMN", "MRNA", "BNTX", "ISRG", "ZTS", "IDXX"
        ]
    },
    "FTSE100": {
        "index": "^FTSE",
        "stocks": [
            # UK Top Companies
            "AZN.L", "SHEL.L", "HSBA.L", "GSK.L", "BP.L", "ULVR.L", "RIO.L", "LGEN.L", "BATS.L", "DGE.L",
            "VOD.L", "LLOY.L", "REL.L", "IMB.L", "NWG.L", "AAL.L", "PRU.L", "NG.L", "STAN.L", "BARC.L"
        ]
    }
}


def create_mock_index_info(ticker):
    """
    Create mock index information for indices that couldn't be fetched.
    
    Args:
        ticker (str): Index ticker symbol
        
    Returns:
        dict: Mock index information
    """
    shortname = f"Index {ticker}"
    longname = f"{ticker} Index"
    current_price = 1000.0
    
    if ticker == "^GSPC":
        shortname = "S&P 500"
        longname = "S&P 500 Index"
        current_price = 5021.84
    elif ticker == "^IXIC":
        shortname = "NASDAQ Composite"
        longname = "NASDAQ Composite Index"
        current_price = 15756.64
    elif ticker == "^DJI":
        shortname = "Dow Jones Industrial Average"
        longname = "Dow Jones Industrial Average Index"
        current_price = 38239.66
    elif ticker == "^FTSE":
        shortname = "FTSE 100"
        longname = "Financial Times Stock Exchange 100 Index"
        current_price = 8147.03
    elif ticker == "^N225":
        shortname = "Nikkei 225"
        longname = "Nikkei 225 Index"
        current_price = 38423.37
    elif ticker == "^HSI":
        shortname = "Hang Seng Index"
        longname = "Hang Seng Index"
        current_price = 17549.98
    elif ticker == "^TNX":
        shortname = "10-Year Treasury Yield"
        longname = "CBOE 10-Year Treasury Note Yield Index"
        current_price = 4.643
    elif ticker == "^TYX":
        shortname = "30-Year Treasury Yield"
        longname = "CBOE 30-Year Treasury Bond Yield Index"
        current_price = 4.758
    
    return {
        "symbol": ticker,
        "shortName": shortname,
        "longName": longname,
        "sector": "Index",
        "industry": "Market Index",
        "marketCap": 1000000000000,
        "currentPrice": current_price
    }

def fetch_eodhd_stock_data(tickers):
    """
    Fetch stock data for multiple tickers using EOD Historical Data API.
    
    Args:
        tickers (list): List of stock ticker symbols
        
    Returns:
        dict: Dictionary containing stock data
    """
    logger.info(f"Fetching EODHD stock data for {len(tickers)} tickers")
    stock_data = {}
    
    # Mapping for index symbols to add exchange suffix
    index_mapping = {
        "^GSPC": "SPY.US",    # S&P 500 (use SPY ETF as proxy)
        "^IXIC": "QQQ.US",    # NASDAQ Composite (use QQQ ETF as proxy)
        "^DJI": "DIA.US",     # Dow Jones Industrial Average (use DIA ETF as proxy)
        "^FTSE": "EZU.US",    # FTSE 100 (use European ETF as proxy)
        "^N225": "EWJ.US",    # Nikkei 225 (use Japan ETF as proxy)
        "^HSI": "FXI.US",     # Hang Seng Index (use China ETF as proxy)
        "^TNX": "TLT.US",     # 10-Year Treasury Yield (use TLT ETF as proxy)
        "^TYX": "TBT.US",     # 30-Year Treasury Yield (use TBT ETF as proxy)
    }
    
    for ticker in tickers:
        try:
            # Handle index symbols differently
            if ticker.startswith("^"):
                if ticker in index_mapping:
                    eodhd_ticker = index_mapping[ticker]
                else:
                    # Skip indices we don't have a mapping for
                    logger.warning(f"No EODHD mapping for index {ticker}. Using fallback.")
                    continue
            else:
                # For regular US stocks, add exchange suffix
                eodhd_ticker = f"{ticker}.US"
            
            # Historical data using the format from examples
            end_date = datetime.datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
            
            # Using the correct format for EOD API
            url = f"{EODHD_BASE_URL}/eod/{eodhd_ticker}"
            params = {
                "api_token": EODHD_API_KEY,
                "from": start_date,
                "to": end_date,
                "fmt": "json"
            }
            
            logger.info(f"Fetching EODHD historical data for {ticker} ({eodhd_ticker})")
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                try:
                    history_data = response.json()
                    if DEBUG_MODE:
                        logger.debug(f"DEBUG: EODHD historical data received for {ticker}: {type(history_data)} with {len(history_data) if isinstance(history_data, list) else 'unknown'} data points")
                    
                    # Validate the data
                    if isinstance(history_data, list) and len(history_data) > 0:
                        # Format history data
                        history = []
                        for item in history_data:
                            try:
                                history.append({
                                    "Date": item.get("date"),
                                    "Open": float(item.get("open", 0)),
                                    "High": float(item.get("high", 0)),
                                    "Low": float(item.get("low", 0)),
                                    "Close": float(item.get("close", 0)),
                                    "Volume": float(item.get("volume", 0)),
                                    "Dividends": float(item.get("dividend", 0)) if item.get("dividend") is not None else 0.0,
                                    "Stock Splits": 0.0  # Not directly provided by EODHD
                                })
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Error processing historical data point for {ticker}: {str(e)}")
                        
                        # Sort by date (oldest first)
                        history.sort(key=lambda x: x["Date"])
                        
                        if not history:
                            logger.warning(f"Failed to process any historical data points for {ticker}. Using fallback.")
                            continue
                        
                        # Skip fundamentals API since it's showing 403 errors (not part of subscription)
                        # Create basic info from historical data
                        company_info = {
                            "symbol": ticker,
                            "shortName": f"{ticker}",
                            "longName": f"{ticker} Stock",
                            "sector": "Unknown",
                            "industry": "Unknown",
                            "marketCap": 0,
                            "currentPrice": float(history[-1]["Close"]) if history else 0
                        }
                        
                        # Try to get some real-time data for additional info
                        try:
                            time.sleep(1)
                            url = f"{EODHD_BASE_URL}/real-time/{eodhd_ticker}"
                            params = {
                                "api_token": EODHD_API_KEY,
                                "fmt": "json"
                            }
                            
                            logger.info(f"Fetching EODHD real-time data for {ticker} ({eodhd_ticker})")
                            rt_response = requests.get(url, params=params, timeout=15)
                            
                            if rt_response.status_code == 200:
                                rt_data = rt_response.json()
                                if DEBUG_MODE:
                                    logger.debug(f"DEBUG: Real-time data for {ticker}: {rt_data}")
                                
                                # Update company info with any available real-time data
                                if rt_data:
                                    company_info["currentPrice"] = float(rt_data.get("close", company_info["currentPrice"]))
                                    company_info["change"] = float(rt_data.get("change", 0))
                                    company_info["changePercent"] = float(rt_data.get("change_p", 0))
                                    company_info["volume"] = float(rt_data.get("volume", 0))
                                    company_info["lastUpdate"] = rt_data.get("timestamp", "")
                        except Exception as rt_error:
                            logger.warning(f"Error fetching real-time data for {ticker}: {str(rt_error)}")
                        
                        # Store the complete stock data
                        stock_data[ticker] = {
                            "info": company_info,
                            "history": history
                        }
                        
                        logger.info(f"Successfully processed EODHD data for {ticker}")
                    else:
                        logger.warning(f"Invalid EODHD data format for {ticker}. Using fallback.")
                except Exception as e:
                    logger.warning(f"Error parsing EODHD response for {ticker}: {str(e)}")
                    logger.warning(f"No valid historical data for {ticker} from EODHD. Using fallback.")
            else:
                logger.warning(f"Failed to fetch EODHD data for {ticker}. Status: {response.status_code}")
                if DEBUG_MODE:
                    logger.debug(f"Response text: {response.text[:200]}")
                logger.warning(f"No valid historical data for {ticker} from EODHD. Using fallback.")
            
            # Add a delay to respect API rate limits
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error fetching EODHD data for {ticker}: {str(e)}")
            if DEBUG_MODE:
                import traceback
                logger.debug(f"DEBUG: Traceback for EODHD error: {traceback.format_exc()}")
    
    return stock_data

def fetch_eodhd_sentiment_data(tickers):
    """
    Fetch sentiment data for multiple tickers using EOD Historical Data API.
    
    Args:
        tickers (list): List of stock ticker symbols
        
    Returns:
        dict: Dictionary containing sentiment data
    """
    logger.info(f"Fetching EODHD sentiment data for {len(tickers)} tickers")
    sentiment_data = {}
    
    # Use same index mapping as the stock data function
    index_mapping = {
        "^GSPC": "SPY.US",    # S&P 500 (use SPY ETF as proxy)
        "^IXIC": "QQQ.US",    # NASDAQ Composite (use QQQ ETF as proxy)
        "^DJI": "DIA.US",     # Dow Jones Industrial Average (use DIA ETF as proxy)
        "^FTSE": "EZU.US",    # FTSE 100 (use European ETF as proxy)
        "^N225": "EWJ.US",    # Nikkei 225 (use Japan ETF as proxy)
        "^HSI": "FXI.US",     # Hang Seng Index (use China ETF as proxy)
        "^TNX": "TLT.US",     # 10-Year Treasury Yield (use TLT ETF as proxy)
        "^TYX": "TBT.US",     # 30-Year Treasury Yield (use TBT ETF as proxy)
    }
    
    for ticker in tickers:
        try:
            # Handle index symbols differently using the mapping
            if ticker.startswith("^"):
                if ticker in index_mapping:
                    eodhd_ticker = index_mapping[ticker]
                else:
                    # Skip indices we don't have a mapping for
                    logger.warning(f"No EODHD mapping for index {ticker}. Skipping sentiment.")
                    sentiment_data[ticker] = {"status": "skipped", "message": "No mapping for index"}
                    continue
            else:
                # For regular US stocks, add exchange suffix
                eodhd_ticker = f"{ticker}.US"
            
            # Using the search API from the examples to look for news
            url = f"{EODHD_BASE_URL}/search/{ticker}"
            params = {
                "api_token": EODHD_API_KEY,
                "fmt": "json"
            }
            
            logger.info(f"Fetching EODHD search/news for {ticker} ({eodhd_ticker})")
            response = requests.get(url, params=params, timeout=15)
            
            search_data = None
            if response.status_code == 200:
                try:
                    search_data = response.json()
                    if DEBUG_MODE:
                        if isinstance(search_data, dict):
                            logger.debug(f"DEBUG: EODHD search data keys: {list(search_data.keys())[:10]}")
                        else:
                            logger.debug(f"DEBUG: EODHD search data type: {type(search_data)}")
                except Exception as e:
                    logger.warning(f"Error parsing EODHD search response for {ticker}: {str(e)}")
            else:
                logger.warning(f"Failed to fetch EODHD search data for {ticker}. Status: {response.status_code}")
                if DEBUG_MODE:
                    logger.debug(f"Response text: {response.text[:200]}")
            
            # Try to get news sentiment data if available
            has_news = False
            news_data = []
            
            # Process any news found in the search
            if search_data and isinstance(search_data, list):
                for item in search_data:
                    if item.get("type") == "news":
                        has_news = True
                        news_data.append({
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", ""),
                            "url": item.get("url", ""),
                            "date": item.get("date", ""),
                            "source": item.get("source", ""),
                            # Add a basic sentiment assessment based on the headline
                            "sentiment": 0.0  # Neutral default
                        })
            
            # Process and store the news data with sentiment analysis
            if has_news:
                # Simple sentiment calculation
                try:
                    # Extract basic keywords for sentiment analysis
                    positive_words = ["up", "rise", "gain", "positive", "growth", "profit", "rally", "bullish", "success"]
                    negative_words = ["down", "fall", "loss", "negative", "decline", "drop", "bearish", "fail", "crash"]
                    
                    # Calculate a simple sentiment score for each news item
                    for news_item in news_data:
                        title_lower = news_item["title"].lower()
                        snippet_lower = news_item["snippet"].lower()
                        
                        pos_count = sum(1 for word in positive_words if word in title_lower or word in snippet_lower)
                        neg_count = sum(1 for word in negative_words if word in title_lower or word in snippet_lower)
                        
                        if pos_count > neg_count:
                            news_item["sentiment"] = 0.5  # Positive
                        elif neg_count > pos_count:
                            news_item["sentiment"] = -0.5  # Negative
                        else:
                            news_item["sentiment"] = 0.0  # Neutral
                    
                    # Calculate overall sentiment
                    sentiment_scores = [item["sentiment"] for item in news_data]
                    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
                    
                    processed_data = {
                        "symbol": ticker,
                        "news": news_data,
                        "sentiment": avg_sentiment,
                        "processed": {
                            "average_sentiment": avg_sentiment,
                            "sentiment_count": len(news_data),
                            "sentiment_label": "positive" if avg_sentiment > 0.05 else 
                                              "negative" if avg_sentiment < -0.05 else "neutral"
                        }
                    }
                    
                    sentiment_data[ticker] = processed_data
                    logger.info(f"Successfully processed sentiment for {ticker} from {len(news_data)} news items")
                except Exception as process_error:
                    logger.warning(f"Error processing sentiment data for {ticker}: {str(process_error)}")
                    sentiment_data[ticker] = {
                        "status": "error", 
                        "message": f"Error processing: {str(process_error)}",
                        "raw_data": news_data
                    }
            else:
                # If no news, try a real-time quote to get basic data
                time.sleep(1)  # Brief pause
                
                url = f"{EODHD_BASE_URL}/real-time/{eodhd_ticker}"
                params = {
                    "api_token": EODHD_API_KEY,
                    "fmt": "json"
                }
                
                logger.info(f"Fetching EODHD real-time data for {ticker} ({eodhd_ticker})")
                rt_response = requests.get(url, params=params, timeout=15)
                
                if rt_response.status_code == 200:
                    try:
                        rt_data = rt_response.json()
                        # Create a basic sentiment based on price change
                        change = rt_data.get("change", 0)
                        change_p = rt_data.get("change_p", 0)
                        
                        sentiment_value = 0.0
                        if change_p > 1.0:
                            sentiment_value = 0.3  # Positive
                        elif change_p < -1.0:
                            sentiment_value = -0.3  # Negative
                        
                        sentiment_data[ticker] = {
                            "symbol": ticker,
                            "sentiment": sentiment_value,
                            "change": change,
                            "change_p": change_p,
                            "price": rt_data.get("close", 0),
                            "processed": {
                                "average_sentiment": sentiment_value,
                                "sentiment_count": 1,
                                "sentiment_label": "positive" if sentiment_value > 0 else 
                                                  "negative" if sentiment_value < 0 else "neutral"
                            }
                        }
                        logger.info(f"Created basic sentiment for {ticker} based on price change")
                    except Exception as rt_error:
                        logger.warning(f"Error processing real-time data for {ticker}: {str(rt_error)}")
                        sentiment_data[ticker] = {"status": "no_data", "message": "No news or valid price data"}
                else:
                    logger.warning(f"Failed to fetch real-time data for {ticker}. Status: {rt_response.status_code}")
                    sentiment_data[ticker] = {"status": "no_data", "message": "No news found"}
            
            # Add a delay to respect API rate limits
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error fetching EODHD sentiment for {ticker}: {str(e)}")
            sentiment_data[ticker] = {"status": "error", "message": str(e)}
    
    return sentiment_data

def fetch_stock_data(tickers):
    """
    Fetch stock data for the given tickers using EODHD as primary source,
    with fallback to Alpaca, Twelve Data and Alpha Vantage.
    
    Args:
        tickers (list): List of stock ticker symbols
        
    Returns:
        dict: Dictionary containing stock data
    """
    logger.info(f"Fetching stock data for {len(tickers)} tickers")
    if DEBUG_MODE:
        logger.debug(f"DEBUG: Starting stock data collection for tickers: {tickers}")
    
    stock_data = {}
    failed_tickers = []
    
    # First try EODHD (more comprehensive data)
    try:
        stock_data = fetch_eodhd_stock_data(tickers)
        # Check if all tickers were fetched successfully
        missing_tickers = [t for t in tickers if t not in stock_data]
        if not missing_tickers:
            logger.info("Successfully fetched all stock data from EODHD")
            return stock_data
        else:
            logger.info(f"Missing {len(missing_tickers)} tickers from EODHD. Will try Alpaca for: {missing_tickers}")
    except Exception as e:
        logger.error(f"Error using EODHD API: {e}")
        stock_data = {}
        missing_tickers = tickers
    
    # Try Alpaca next for any missing tickers
    try:
        alpaca_data = fetch_alpaca_stock_data(missing_tickers)
        # Update stock_data with any new data from Alpaca
        stock_data.update(alpaca_data)
        
        # Check if we still have missing tickers
        missing_tickers = [t for t in tickers if t not in stock_data]
        if not missing_tickers:
            logger.info("Successfully fetched all remaining stock data from Alpaca")
            return stock_data
        else:
            logger.info(f"Still missing {len(missing_tickers)} tickers. Will try alternative sources for: {missing_tickers}")
    except Exception as e:
        logger.error(f"Error using Alpaca API: {e}")
        missing_tickers = [t for t in tickers if t not in stock_data]
    
    # Fallback logic for any missing tickers
    # This section will only run if EODHD and Alpaca didn't provide data for all tickers
    for ticker in missing_tickers:
        try:
            # Try to fetch data from Twelve Data API (much better free tier)
            logger.info(f"Fetching stock data for {ticker} from Twelve Data API")
            
            # Get daily price data (last 30 days)
            url = "https://api.twelvedata.com/time_series"
            params = {
                "symbol": ticker,
                "interval": "1day",
                "outputsize": 30,  # Last 30 days
                "apikey": TWELVE_DATA_API_KEY  # Twelve Data API key with better limits
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Debug output based on debug mode
                if DEBUG_MODE:
                    logger.debug(f"DEBUG: Twelve Data response for {ticker}: {json.dumps(data, indent=2)}")
                
                # Check if we got valid data
                if "values" in data:
                    # Convert to our expected format
                    history = []
                    values = data["values"]
                    
                    # Twelve Data returns values in descending order (newest first)
                    # We'll reverse to get ascending order (oldest first)
                    for value in reversed(values):
                        # Convert date format
                        date_str = value["datetime"]
                        history.append({
                            "Date": datetime.datetime.strptime(date_str, "%Y-%m-%d"),
                            "Open": float(value["open"]),
                            "High": float(value["high"]),
                            "Low": float(value["low"]),
                            "Close": float(value["close"]),
                            "Volume": float(value.get("volume", 0)),
                            "Dividends": 0.0,
                            "Stock Splits": 0.0
                        })
                    
                    # Get company profile from Twelve Data
                    time.sleep(1)  # Brief pause
                    
                    # Use Twelve Data profile endpoint
                    profile_url = "https://api.twelvedata.com/profile"
                    profile_params = {
                        "symbol": ticker,
                        "apikey": TWELVE_DATA_API_KEY
                    }
                    
                    profile_response = requests.get(profile_url, params=profile_params)
                    
                    if profile_response.status_code == 200:
                        profile_data = profile_response.json()
                        
                        if DEBUG_MODE:
                            logger.debug(f"DEBUG: Twelve Data profile response for {ticker}: {json.dumps(profile_data, indent=2)}")
                        
                        # Create info object
                        info = {
                            "symbol": ticker,
                            "shortName": profile_data.get("name", f"Stock {ticker}"),
                            "longName": profile_data.get("name", f"{ticker} Corporation"),
                            "sector": profile_data.get("sector", "Unknown"),
                            "industry": profile_data.get("industry", "Unknown"),
                            "marketCap": float(profile_data.get("market_capitalization", "0")),
                            "currentPrice": float(history[-1]["Close"]) if history else 0,
                            "description": profile_data.get("description", ""),
                            "exchange": profile_data.get("exchange", ""),
                            "peRatio": float(profile_data.get("pe_ratio", "0") or 0),
                            "dividendYield": float(profile_data.get("dividend_yield", "0") or 0),
                        }
                        
                        stock_data[ticker] = {
                            "info": info,
                            "history": history,
                        }
                        
                        logger.info(f"Successfully fetched stock data for {ticker}")
                    else:
                        # If profile API fails, still use the price data with basic info
                        logger.warning(f"Failed to fetch company profile for {ticker}. Using basic info.")
                        
                        # Create basic info with available data
                        info = {
                            "symbol": ticker,
                            "shortName": f"Stock {ticker}",
                            "longName": f"{ticker} Corporation",
                            "sector": "Unknown",
                            "industry": "Unknown",
                            "marketCap": 0,
                            "currentPrice": float(history[-1]["Close"]) if history else 0,
                        }
                        
                        stock_data[ticker] = {
                            "info": info,
                            "history": history,
                        }
                else:
                    # Data retrieval failed
                    logger.warning(f"Invalid data received for {ticker}. No data available.")
                    failed_tickers.append(ticker)
            else:
                # API call failed
                logger.warning(f"Failed to fetch data for {ticker} (Status: {response.status_code}).")
                failed_tickers.append(ticker)
            
            # Add a delay to respect API rate limits
            time.sleep(12)
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            failed_tickers.append(ticker)
    
    # Report any tickers that failed across all attempts
    if failed_tickers:
        logger.warning(f"Failed to retrieve data for {len(failed_tickers)} tickers: {', '.join(failed_tickers)}")
    
    return stock_data

def create_mock_stock_info(ticker):
    """
    Create mock stock information.
    
    Args:
        ticker (str): Stock ticker symbol
        
    Returns:
        dict: Mock stock information
    """
    # Sector and industry based on ticker
    sector = "Technology"
    industry = "Technology Services"
    
    if ticker in ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"]:
        sector = "Technology"
        industry = "Technology Services"
    elif ticker in ["JPM", "BAC", "WFC", "C", "GS", "MS", "BLK"]:
        sector = "Finance"
        industry = "Banking"
    elif ticker in ["XOM", "CVX", "BP", "SHEL", "TTE", "COP"]:
        sector = "Energy"
        industry = "Oil & Gas"
    
    # Determine a realistic price based on ticker
    price_map = {
        "AAPL": 178.72,
        "MSFT": 428.15,
        "GOOGL": 156.37,
        "AMZN": 185.25,
        "META": 494.78,
        "TSLA": 187.93,
        "NVDA": 874.15,
        "JPM": 191.42,
        "BAC": 39.60,
        "GS": 462.87,
        "XOM": 114.56,
        "CVX": 157.32,
    }
    
    current_price = price_map.get(ticker, 100.0)
    
    return {
        "symbol": ticker,
        "shortName": f"Stock {ticker}",
        "longName": f"{ticker} Corporation",
        "sector": sector,
        "industry": industry,
        "marketCap": 100000000000,
        "currentPrice": current_price
    }

def generate_mock_stock_history(ticker):
    """
    Generate mock stock history data when API calls fail.
    
    Args:
        ticker (str): Stock ticker symbol
        
    Returns:
        list: List of mock historical data points
    """
    history = []
    base_price = 100.0
    
    # Randomize the starting price based on ticker to create variety
    import hashlib
    ticker_hash = int(hashlib.md5(ticker.encode()).hexdigest(), 16) % 100
    base_price = base_price + ticker_hash
    
    # Generate 30 days of mock data
    for i in range(30):
        date = datetime.datetime.now() - datetime.timedelta(days=30-i)
        date_str = date.strftime("%Y-%m-%d")  # Convert to string format
        
        # Add some randomness to the price movement
        import random
        daily_change = random.uniform(-0.02, 0.02)  # -2% to +2% daily change
        
        # Ensure generally positive trend for testing
        if i > 20:  # Make the last 10 days trend up for testing
            daily_change = abs(daily_change) * 1.5
        
        price = base_price * (1 + daily_change)
        base_price = price  # Update for next iteration
        
        history.append({
            "Date": date_str,  # Store as string instead of datetime object
            "Open": price * 0.99,
            "High": price * 1.02,
            "Low": price * 0.98,
            "Close": price,
            "Volume": random.randint(1000000, 10000000),
            "Dividends": 0.0,
            "Stock Splits": 0.0
        })
    
    return history


def fetch_forex_data(pairs):
    """
    Fetch forex data using Alpha Vantage API.
    
    Args:
        pairs (list): List of currency pairs (e.g., ['EURUSD=X'])
        
    Returns:
        dict: Dictionary containing forex data
    """
    logger.info(f"Fetching forex data for {len(pairs)} pairs")
    forex_data = {}
    failed_pairs = []
    
    for pair in pairs:
        # Clean up Yahoo Finance format to Alpha Vantage format
        # Convert EURUSD=X to EUR/USD
        if pair.endswith("=X"):
            clean_pair = pair[:-2]
            from_currency = clean_pair[:3]
            to_currency = clean_pair[3:]
        else:
            # Try to extract currencies from the format
            if len(pair) == 6:
                from_currency = pair[:3]
                to_currency = pair[3:]
            else:
                logger.warning(f"Unsupported forex pair format: {pair}. Skipping.")
                failed_pairs.append(pair)
                continue
        
        try:
            logger.info(f"Fetching forex data for {from_currency}/{to_currency} from Twelve Data")
            
            # Use Twelve Data API for forex
            url = "https://api.twelvedata.com/time_series"
            params = {
                "symbol": f"{from_currency}/{to_currency}",
                "interval": "1day",
                "outputsize": 30,  # Last 30 days
                "apikey": TWELVE_DATA_API_KEY
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if DEBUG_MODE:
                    logger.debug(f"DEBUG: Twelve Data forex response for {pair}: {json.dumps(data, indent=2)}")
                
                # Check if we got valid data
                if "values" in data:
                    # Convert to our expected format
                    history = []
                    values = data["values"]
                    
                    # Twelve Data returns values in descending order (newest first)
                    # We'll reverse to get ascending order (oldest first)
                    for value in reversed(values):
                        # Convert date format
                        date_str = value["datetime"]
                        history.append({
                            "Date": datetime.datetime.strptime(date_str, "%Y-%m-%d"),
                            "Open": float(value["open"]),
                            "High": float(value["high"]),
                            "Low": float(value["low"]),
                            "Close": float(value["close"]),
                            # No volume data for forex, use a placeholder
                            "Volume": 0.0,
                            "Dividends": 0.0,
                            "Stock Splits": 0.0
                        })
                    
                    forex_data[pair] = history
                    logger.info(f"Successfully fetched forex data for {pair}")
                else:
                    logger.warning(f"Invalid data received for {pair}. Skipping.")
                    failed_pairs.append(pair)
            else:
                logger.warning(f"Failed to fetch forex data for {pair} (Status: {response.status_code}).")
                failed_pairs.append(pair)
            
            # Add a delay to respect API rate limits
            time.sleep(12)
            
        except Exception as e:
            logger.error(f"Error fetching forex data for {pair}: {e}")
            failed_pairs.append(pair)
    
    # Report any forex pairs that failed
    if failed_pairs:
        logger.warning(f"Failed to retrieve data for {len(failed_pairs)} forex pairs: {', '.join(failed_pairs)}")
    
    return forex_data

def fetch_alpaca_stock_data(tickers):
    """
    Fetch stock data for multiple tickers using Alpaca Markets API.
    
    Args:
        tickers (list): List of stock ticker symbols
        
    Returns:
        dict: Dictionary containing stock data
    """
    logger.info(f"Fetching Alpaca stock data for {len(tickers)} tickers")
    stock_data = {}
    
    # Map standard index symbols to Alpaca format
    index_mapping = {
        "^GSPC": "SPY",    # S&P 500 (use SPY ETF as proxy)
        "^IXIC": "QQQ",    # NASDAQ (use QQQ ETF as proxy)
        "^DJI": "DIA",     # Dow Jones (use DIA ETF as proxy)
        "^TNX": "TLT",     # 10-Year Treasury (use TLT ETF as proxy)
        "^TYX": "TBT",     # 30-Year Treasury (use TBT ETF as proxy)
        # International indices might not be available in free tier
        "^FTSE": "VGK",    # FTSE 100 (use VGK ETF as European proxy)
        "^N225": "EWJ",    # Nikkei 225 (use EWJ ETF as Japan proxy)
        "^HSI": "FXI",     # Hang Seng (use FXI ETF as China proxy)
    }
    
    # Map tickers for Alpaca
    alpaca_tickers = []
    for ticker in tickers:
        if ticker.startswith("^"):
            # If it's an index, use the ETF proxy if available
            if ticker in index_mapping:
                alpaca_tickers.append(index_mapping[ticker])
            else:
                logger.warning(f"No Alpaca mapping for index {ticker}. Will use mock data.")
        else:
            alpaca_tickers.append(ticker)
    
    # Batch process tickers to avoid hitting rate limits
    batch_size = 10  # Process 10 tickers at a time
    all_data = {}
    
    for i in range(0, len(alpaca_tickers), batch_size):
        batch = alpaca_tickers[i:i+batch_size]
        
        # If batch is empty (e.g., all indices without mappings), skip
        if not batch:
            continue
            
        try:
            # Format for Alpaca: comma-separated string
            symbols_str = ",".join(batch)
            
            # Set up request parameters
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=30)
            
            # Format dates as ISO strings (YYYY-MM-DD)
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # Get historical bars from Alpaca
            url = f"{ALPACA_DATA_URL}/v2/stocks/bars"
            headers = {
                "APCA-API-KEY-ID": ALPACA_API_KEY,
                "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
                "Accept": "application/json"
            }
            params = {
                "symbols": symbols_str,
                "timeframe": "1D",  # Daily data
                "start": start_str,
                "end": end_str,
                "limit": 30,
                "adjustment": "all"  # Adjust for splits and dividends
            }
            
            logger.info(f"Fetching Alpaca data for batch: {batch}")
            
            if DEBUG_MODE:
                logger.debug(f"DEBUG: Alpaca API URL: {url}")
                logger.debug(f"DEBUG: Alpaca API Headers: {headers}")
                logger.debug(f"DEBUG: Alpaca API Params: {params}")
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            # Log full response for debugging
            if DEBUG_MODE:
                logger.debug(f"DEBUG: Alpaca response status: {response.status_code}")
                logger.debug(f"DEBUG: Alpaca response headers: {response.headers}")
                logger.debug(f"DEBUG: First 500 chars of response: {response.text[:500]}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Debug output for the first response
                if DEBUG_MODE and i == 0:
                    logger.debug(f"DEBUG: Alpaca bars response structure: {json.dumps(data.keys(), indent=2)}")
                
                # Check if we got valid data
                if "bars" in data:
                    bars_data = data["bars"]
                    
                    # Process each ticker in the batch
                    for symbol in batch:
                        if symbol in bars_data and bars_data[symbol]:
                            # Get company details
                            details_url = f"{ALPACA_DATA_URL}/v2/stocks/{symbol}/details"
                            details_response = requests.get(details_url, headers=headers, timeout=10)
                            
                            company_info = {}
                            if details_response.status_code == 200:
                                company_details = details_response.json()
                                if DEBUG_MODE:
                                    logger.debug(f"DEBUG: Alpaca details for {symbol}: {json.dumps(company_details, indent=2)}")
                                
                                company_info = {
                                    "symbol": symbol,
                                    "shortName": company_details.get("name", f"Stock {symbol}"),
                                    "longName": company_details.get("name", f"{symbol} Corporation"),
                                    "sector": company_details.get("sector", "Unknown"),
                                    "industry": company_details.get("industry", "Unknown"),
                                    "marketCap": float(company_details.get("market_cap", 0)),
                                    "currentPrice": float(company_details.get("price", 0)),
                                    "exchange": company_details.get("exchange", ""),
                                    "peRatio": company_details.get("pe_ratio", 0),
                                    "dividendYield": company_details.get("dividend_yield", 0) if company_details.get("dividend_yield") else 0
                                }
                            else:
                                # If company details fail, create basic info
                                latest_price = float(bars_data[symbol][-1]["c"]) if bars_data[symbol] else 0
                                company_info = {
                                    "symbol": symbol,
                                    "shortName": f"Stock {symbol}",
                                    "longName": f"{symbol} Corporation",
                                    "sector": "Unknown",
                                    "industry": "Unknown",
                                    "marketCap": 0,
                                    "currentPrice": latest_price
                                }
                            
                            # Process historical bars
                            history = []
                            for bar in bars_data[symbol]:
                                date_str = bar["t"].split("T")[0]  # Extract date part from ISO timestamp
                                history.append({
                                    "Date": date_str,
                                    "Open": float(bar["o"]),
                                    "High": float(bar["h"]),
                                    "Low": float(bar["l"]),
                                    "Close": float(bar["c"]),
                                    "Volume": float(bar["v"]),
                                    "Dividends": 0.0,  # Alpaca doesn't provide dividend data in bars
                                    "Stock Splits": 0.0  # Alpaca doesn't provide split data in bars
                                })
                            
                            all_data[symbol] = {
                                "info": company_info,
                                "history": history
                            }
                            logger.info(f"Successfully processed Alpaca data for {symbol}")
                        else:
                            logger.warning(f"No bar data found for {symbol} in Alpaca response")
                else:
                    logger.warning(f"No 'bars' key found in Alpaca response: {data}")
            else:
                logger.warning(f"Failed to fetch data from Alpaca (Status: {response.status_code}): {response.text}")
            
            # Add a short delay between batches
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error fetching batch from Alpaca: {e}")
    
    # Now map the Alpaca data back to the original ticker symbols
    for ticker in tickers:
        if ticker.startswith("^") and ticker in index_mapping:
            # Map the ETF data back to the index
            etf_symbol = index_mapping[ticker]
            if etf_symbol in all_data:
                # Get the ETF data
                etf_data = all_data[etf_symbol]
                
                # Create index-specific info
                shortname = f"Index {ticker}"
                longname = f"{ticker} Index"
                
                if ticker == "^GSPC":
                    shortname = "S&P 500"
                    longname = "S&P 500 Index"
                elif ticker == "^IXIC":
                    shortname = "NASDAQ Composite"
                    longname = "NASDAQ Composite Index"
                elif ticker == "^DJI":
                    shortname = "Dow Jones Industrial Average"
                    longname = "Dow Jones Industrial Average Index"
                elif ticker == "^FTSE":
                    shortname = "FTSE 100"
                    longname = "Financial Times Stock Exchange 100 Index"
                elif ticker == "^N225":
                    shortname = "Nikkei 225"
                    longname = "Nikkei 225 Index"
                elif ticker == "^HSI":
                    shortname = "Hang Seng Index"
                    longname = "Hang Seng Index"
                elif ticker == "^TNX":
                    shortname = "10-Year Treasury Yield"
                    longname = "CBOE 10-Year Treasury Note Yield Index"
                elif ticker == "^TYX":
                    shortname = "30-Year Treasury Yield"
                    longname = "CBOE 30-Year Treasury Bond Yield Index"
                
                # Use the ETF's price data but customize the info for the index
                info = {
                    "symbol": ticker,
                    "shortName": shortname,
                    "longName": longname,
                    "sector": "Index",
                    "industry": "Market Index",
                    "marketCap": 1000000000000,
                    "currentPrice": etf_data["info"]["currentPrice"]
                }
                
                stock_data[ticker] = {
                    "info": info,
                    "history": etf_data["history"]
                }
            else:
                # Fall back to mock data
                logger.warning(f"No data available for index proxy {etf_symbol}. Using mock data for {ticker}.")
                stock_data[ticker] = {
                    "info": create_mock_index_info(ticker),
                    "history": generate_mock_stock_history(ticker)
                }
        elif not ticker.startswith("^"):
            # Regular stock ticker
            if ticker in all_data:
                stock_data[ticker] = all_data[ticker]
            else:
                # Fall back to mock data
                logger.warning(f"No data available for {ticker} from Alpaca. Using mock data.")
                stock_data[ticker] = {
                    "info": create_mock_stock_info(ticker),
                    "history": generate_mock_stock_history(ticker)
                }
    
    return stock_data


def generate_mock_forex_history(pair):
    """
    Generate mock forex history data when API calls fail.
    
    Args:
        pair (str): Currency pair symbol
        
    Returns:
        list: List of mock historical data points
    """
    history = []
    
    # Set base exchange rate based on the pair
    base_rates = {
        "EURUSD=X": 1.10,
        "GBPUSD=X": 1.25,
        "USDJPY=X": 150.0,
        "USDCAD=X": 1.35,
        "AUDUSD=X": 0.65,
        "USDCNY=X": 7.20,
    }
    
    base_rate = base_rates.get(pair, 1.0)
    
    # Generate 30 days of mock data
    import random
    for i in range(30):
        date = datetime.datetime.now() - datetime.timedelta(days=30-i)
        date_str = date.strftime("%Y-%m-%d")  # Convert to string format
        
        # Add some randomness to the rate movement
        daily_change = random.uniform(-0.005, 0.005)  # -0.5% to +0.5% daily change
        
        # Create small trends for testing
        if i > 20:  # Last 10 days
            if pair in ["EURUSD=X", "GBPUSD=X", "AUDUSD=X"]:  # These strengthen against USD
                daily_change = abs(daily_change) * 0.8
            else:  # USD strengthens against these
                daily_change = -abs(daily_change) * 0.8
        
        rate = base_rate * (1 + daily_change)
        base_rate = rate  # Update for next iteration
        
        history.append({
            "Date": date_str,  # Store as string instead of datetime object
            "Open": rate * 0.999,
            "High": rate * 1.003,
            "Low": rate * 0.997,
            "Close": rate,
            "Volume": random.randint(1000000, 5000000),
            "Dividends": 0.0,
            "Stock Splits": 0.0
        })
    
    return history


def fetch_bond_data(tickers):
    """
    Fetch bond data using FRED API for Treasury yields.
    For bond data, we map Yahoo Finance tickers to FRED series IDs.
    
    Args:
        tickers (list): List of bond tickers (e.g., '^TNX' for 10-Year Treasury)
        
    Returns:
        dict: Dictionary containing bond data
    """
    logger.info(f"Fetching bond data for {len(tickers)} bonds")
    bond_data = {}
    failed_bonds = []
    
    # Map Yahoo Finance bond tickers to FRED series IDs
    ticker_to_fred = {
        "^TNX": "DGS10",   # 10-Year Treasury Constant Maturity Rate
        "^TYX": "DGS30",   # 30-Year Treasury Constant Maturity Rate
        "^FVX": "DGS5",    # 5-Year Treasury Constant Maturity Rate
        "^IRX": "DTB3",    # 3-Month Treasury Bill: Secondary Market Rate
    }
    
    for ticker in tickers:
        # Check if we have a mapping for this ticker
        fred_id = ticker_to_fred.get(ticker)
        
        if fred_id:
            try:
                logger.info(f"Fetching bond data for {ticker} (FRED ID: {fred_id})")
                
                # Using requests directly as fredapi might not be installed
                url = f"https://api.stlouisfed.org/fred/series/observations"
                params = {
                    "series_id": fred_id,
                    "api_key": FRED_API_KEY,
                    "file_type": "json",
                    "limit": 100,  # Get the last 100 observations
                    "sort_order": "desc",
                    "observation_start": (datetime.datetime.now() - datetime.timedelta(days=180)).strftime("%Y-%m-%d")
                }
                
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if we got valid data
                    if "observations" in data and len(data["observations"]) > 0:
                        # Convert to our expected format
                        history = []
                        observations = data["observations"]
                        
                        # Sort dates in ascending order (oldest first)
                        observations.sort(key=lambda x: x["date"])
                        
                        for obs in observations:
                            # Skip entries without values
                            if obs["value"] == ".":
                                continue
                                
                            # The value is a percentage, so we need to convert it to decimal
                            value = float(obs["value"])
                            
                            # For bond data, the value is the yield which is a percentage
                            # We'll use this as the "Close" price
                            history.append({
                                "Date": datetime.datetime.strptime(obs["date"], "%Y-%m-%d"),
                                "Open": value,
                                "High": value,
                                "Low": value,
                                "Close": value,
                                "Volume": 0.0,
                                "Dividends": 0.0,
                                "Stock Splits": 0.0
                            })
                        
                        if history:
                            bond_data[ticker] = history
                            logger.info(f"Successfully fetched bond data for {ticker}")
                        else:
                            logger.warning(f"No valid observations for {ticker}. Skipping.")
                            failed_bonds.append(ticker)
                    else:
                        logger.warning(f"Invalid data received for {ticker}. Skipping.")
                        failed_bonds.append(ticker)
                else:
                    logger.warning(f"Failed to fetch bond data for {ticker} (Status: {response.status_code}). Skipping.")
                    failed_bonds.append(ticker)
            
            except Exception as e:
                logger.error(f"Error fetching bond data for {ticker}: {e}")
                failed_bonds.append(ticker)
        else:
            logger.warning(f"No FRED mapping for bond ticker {ticker}. Skipping.")
            failed_bonds.append(ticker)
    
    # Report any bonds that failed across all attempts
    if failed_bonds:
        logger.warning(f"Failed to retrieve data for {len(failed_bonds)} bond tickers: {', '.join(failed_bonds)}")
    
    return bond_data

def generate_mock_bond_history(ticker):
    """
    Generate mock bond yield history data when API calls fail.
    
    Args:
        ticker (str): Bond ticker symbol
        
    Returns:
        list: List of mock historical data points
    """
    history = []
    
    # Set base yield based on the bond type
    base_yields = {
        "^TNX": 4.50,  # 10-Year Treasury
        "^TYX": 4.65,  # 30-Year Treasury
        "^FVX": 4.30,  # 5-Year Treasury
        "^IRX": 3.90,  # 13-Week Treasury Bill
    }
    
    base_yield = base_yields.get(ticker, 4.0)
    
    # Generate 30 days of mock data
    import random
    for i in range(30):
        date = datetime.datetime.now() - datetime.timedelta(days=30-i)
        date_str = date.strftime("%Y-%m-%d")  # Convert to string format
        
        # Add some randomness to the yield movement
        daily_change = random.uniform(-0.04, 0.04)  # -4 to +4 basis points daily change
        
        # Create trends for testing - yields generally trending down in test data
        if i > 15:
            daily_change = -abs(daily_change) * 1.2
        
        yield_value = base_yield + daily_change / 100  # Convert basis points to percentage
        base_yield = yield_value  # Update for next iteration
        
        history.append({
            "Date": date_str,  # Store as string instead of datetime object
            "Open": yield_value * 0.998,
            "High": yield_value * 1.004,
            "Low": yield_value * 0.996,
            "Close": yield_value,
            "Volume": random.randint(100000, 500000),
            "Dividends": 0.0,
            "Stock Splits": 0.0
        })
    
    return history


def fetch_news_data(queries):
    """
    Fetch news headlines and content for given queries.
    
    Args:
        queries (list): List of search queries
        
    Returns:
        dict: Dictionary containing news data
    """
    logger.info(f"Fetching news data for {len(queries)} queries")
    news_data = {}
    
    for query in queries:
        try:
            news = news_api.get_everything(
                q=query,
                from_param=(datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
                to=TODAY,
                language="en",
                sort_by="relevancy",
                page_size=10
            )
            news_data[query] = news
            logger.debug(f"Successfully fetched news for {query}")
        except Exception as e:
            logger.error(f"Error fetching news for {query}: {e}")
            # Provide fallback if API request fails
            news_data[query] = {
                "status": "error",
                "totalResults": 0,
                "articles": []
            }
    
    return news_data


def fetch_trend_data(keywords):
    """
    Fetch Google Trends data for given keywords.
    
    Args:
        keywords (list): List of keywords to search for
        
    Returns:
        dict: Dictionary containing trends data
    """
    logger.info(f"Fetching trend data for {len(keywords)} keywords")
    trend_data = {}
    
    try:
        trend_api.build_payload(keywords, timeframe='now 7-d')
        trend_df = trend_api.interest_over_time()
        if not trend_df.empty:
            trend_data = trend_df.reset_index().to_dict(orient="records")
            logger.debug(f"Successfully fetched trends for {keywords}")
        else:
            logger.warning(f"No trend data found for {keywords}")
    except Exception as e:
        logger.error(f"Error fetching trends for {keywords}: {e}")
    
    return trend_data


# Crypto data function has been removed as requested


def fetch_fred_data(series):
    """
    Fetch economic data from FRED API.
    
    Args:
        series (list): List of FRED series IDs
        
    Returns:
        dict: Dictionary containing FRED data
    """
    logger.info(f"Fetching FRED data for {len(series)} series")
    fred_data = {}
    
    for series_id in series:
        try:
            # Using requests directly as fredapi is not in requirements
            url = f"https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "limit": 30,  # Last 30 observations
                "sort_order": "desc",
                "observation_start": (datetime.datetime.now() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
            }
            response = requests.get(url, params=params)
            if response.status_code == 200:
                fred_data[series_id] = response.json()
                logger.debug(f"Successfully fetched FRED data for {series_id}")
            else:
                logger.error(f"Error fetching FRED data for {series_id}: {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching FRED data for {series_id}: {e}")
    
    return fred_data


def fetch_alpha_vantage_data(symbols, function="TIME_SERIES_DAILY"):
    """
    Fetch data from Alpha Vantage API.
    
    Args:
        symbols (list): List of stock symbols
        function (str): Alpha Vantage function to use
        
    Returns:
        dict: Dictionary containing Alpha Vantage data
    """
    logger.info(f"Fetching Alpha Vantage data for {len(symbols)} symbols")
    alpha_data = {}
    
    for symbol in symbols:
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": function,
                "symbol": symbol,
                "apikey": ALPHA_VANTAGE_API_KEY,
                "outputsize": "compact"
            }
            response = requests.get(url, params=params)
            if response.status_code == 200:
                alpha_data[symbol] = response.json()
                logger.debug(f"Successfully fetched Alpha Vantage data for {symbol}")
                # Alpha Vantage has a rate limit, so we need to pause
                time.sleep(12)  # To respect the free tier limit of 5 calls per minute
            else:
                logger.error(f"Error fetching Alpha Vantage data for {symbol}: {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching Alpha Vantage data for {symbol}: {e}")
    
    return alpha_data


def fetch_finnhub_quote_data(symbols):
    """
    Fetch real-time quote data from Finnhub API.
    
    Args:
        symbols (list): List of stock symbols
        
    Returns:
        dict: Dictionary containing quote data
    """
    logger.info(f"Fetching Finnhub quote data for {len(symbols)} symbols")
    quote_data = {}
    
    for symbol in symbols:
        try:
            quote = finnhub_client.quote(symbol)
            quote_data[symbol] = quote
            logger.debug(f"Successfully fetched quote data for {symbol}")
            time.sleep(0.1)  # Slight delay to avoid hitting rate limits
        except Exception as e:
            logger.error(f"Error fetching Finnhub quote data for {symbol}: {e}")
    
    return quote_data


def fetch_finnhub_company_data(symbols):
    """
    Fetch company profile data from Finnhub API.
    
    Args:
        symbols (list): List of stock symbols
        
    Returns:
        dict: Dictionary containing company profile data
    """
    logger.info(f"Fetching Finnhub company data for {len(symbols)} symbols")
    company_data = {}
    
    for symbol in symbols:
        try:
            profile = finnhub_client.company_profile2(symbol=symbol)
            company_data[symbol] = profile
            logger.debug(f"Successfully fetched company profile for {symbol}")
            time.sleep(0.1)  # Slight delay to avoid hitting rate limits
        except Exception as e:
            logger.error(f"Error fetching Finnhub company profile for {symbol}: {e}")
    
    return company_data


# Removing Finnhub sentiment API since it requires premium subscription
# We'll use the News API for sentiment analysis instead in the analyze_data.py file


def fetch_finnhub_earnings_data(symbols):
    """
    Fetch earnings data from Finnhub API.
    
    Args:
        symbols (list): List of stock symbols
        
    Returns:
        dict: Dictionary containing earnings data
    """
    logger.info(f"Fetching Finnhub earnings data for {len(symbols)} symbols")
    earnings_data = {}
    
    for symbol in symbols:
        try:
            # The company_earnings method only takes the symbol 
            earnings = finnhub_client.company_earnings(symbol)
            earnings_data[symbol] = earnings
            logger.debug(f"Successfully fetched earnings data for {symbol}")
            time.sleep(0.1)  # Slight delay to avoid hitting rate limits
        except Exception as e:
            logger.error(f"Error fetching Finnhub earnings data for {symbol}: {e}")
    
    return earnings_data


def fetch_finnhub_insider_data(symbols):
    """
    Fetch insider transactions data from Finnhub API.
    
    Args:
        symbols (list): List of stock symbols
        
    Returns:
        dict: Dictionary containing insider transactions data
    """
    logger.info(f"Fetching Finnhub insider data for {len(symbols)} symbols")
    insider_data = {}
    
    from_date = (datetime.datetime.now() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
    to_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    for symbol in symbols:
        try:
            insider = finnhub_client.stock_insider_transactions(symbol, from_date, to_date)
            insider_data[symbol] = insider
            logger.debug(f"Successfully fetched insider data for {symbol}")
            time.sleep(0.1)  # Slight delay to avoid hitting rate limits
        except Exception as e:
            logger.error(f"Error fetching Finnhub insider data for {symbol}: {e}")
    
    return insider_data


class DataEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles datetime, timestamps, and numpy types.
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d")  # Format as YYYY-MM-DD
        elif isinstance(obj, pd.Timestamp):
            return obj.strftime("%Y-%m-%d")  # Format as YYYY-MM-DD
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        return super().default(obj)

def save_data(data, filename):
    """
    Save data to a JSON file.
    
    Args:
        data (dict): Data to save
        filename (str): Filename to save data to
    """
    file_path = RAW_DATA_DIR / f"{filename}_{TODAY}.json"
    try:
        # Pre-process data to fix any potential serialization issues
        if isinstance(data, dict):
            # Clean each ticker's data for potential datetime objects
            for ticker, ticker_data in data.items():
                if isinstance(ticker_data, dict) and 'history' in ticker_data:
                    # Ensure all date fields in history are strings
                    for i, entry in enumerate(ticker_data['history']):
                        if isinstance(entry, dict) and 'Date' in entry:
                            if isinstance(entry['Date'], (datetime.datetime, pd.Timestamp)):
                                ticker_data['history'][i]['Date'] = entry['Date'].strftime("%Y-%m-%d")
        
        # Now save the data with our custom encoder as backup
        with open(file_path, 'w') as f:
            json.dump(data, f, cls=DataEncoder, ensure_ascii=False, indent=2)
        logger.info(f"Data saved to {file_path}")
        
        if DEBUG_MODE:
            # Check if there's actual content in the data
            if isinstance(data, dict) and len(data) == 0:
                logger.warning(f"DEBUG: Empty dictionary saved to {file_path}")
            elif isinstance(data, list) and len(data) == 0:
                logger.warning(f"DEBUG: Empty list saved to {file_path}")
            else:
                try:
                    # Try to serialize to get size
                    serialized_data = json.dumps(data, cls=DataEncoder)
                    data_size = len(serialized_data)
                    logger.debug(f"DEBUG: Saved {data_size} bytes to {file_path}")
                    
                    # Print summary of what was saved
                    if isinstance(data, dict):
                        logger.debug(f"DEBUG: Keys in saved data: {list(data.keys())}")
                        for key, value in data.items():
                            if isinstance(value, dict):
                                logger.debug(f"DEBUG:   {key}: {len(value)} items")
                            elif isinstance(value, list):
                                logger.debug(f"DEBUG:   {key}: {len(value)} items (list)")
                            else:
                                logger.debug(f"DEBUG:   {key}: {type(value).__name__}")
                except Exception as err:
                    logger.error(f"Error calculating data size: {err}")
    except Exception as e:
        logger.error(f"Error saving data to {file_path}: {e}")
        # Try to identify the problematic part
        if isinstance(data, dict):
            for key, value in data.items():
                try:
                    # Test serialize each value
                    json.dumps({key: value}, cls=DataEncoder)
                except Exception as key_error:
                    logger.error(f"Problem with key '{key}': {key_error}")
                    # If it's a dict with history, check each record
                    if isinstance(value, dict) and 'history' in value:
                        for i, record in enumerate(value['history']):
                            try:
                                json.dumps(record, cls=DataEncoder)
                            except Exception as record_error:
                                logger.error(f"Problem with history record {i} for '{key}': {record_error}")
                                # Print problematic record keys and types
                                for rec_key, rec_val in record.items():
                                    logger.error(f"   {rec_key}: {type(rec_val)}")


def test_run():
    """
    A limited test run that fetches a minimal set of data to test API integration.
    Uses mock data generation when API requests fail.
    """
    # Ensure data directories exist
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Test with a single market and reduced stocks to avoid rate limits
    test_market_name = "S&P500"
    test_index = markets[test_market_name]["index"]
    test_stocks = markets[test_market_name]["stocks"][:3]  # Just first 3 stocks
    
    test_bonds = ["^TNX"]  # Just 10-Year Treasury
    test_forex = ["EURUSD=X"]  # Just EUR/USD pair
    test_news_queries = ["stock market"]  # Just one news query
    test_fred_series = ["UNRATE"]  # Just unemployment rate
    test_finnhub_symbols = ["AAPL"]  # Just Apple for Finnhub
    
    # Use a short list of stocks for EODHD API testing
    eodhd_test_stocks = ["AAPL", "MSFT"]  # Test with Apple and Microsoft
    
    # Fetch data (minimal calls to avoid rate limits)
    logger.info("Starting test data collection")
    
    # Test EODHD API directly
    logger.info("Testing EODHD API directly")
    logger.info("Fetching EODHD stock data")
    eodhd_stock_data = fetch_eodhd_stock_data(eodhd_test_stocks)
    
    logger.info("Fetching EODHD sentiment data")
    eodhd_sentiment_data = fetch_eodhd_sentiment_data(eodhd_test_stocks)
    
    # Save EODHD test data
    save_data(eodhd_stock_data, "eodhd_stock_test")
    save_data(eodhd_sentiment_data, "eodhd_sentiment_test")
    
    # Fetch market index data through the main function
    logger.info(f"Fetching index data for {test_market_name}")
    index_data = fetch_stock_data([test_index])
    market_index_name = f"index_{test_market_name.lower()}"
    save_data(index_data, market_index_name)
    
    # Fetch a few stocks for the market
    logger.info(f"Fetching stock data for {test_market_name}")
    market_stocks = fetch_stock_data(test_stocks)
    market_stocks_name = f"stocks_{test_market_name.lower()}"
    save_data(market_stocks, market_stocks_name)
    
    # Create mock data for other markets to test multi-market support
    logger.info("Creating mock data for NASDAQ market")
    nasdaq_index = markets["NASDAQ"]["index"]
    nasdaq_index_data = {
        nasdaq_index: {
            "info": {
                "symbol": nasdaq_index,
                "shortName": "NASDAQ Composite",
                "longName": "NASDAQ Composite Index",
                "sector": "Index",
                "industry": "Market Index",
                "marketCap": 1000000000000,
                "currentPrice": 15756.64
            },
            "history": generate_mock_stock_history(nasdaq_index)
        }
    }
    save_data(nasdaq_index_data, "index_nasdaq")
    
    # Create mock stock data for NASDAQ
    nasdaq_stocks_data = {}
    for ticker in markets["NASDAQ"]["stocks"][:3]:  # Just first 3 stocks
        nasdaq_stocks_data[ticker] = {
            "info": create_mock_stock_info(ticker),
            "history": generate_mock_stock_history(ticker)
        }
    save_data(nasdaq_stocks_data, "stocks_nasdaq")
    
    # Other data types
    logger.info("Fetching bond data")
    bond_data = fetch_bond_data(test_bonds)
    
    logger.info("Fetching forex data")
    forex_data = fetch_forex_data(test_forex)
    
    logger.info("Fetching news data")
    news_data = fetch_news_data(test_news_queries)
    
    logger.info("Fetching FRED data")
    fred_data = fetch_fred_data(test_fred_series)
    
    logger.info("Fetching Alpha Vantage data")
    alpha_data = fetch_alpha_vantage_data(["AAPL"])
    
    # Finnhub data
    logger.info("Fetching Finnhub quote data")
    finnhub_quote_data = fetch_finnhub_quote_data(test_finnhub_symbols)
    
    logger.info("Fetching Finnhub company data")
    finnhub_company_data = fetch_finnhub_company_data(test_finnhub_symbols)
    
    # We don't use Finnhub sentiment data anymore as it requires premium API access
    logger.info("Using EODHD sentiment data instead of Finnhub sentiment")
    finnhub_sentiment_data = {}  # Empty dictionary as placeholder
    
    logger.info("Fetching Finnhub earnings data")
    finnhub_earnings_data = fetch_finnhub_earnings_data(test_finnhub_symbols)
    
    logger.info("Fetching Finnhub insider data")
    finnhub_insider_data = fetch_finnhub_insider_data(test_finnhub_symbols)
    
    # Save additional data
    save_data(forex_data, "forex")
    save_data(bond_data, "bonds")
    save_data(news_data, "news")
    save_data(fred_data, "fred")
    save_data(alpha_data, "alpha_vantage")
    save_data(eodhd_sentiment_data, "eodhd_sentiment")
    
    # Save Finnhub data
    save_data(finnhub_quote_data, "finnhub_quotes")
    save_data(finnhub_company_data, "finnhub_company")
    save_data(finnhub_sentiment_data, "finnhub_sentiment")
    save_data(finnhub_earnings_data, "finnhub_earnings")
    save_data(finnhub_insider_data, "finnhub_insider")
    
    logger.info("Test data collection completed")
    
    return {
        "eodhd_stock_test": len(eodhd_stock_data),
        "eodhd_sentiment_test": len(eodhd_sentiment_data),
        f"index_{test_market_name.lower()}": len(index_data),
        f"stocks_{test_market_name.lower()}": len(market_stocks),
        "index_nasdaq": len(nasdaq_index_data),
        "stocks_nasdaq": len(nasdaq_stocks_data),
        "forex": len(forex_data),
        "bonds": len(bond_data),
        "news": len(news_data),
        "fred": len(fred_data),
        "alpha_vantage": len(alpha_data),
        "eodhd_sentiment": len(eodhd_sentiment_data),
        "finnhub_quotes": len(finnhub_quote_data),
        "finnhub_company": len(finnhub_company_data),
        "finnhub_sentiment": len(finnhub_sentiment_data),
        "finnhub_earnings": len(finnhub_earnings_data),
        "finnhub_insider": len(finnhub_insider_data)
    }

def main():
    # Ensure data directories exist
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Track total progress and failures
    total_markets = len(markets)
    markets_processed = 0
    total_stocks = sum(len(market_data["stocks"]) for market_data in markets.values())
    stocks_processed = 0
    all_failed_items = {
        "stocks": [],
        "indices": [],
        "forex": [],
        "bonds": [],
        "news": [],
        "sentiment": [],
        "company_data": []
    }
    
    # Process each market
    for market_name, market_data in markets.items():
        markets_processed += 1
        market_progress = (markets_processed / total_markets) * 100
        logger.info(f"Processing {market_name} market ({markets_processed}/{total_markets}, {market_progress:.1f}% of markets)")
        
        # Fetch index data
        index_ticker = market_data["index"]
        logger.info(f"Fetching index data for {market_name}: {index_ticker}")
        index_data = fetch_stock_data([index_ticker])
        
        # Check if index data was fetched successfully
        if index_ticker not in index_data:
            all_failed_items["indices"].append(index_ticker)
            logger.warning(f"Failed to fetch index data for {market_name} ({index_ticker})")
        
        market_index_name = f"index_{market_name.lower()}"
        save_data(index_data, market_index_name)
        time.sleep(3)  # Pause between API calls
        
        # Fetch stocks data in batches to respect API limits
        stocks = market_data["stocks"]
        all_stocks_data = {}
        
        # Process in batches of 5 to respect API rate limits
        for i in range(0, len(stocks), 5):
            batch = stocks[i:i+5]
            batch_stocks_processed = min(5, len(stocks) - i)
            stocks_processed += batch_stocks_processed
            total_progress = (stocks_processed / total_stocks) * 100
            
            logger.info(f"Fetching batch of stocks for {market_name}: {batch} ({stocks_processed}/{total_stocks}, {total_progress:.1f}% complete)")
            batch_data = fetch_stock_data(batch)
            
            # Add any failed tickers to the list
            for ticker in batch:
                if ticker not in batch_data:
                    all_failed_items["stocks"].append(ticker)
            
            all_stocks_data.update(batch_data)
            
            # Don't sleep after the last batch
            if i + 5 < len(stocks):
                time.sleep(60)  # Respect API rate limits - longer pause between batches
        
        # Save market stocks data
        market_stocks_name = f"stocks_{market_name.lower()}"
        save_data(all_stocks_data, market_stocks_name)
        time.sleep(5)  # Pause between markets
    
    # Forex pairs - top 3
    forex_pairs = [
        "EURUSD=X",  # Euro/US Dollar
        "GBPUSD=X",  # British Pound/US Dollar
        "USDJPY=X",  # US Dollar/Japanese Yen
    ]
    
    # Bond tickers - just 2 most important
    bonds = [
        "^TNX",    # 10-Year Treasury Yield
        "^TYX",    # 30-Year Treasury Yield
    ]
    
    # News queries - reduced to 4
    news_queries = [
        "stock market",
        "interest rates",
        "inflation",
        "federal reserve",
    ]
    
    # Google Trends keywords - reduced to 3
    trend_keywords = [
        "invest",
        "stock market",
        "bear market",
    ]
    
    # FRED series - just 3
    fred_series = [
        "UNRATE",    # Unemployment Rate
        "CPIAUCSL",  # Consumer Price Index
        "FEDFUNDS",  # Federal Funds Rate
    ]
    
    # Symbols for detailed analysis - select top stocks from each market
    analysis_symbols = []
    for market_data in markets.values():
        # Take first 2 stocks from each market for detailed analysis
        analysis_symbols.extend(market_data["stocks"][:2])
    
    # Remove duplicates while preserving order
    analysis_symbols = list(dict.fromkeys(analysis_symbols))
    
    if DEBUG_MODE:
        logger.debug(f"DEBUG: Selected {len(analysis_symbols)} stocks for detailed analysis: {analysis_symbols}")
    
    # Fetch remaining data types
    logger.info("Fetching forex data")
    forex_data = fetch_forex_data(forex_pairs)
    # Add any failed forex pairs to the list
    for pair in forex_pairs:
        if pair not in forex_data:
            all_failed_items["forex"].append(pair)
    time.sleep(3)
    
    logger.info("Fetching bond data")
    bond_data = fetch_bond_data(bonds)
    # Add any failed bonds to the list
    for bond in bonds:
        if bond not in bond_data:
            all_failed_items["bonds"].append(bond)
    time.sleep(3)
    
    logger.info("Fetching news data")
    news_data = fetch_news_data(news_queries)
    # Add any failed news queries to the list
    for query in news_queries:
        if query not in news_data or news_data[query].get("status") == "error":
            all_failed_items["news"].append(query)
    time.sleep(3)
    
    logger.info("Fetching trend data")
    trend_data = fetch_trend_data(trend_keywords)
    time.sleep(3)
    
    logger.info("Fetching FRED data")
    fred_data = fetch_fred_data(fred_series)
    # Add any failed FRED series to the list
    for series in fred_series:
        if series not in fred_data:
            all_failed_items["company_data"].append(f"FRED:{series}")
    time.sleep(3)
    
    # EODHD Sentiment data for all analysis symbols
    logger.info("Fetching EODHD sentiment data")
    eodhd_sentiment_data = fetch_eodhd_sentiment_data(analysis_symbols)
    # Add any failed sentiment symbols to the list
    for symbol in analysis_symbols:
        if symbol not in eodhd_sentiment_data or eodhd_sentiment_data[symbol].get("status") in ["error", "no_data"]:
            all_failed_items["sentiment"].append(symbol)
    time.sleep(3)
    
    # Alpha Vantage data (limited due to API limits)
    logger.info("Fetching Alpha Vantage data")
    alpha_symbols = analysis_symbols[:2]  # Just use first two symbols for Alpha Vantage
    alpha_data = fetch_alpha_vantage_data(alpha_symbols)
    time.sleep(3)
    
    # Process Finnhub data in smaller batches
    finnhub_quote_data = {}
    finnhub_company_data = {}
    finnhub_earnings_data = {}
    finnhub_insider_data = {}
    
    # Process in batches of 3 to respect Finnhub rate limits
    for i in range(0, len(analysis_symbols), 3):
        batch = analysis_symbols[i:i+3]
        
        logger.info(f"Fetching Finnhub quote data for batch: {batch}")
        batch_quotes = fetch_finnhub_quote_data(batch)
        finnhub_quote_data.update(batch_quotes)
        time.sleep(1)
        
        logger.info(f"Fetching Finnhub company data for batch: {batch}")
        batch_company = fetch_finnhub_company_data(batch)
        finnhub_company_data.update(batch_company)
        # Add any failed company data to the list
        for symbol in batch:
            if symbol not in batch_company or not batch_company[symbol]:
                all_failed_items["company_data"].append(f"Finnhub:{symbol}")
        time.sleep(1)
        
        logger.info(f"Fetching Finnhub earnings data for batch: {batch}")
        batch_earnings = fetch_finnhub_earnings_data(batch)
        finnhub_earnings_data.update(batch_earnings)
        time.sleep(1)
        
        logger.info(f"Fetching Finnhub insider data for batch: {batch}")
        batch_insider = fetch_finnhub_insider_data(batch)
        finnhub_insider_data.update(batch_insider)
        time.sleep(2)  # Slightly longer pause between batches
    
    # We don't use Finnhub sentiment data as it requires premium API access
    logger.info("Skipping Finnhub sentiment data (using EODHD sentiment instead)")
    finnhub_sentiment_data = {}  # Empty dictionary as placeholder
    
    # Save additional data
    logger.info("Saving additional collected data")
    save_data(forex_data, "forex")
    save_data(bond_data, "bonds")
    save_data(news_data, "news")
    save_data(trend_data, "trends")
    save_data(fred_data, "fred")
    save_data(alpha_data, "alpha_vantage")
    save_data(eodhd_sentiment_data, "eodhd_sentiment")
    
    # Save Finnhub data
    save_data(finnhub_quote_data, "finnhub_quotes")
    save_data(finnhub_company_data, "finnhub_company")
    save_data(finnhub_sentiment_data, "finnhub_sentiment")
    save_data(finnhub_earnings_data, "finnhub_earnings")
    save_data(finnhub_insider_data, "finnhub_insider")
    
    # Save failed items information
    failed_items_summary = {
        "date": TODAY,
        "total_failures": sum(len(items) for items in all_failed_items.values()),
        "failed_items": all_failed_items
    }
    save_data(failed_items_summary, "failed_items")
    
    # Print summary of failures
    total_failures = sum(len(items) for items in all_failed_items.values())
    if total_failures > 0:
        logger.warning(f"Data collection completed with {total_failures} failed items:")
        for category, items in all_failed_items.items():
            if items:
                logger.warning(f"  - Failed {category}: {len(items)} items")
        logger.info("See 'failed_items' file for details")
    else:
        logger.info("Market data collection completed successfully with no failures")


if __name__ == "__main__":
    import sys
    
    # Check for debug mode flag
    if len(sys.argv) > 1 and (sys.argv[1] == "--debug" or (len(sys.argv) > 2 and sys.argv[2] == "--debug")):
        # Enable debug mode
        DEBUG_MODE = True
        # Set logger level to DEBUG
        logger.setLevel(logging.DEBUG)
        # Add a console handler for more verbose output
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        # Remove existing handlers to avoid duplicate logs
        for handler in logger.handlers:
            logger.removeHandler(handler)
        logger.addHandler(console)
        # Also set root logger level
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        # Remove existing handlers to avoid duplicate logs
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)
        root_logger.addHandler(console)
        
        print("Running in DEBUG mode - fetching data with verbose output")
        print("Debugging info will be printed throughout execution")
    
    # Check for test mode
    if len(sys.argv) > 1 and (sys.argv[1] == "--test" or (len(sys.argv) > 2 and sys.argv[2] == "--test")):
        # Set console log level to INFO in test mode to see details of API calls
        if not DEBUG_MODE:
            console = logging.StreamHandler()
            console.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console.setFormatter(formatter)
            # Remove existing handlers to avoid duplicate logs
            for handler in logger.handlers:
                logger.removeHandler(handler)
            logger.addHandler(console)
            
            # Set root logger level
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.INFO)
            # Remove existing handlers to avoid duplicate logs
            for handler in root_logger.handlers:
                root_logger.removeHandler(handler)
            root_logger.addHandler(console)
        
        print("Running in test mode - fetching limited data")
        results = test_run()
        print("\nTest completed. Data counts:")
        for data_type, count in results.items():
            print(f"  - {data_type}: {count} items")
    else:
        if not DEBUG_MODE:
            print("Running in full mode - fetching all data")
        main()
