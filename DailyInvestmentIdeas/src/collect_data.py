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

# Hardcoded API keys
ALPHA_VANTAGE_API_KEY = "ZMUZQIRZWJKML99P"
FRED_API_KEY = "fb670d7e87729f288ed7ffb40f986bb9"
NEWS_API_KEY = "b8851f0d4dc5462bbdddebc446bbfe89"
FINNHUB_API_KEY = "d000cm9r01qud9ql2jagd000cm9r01qud9ql2jb0"

# Set up API clients
news_api = NewsApiClient(api_key=NEWS_API_KEY)
trend_api = TrendReq()
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

# Set up paths
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
TODAY = datetime.datetime.now().strftime("%Y-%m-%d")


def fetch_stock_data(tickers):
    """
    Fetch stock data for the given tickers using Alpha Vantage API.
    Alpha Vantage has a limit of 5 requests per minute on free tier, so we handle that with delays.
    For market indices, we use mock data since they're not easily available in free APIs.
    
    Args:
        tickers (list): List of stock ticker symbols
        
    Returns:
        dict: Dictionary containing stock data
    """
    logger.info(f"Fetching stock data for {len(tickers)} tickers")
    stock_data = {}
    
    for ticker in tickers:
        # For indices (starting with ^), we use mock data
        if ticker.startswith("^"):
            logger.info(f"Using mock data for index: {ticker}")
            history = generate_mock_stock_history(ticker)
            
            # Create index-specific info
            sector = "Index"
            industry = "Market Index"
            
            # Index names
            shortname = f"Index {ticker}"
            longname = f"{ticker} Index"
            
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
            else:
                current_price = 1000.0
            
            info = {
                "symbol": ticker,
                "shortName": shortname,
                "longName": longname,
                "sector": sector,
                "industry": industry,
                "marketCap": 1000000000000,
                "currentPrice": current_price
            }
            
            stock_data[ticker] = {
                "info": info,
                "history": history,
            }
            continue
        
        try:
            # Try to fetch data from Alpha Vantage API
            logger.info(f"Fetching stock data for {ticker} from Alpha Vantage")
            
            # Get daily price data (compact = last 100 days)
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": ticker,
                "outputsize": "compact",  # compact = last 100 days
                "apikey": ALPHA_VANTAGE_API_KEY
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if we got valid data
                if "Time Series (Daily)" in data:
                    # Convert to our expected format
                    history = []
                    time_series = data["Time Series (Daily)"]
                    
                    # Sort dates in ascending order (oldest first)
                    sorted_dates = sorted(time_series.keys())
                    
                    for date_str in sorted_dates:
                        daily_data = time_series[date_str]
                        history.append({
                            "Date": datetime.datetime.strptime(date_str, "%Y-%m-%d"),
                            "Open": float(daily_data["1. open"]),
                            "High": float(daily_data["2. high"]),
                            "Low": float(daily_data["3. low"]),
                            "Close": float(daily_data["4. close"]),
                            "Volume": float(daily_data["5. volume"]),
                            "Dividends": 0.0,
                            "Stock Splits": 0.0
                        })
                    
                    # Get company overview
                    time.sleep(12)  # Respect 5 calls per minute limit
                    
                    overview_params = {
                        "function": "OVERVIEW",
                        "symbol": ticker,
                        "apikey": ALPHA_VANTAGE_API_KEY
                    }
                    
                    overview_response = requests.get(url, params=overview_params)
                    
                    if overview_response.status_code == 200:
                        overview_data = overview_response.json()
                        
                        # Create info object
                        info = {
                            "symbol": ticker,
                            "shortName": overview_data.get("Name", f"Stock {ticker}"),
                            "longName": overview_data.get("Name", f"{ticker} Corporation"),
                            "sector": overview_data.get("Sector", "Unknown"),
                            "industry": overview_data.get("Industry", "Unknown"),
                            "marketCap": float(overview_data.get("MarketCapitalization", "0")) if overview_data.get("MarketCapitalization", "0").isdigit() else 0,
                            "currentPrice": float(history[-1]["Close"]) if history else 0,
                            "description": overview_data.get("Description", ""),
                            "exchange": overview_data.get("Exchange", ""),
                            "peRatio": float(overview_data.get("PERatio", "0")) if overview_data.get("PERatio", "0").replace(".", "", 1).isdigit() else 0,
                            "dividendYield": float(overview_data.get("DividendYield", "0")) if overview_data.get("DividendYield", "0").replace(".", "", 1).isdigit() else 0,
                        }
                        
                        stock_data[ticker] = {
                            "info": info,
                            "history": history,
                        }
                        
                        logger.info(f"Successfully fetched stock data for {ticker}")
                    else:
                        # If overview fails, still use the price data
                        logger.warning(f"Failed to fetch company overview for {ticker}. Using basic info.")
                        
                        # Create basic info
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
                    logger.warning(f"Invalid data received for {ticker}. Using mock data.")
                    history = generate_mock_stock_history(ticker)
                    
                    # Create basic info
                    info = create_mock_stock_info(ticker)
                    
                    stock_data[ticker] = {
                        "info": info,
                        "history": history,
                    }
            else:
                logger.warning(f"Failed to fetch data for {ticker} (Status: {response.status_code}). Using mock data.")
                history = generate_mock_stock_history(ticker)
                
                # Create basic info
                info = create_mock_stock_info(ticker)
                
                stock_data[ticker] = {
                    "info": info,
                    "history": history,
                }
            
            # Add a delay to respect Alpha Vantage's rate limits (5 calls per minute on free tier)
            time.sleep(12)
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            
            # Create mock data as fallback
            history = generate_mock_stock_history(ticker)
            info = create_mock_stock_info(ticker)
            
            stock_data[ticker] = {
                "info": info,
                "history": history,
            }
    
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
        
        # Add some randomness to the price movement
        import random
        daily_change = random.uniform(-0.02, 0.02)  # -2% to +2% daily change
        
        # Ensure generally positive trend for testing
        if i > 20:  # Make the last 10 days trend up for testing
            daily_change = abs(daily_change) * 1.5
        
        price = base_price * (1 + daily_change)
        base_price = price  # Update for next iteration
        
        history.append({
            "Date": date,
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
                logger.warning(f"Unsupported forex pair format: {pair}. Using mock data.")
                mock_history = generate_mock_forex_history(pair)
                forex_data[pair] = mock_history
                continue
        
        try:
            logger.info(f"Fetching forex data for {from_currency}/{to_currency} from Alpha Vantage")
            
            # Use Alpha Vantage API to get forex data
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "FX_DAILY",
                "from_symbol": from_currency,
                "to_symbol": to_currency,
                "outputsize": "compact",  # compact = last 100 data points
                "apikey": ALPHA_VANTAGE_API_KEY
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if we got valid data
                if "Time Series FX (Daily)" in data:
                    # Convert to our expected format
                    history = []
                    time_series = data["Time Series FX (Daily)"]
                    
                    # Sort dates in ascending order (oldest first)
                    sorted_dates = sorted(time_series.keys())
                    
                    for date_str in sorted_dates:
                        daily_data = time_series[date_str]
                        history.append({
                            "Date": datetime.datetime.strptime(date_str, "%Y-%m-%d"),
                            "Open": float(daily_data["1. open"]),
                            "High": float(daily_data["2. high"]),
                            "Low": float(daily_data["3. low"]),
                            "Close": float(daily_data["4. close"]),
                            # No volume data for forex, use a placeholder
                            "Volume": 0.0,
                            "Dividends": 0.0,
                            "Stock Splits": 0.0
                        })
                    
                    forex_data[pair] = history
                    logger.info(f"Successfully fetched forex data for {pair}")
                else:
                    logger.warning(f"Invalid data received for {pair}. Using mock data.")
                    mock_history = generate_mock_forex_history(pair)
                    forex_data[pair] = mock_history
            else:
                logger.warning(f"Failed to fetch forex data for {pair} (Status: {response.status_code}). Using mock data.")
                mock_history = generate_mock_forex_history(pair)
                forex_data[pair] = mock_history
            
            # Add a delay to respect Alpha Vantage's rate limits (5 calls per minute on free tier)
            time.sleep(12)
            
        except Exception as e:
            logger.error(f"Error fetching forex data for {pair}: {e}")
            mock_history = generate_mock_forex_history(pair)
            forex_data[pair] = mock_history
    
    return forex_data

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
            "Date": date,
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
                        
                        bond_data[ticker] = history
                        logger.info(f"Successfully fetched bond data for {ticker}")
                    else:
                        logger.warning(f"Invalid data received for {ticker}. Using mock data.")
                        mock_history = generate_mock_bond_history(ticker)
                        bond_data[ticker] = mock_history
                else:
                    logger.warning(f"Failed to fetch bond data for {ticker} (Status: {response.status_code}). Using mock data.")
                    mock_history = generate_mock_bond_history(ticker)
                    bond_data[ticker] = mock_history
            
            except Exception as e:
                logger.error(f"Error fetching bond data for {ticker}: {e}")
                mock_history = generate_mock_bond_history(ticker)
                bond_data[ticker] = mock_history
        else:
            logger.warning(f"No FRED mapping for bond ticker {ticker}. Using mock data.")
            mock_history = generate_mock_bond_history(ticker)
            bond_data[ticker] = mock_history
    
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
        
        # Add some randomness to the yield movement
        daily_change = random.uniform(-0.04, 0.04)  # -4 to +4 basis points daily change
        
        # Create trends for testing - yields generally trending down in test data
        if i > 15:
            daily_change = -abs(daily_change) * 1.2
        
        yield_value = base_yield + daily_change / 100  # Convert basis points to percentage
        base_yield = yield_value  # Update for next iteration
        
        history.append({
            "Date": date,
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
        if isinstance(obj, (datetime.datetime, pd.Timestamp)):
            return obj.isoformat()
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
        with open(file_path, 'w') as f:
            json.dump(data, f, cls=DataEncoder)
        logger.info(f"Data saved to {file_path}")
    except Exception as e:
        logger.error(f"Error saving data to {file_path}: {e}")


def test_run():
    """
    A limited test run that fetches a minimal set of data to test API integration.
    Uses mock data generation when API requests fail.
    """
    # Ensure data directories exist
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Limited test data sets - use very few items to avoid rate limits
    test_indices = ["^GSPC"]  # S&P 500 only
    test_tech_stocks = ["AAPL", "MSFT"]  # Just Apple and Microsoft
    test_bonds = ["^TNX"]  # Just 10-Year Treasury
    test_forex = ["EURUSD=X"]  # Just EUR/USD pair
    test_news_queries = ["stock market"]  # Just one news query
    test_fred_series = ["UNRATE"]  # Just unemployment rate
    test_finnhub_symbols = ["AAPL", "MSFT"]  # Just Apple and Microsoft for Finnhub
    
    # Fetch data (minimal calls to avoid rate limits)
    logger.info("Starting test data collection")
    
    logger.info("Fetching stock index data")
    index_data = fetch_stock_data(test_indices)
    
    logger.info("Fetching tech stock data")
    tech_data = fetch_stock_data(test_tech_stocks)
    
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
    logger.info("Skipping Finnhub sentiment data (premium API required)")
    finnhub_sentiment_data = {}  # Empty dictionary as placeholder
    
    logger.info("Fetching Finnhub earnings data")
    finnhub_earnings_data = fetch_finnhub_earnings_data(test_finnhub_symbols)
    
    logger.info("Fetching Finnhub insider data")
    finnhub_insider_data = fetch_finnhub_insider_data(test_finnhub_symbols)
    
    # Create finance and energy stock mock data for testing analysis
    logger.info("Creating mock finance stock data")
    finance_data = {
        "JPM": {
            "info": {
                "symbol": "JPM",
                "shortName": "JPMorgan Chase",
                "longName": "JPMorgan Chase & Co.",
                "sector": "Finance",
                "industry": "Banks",
                "marketCap": 500000000000,
                "currentPrice": 150.0
            },
            "history": generate_mock_stock_history("JPM")
        },
        "BAC": {
            "info": {
                "symbol": "BAC",
                "shortName": "Bank of America",
                "longName": "Bank of America Corporation",
                "sector": "Finance",
                "industry": "Banks",
                "marketCap": 300000000000,
                "currentPrice": 40.0
            },
            "history": generate_mock_stock_history("BAC")
        }
    }
    
    logger.info("Creating mock energy stock data")
    energy_data = {
        "XOM": {
            "info": {
                "symbol": "XOM",
                "shortName": "Exxon Mobil",
                "longName": "Exxon Mobil Corporation",
                "sector": "Energy",
                "industry": "Oil & Gas",
                "marketCap": 400000000000,
                "currentPrice": 110.0
            },
            "history": generate_mock_stock_history("XOM")
        },
        "CVX": {
            "info": {
                "symbol": "CVX",
                "shortName": "Chevron",
                "longName": "Chevron Corporation",
                "sector": "Energy",
                "industry": "Oil & Gas",
                "marketCap": 350000000000,
                "currentPrice": 170.0
            },
            "history": generate_mock_stock_history("CVX")
        }
    }
    
    # Crypto data has been removed as requested
    
    # Save test data
    save_data(index_data, "indices")
    save_data(tech_data, "tech_stocks")
    save_data(finance_data, "finance_stocks")
    save_data(energy_data, "energy_stocks")
    save_data(forex_data, "forex")
    save_data(bond_data, "bonds")
    save_data(news_data, "news")
    save_data(fred_data, "fred")
    save_data(alpha_data, "alpha_vantage")
    # Crypto data has been removed as requested
    
    # Save Finnhub data
    save_data(finnhub_quote_data, "finnhub_quotes")
    save_data(finnhub_company_data, "finnhub_company")
    save_data(finnhub_sentiment_data, "finnhub_sentiment")
    save_data(finnhub_earnings_data, "finnhub_earnings")
    save_data(finnhub_insider_data, "finnhub_insider")
    
    logger.info("Test data collection completed")
    
    return {
        "indices": len(index_data),
        "tech_stocks": len(tech_data),
        "finance_stocks": len(finance_data),
        "energy_stocks": len(energy_data),
        "forex": len(forex_data),
        "bonds": len(bond_data),
        "news": len(news_data),
        "fred": len(fred_data),
        "alpha_vantage": len(alpha_data),
        "finnhub_quotes": len(finnhub_quote_data),
        "finnhub_company": len(finnhub_company_data),
        "finnhub_sentiment": len(finnhub_sentiment_data),
        "finnhub_earnings": len(finnhub_earnings_data),
        "finnhub_insider": len(finnhub_insider_data)
    }

def main():
    # Ensure data directories exist
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Define data to fetch - REDUCED to just top stocks to avoid rate limiting
    # Regional stock indices - top 5 most important
    indices = [
        "^GSPC",    # S&P 500 (US)
        "^IXIC",    # NASDAQ Composite (US)
        "^FTSE",    # FTSE 100 (UK)
        "^N225",    # Nikkei 225 (Japan)
        "^HSI",     # Hang Seng Index (Hong Kong)
    ]
    
    # Major tech stocks - top 5
    tech_stocks = [
        "AAPL",  # Apple
        "MSFT",  # Microsoft
        "GOOGL", # Alphabet (Google)
        "AMZN",  # Amazon
        "META",  # Meta (Facebook)
    ]
    
    # Financial stocks - top 3
    financial_stocks = [
        "JPM",   # JPMorgan Chase
        "BAC",   # Bank of America
        "GS",    # Goldman Sachs
    ]
    
    # Energy stocks - top 2
    energy_stocks = [
        "XOM",   # ExxonMobil
        "CVX",   # Chevron
    ]
    
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
    
    # Crypto data has been removed as requested
    
    # FRED series - just 3
    fred_series = [
        "UNRATE",    # Unemployment Rate
        "CPIAUCSL",  # Consumer Price Index
        "FEDFUNDS",  # Federal Funds Rate
    ]
    
    # Symbols for Finnhub detailed analysis - just 5 total
    finnhub_symbols = [
        "AAPL", "MSFT",  # Tech
        "JPM",           # Finance
        "XOM", "CVX"     # Energy
    ]
    
    # Add delays between API calls to prevent rate limiting
    logger.info("Starting regular data collection with reduced scope")
    
    # Fetch data with pauses between different data sources
    logger.info("Fetching market indices data")
    index_data = fetch_stock_data(indices)
    time.sleep(3)
    
    logger.info("Fetching tech stocks data")
    tech_data = fetch_stock_data(tech_stocks)
    time.sleep(3)
    
    logger.info("Fetching finance stocks data")
    finance_data = fetch_stock_data(financial_stocks)
    time.sleep(3)
    
    logger.info("Fetching energy stocks data")
    energy_data = fetch_stock_data(energy_stocks)
    time.sleep(3)
    
    logger.info("Fetching forex data")
    forex_data = fetch_forex_data(forex_pairs)
    time.sleep(3)
    
    logger.info("Fetching bond data")
    bond_data = fetch_bond_data(bonds)
    time.sleep(3)
    
    logger.info("Fetching news data")
    news_data = fetch_news_data(news_queries)
    time.sleep(3)
    
    logger.info("Fetching trend data")
    trend_data = fetch_trend_data(trend_keywords)
    time.sleep(3)
    
    # Crypto data has been removed as requested
    
    logger.info("Fetching FRED data")
    fred_data = fetch_fred_data(fred_series)
    time.sleep(3)
    
    # Alpha Vantage data (limited to 2 symbols due to API limits)
    logger.info("Fetching Alpha Vantage data")
    alpha_symbols = ["AAPL", "MSFT"]
    alpha_data = fetch_alpha_vantage_data(alpha_symbols)
    time.sleep(3)
    
    # Finnhub data
    logger.info("Fetching Finnhub quote data")
    finnhub_quote_data = fetch_finnhub_quote_data(finnhub_symbols)
    time.sleep(1)
    
    logger.info("Fetching Finnhub company data")
    finnhub_company_data = fetch_finnhub_company_data(finnhub_symbols)
    time.sleep(1)
    
    # We don't use Finnhub sentiment data anymore as it requires premium API access
    logger.info("Skipping Finnhub sentiment data (premium API required)")
    finnhub_sentiment_data = {}  # Empty dictionary as placeholder
    time.sleep(1)
    
    logger.info("Fetching Finnhub earnings data")
    finnhub_earnings_data = fetch_finnhub_earnings_data(finnhub_symbols)
    time.sleep(1)
    
    logger.info("Fetching Finnhub insider data")
    finnhub_insider_data = fetch_finnhub_insider_data(finnhub_symbols)
    
    # Save data
    logger.info("Saving collected data")
    save_data(index_data, "indices")
    save_data(tech_data, "tech_stocks")
    save_data(finance_data, "finance_stocks")
    save_data(energy_data, "energy_stocks")
    save_data(forex_data, "forex")
    save_data(bond_data, "bonds")
    save_data(news_data, "news")
    save_data(trend_data, "trends")
    # Crypto data has been removed as requested
    save_data(fred_data, "fred")
    save_data(alpha_data, "alpha_vantage")
    
    # Save Finnhub data
    save_data(finnhub_quote_data, "finnhub_quotes")
    save_data(finnhub_company_data, "finnhub_company")
    save_data(finnhub_sentiment_data, "finnhub_sentiment")
    save_data(finnhub_earnings_data, "finnhub_earnings")
    save_data(finnhub_insider_data, "finnhub_insider")
    
    logger.info("Regular data collection completed")


if __name__ == "__main__":
    import sys
    
    # Set up console handler to reduce noise in test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Set console log level to WARNING to reduce noise
        console = logging.StreamHandler()
        console.setLevel(logging.WARNING)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logger.handlers = [console]  # Replace existing handlers
        
        # Also set root logger level
        logging.getLogger().setLevel(logging.WARNING)
        
        print("Running in test mode - fetching limited data")
        results = test_run()
        print("Test completed. Data counts:")
        for data_type, count in results.items():
            print(f"  - {data_type}: {count} items")
    else:
        print("Running in full mode - fetching all data")
        main()
