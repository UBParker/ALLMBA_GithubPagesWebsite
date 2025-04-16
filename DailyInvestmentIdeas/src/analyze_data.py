#!/usr/bin/env python3
"""
Data Analysis Script

This script analyzes collected financial data and generates investment ideas
based on market trends, technical indicators, news sentiment, and other factors.
"""

import os
import json
import datetime
import logging
from pathlib import Path
from dotenv import load_dotenv

# Data processing
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler
from textblob import TextBlob

# NLP for sentiment analysis
import nltk
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

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

# Set up paths
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
TODAY = datetime.datetime.now().strftime("%Y-%m-%d")

class DataAnalyzer:
    def __init__(self):
        self.data = {}
        self.markets = {}  # Store market data organized by market name
        self.ideas = []
        self.trends = {}
        self.sentiment = {}
    
    def load_data(self):
        """
        Load collected data from raw data directory, organizing by market.
        """
        logger.info("Loading raw data")
        
        # Load market data
        self.markets = {}
        
        # Get market names from the configured markets
        market_names = ["S&P500", "NASDAQ", "FTSE100"]
        
        # Load data for each market
        for market_name in market_names:
            market_name_lower = market_name.lower()
            
            # Find and load index data
            index_pattern = f"index_{market_name_lower}_*.json"
            index_files = sorted(RAW_DATA_DIR.glob(index_pattern), reverse=True)
            
            # Find and load stocks data
            stocks_pattern = f"stocks_{market_name_lower}_*.json"
            stocks_files = sorted(RAW_DATA_DIR.glob(stocks_pattern), reverse=True)
            
            if index_files and stocks_files:
                try:
                    # Load index data
                    with open(index_files[0], 'r') as f:
                        index_data = json.load(f)
                    
                    # Load stocks data
                    with open(stocks_files[0], 'r') as f:
                        stocks_data = json.load(f)
                    
                    # Store in markets dictionary
                    self.markets[market_name] = {
                        "index": index_data,
                        "stocks": stocks_data,
                        "index_file": index_files[0].name,
                        "stocks_file": stocks_files[0].name
                    }
                    
                    if DEBUG_MODE:
                        logger.debug(f"DEBUG: Loaded market data for {market_name}")
                        logger.debug(f"DEBUG:   Index: {list(index_data.keys())}")
                        logger.debug(f"DEBUG:   Stocks: {len(stocks_data)} stocks loaded")
                        
                        # Show top 5 stocks to verify data
                        stock_names = list(stocks_data.keys())[:5]
                        logger.debug(f"DEBUG:   Sample stocks: {stock_names}")
                except Exception as e:
                    logger.error(f"Error loading market data for {market_name}: {e}")
            else:
                if DEBUG_MODE:
                    if not index_files:
                        logger.warning(f"DEBUG: No index data files found for {market_name}")
                    if not stocks_files:
                        logger.warning(f"DEBUG: No stocks data files found for {market_name}")
        
        if not self.markets:
            logger.warning("No market data found. Falling back to legacy data format.")
            
            # Fall back to legacy format for backward compatibility
            legacy_data_types = ["indices", "tech_stocks", "finance_stocks", "energy_stocks"]
            
            for file_type in legacy_data_types:
                pattern = f"{file_type}_*.json"
                files = sorted(RAW_DATA_DIR.glob(pattern), reverse=True)
                
                if files:
                    latest_file = files[0]
                    try:
                        with open(latest_file, 'r') as f:
                            data = json.load(f)
                            self.data[file_type] = data
                        
                        logger.debug(f"Loaded legacy data type: {file_type}")
                    except Exception as e:
                        logger.error(f"Error loading {latest_file}: {e}")
        
        # Load other data types (unchanged)
        other_data_types = [
            "forex", "bonds", "news", "trends", "crypto", "fred", "alpha_vantage",
            "finnhub_quotes", "finnhub_company", "finnhub_sentiment", 
            "finnhub_earnings", "finnhub_insider"
        ]
        
        for file_type in other_data_types:
            pattern = f"{file_type}_*.json"
            files = sorted(RAW_DATA_DIR.glob(pattern), reverse=True)
            
            if files:
                latest_file = files[0]
                try:
                    with open(latest_file, 'r') as f:
                        data = json.load(f)
                        self.data[file_type] = data
                    
                    if DEBUG_MODE:
                        logger.debug(f"DEBUG: Loaded {latest_file}")
                        # Check data content
                        if isinstance(data, dict):
                            logger.debug(f"DEBUG: {file_type} contains {len(data)} items")
                            if len(data) == 0:
                                logger.warning(f"DEBUG: Empty dictionary loaded from {latest_file}")
                            else:
                                # Show some sample data keys
                                sample_keys = list(data.keys())[:3]
                                logger.debug(f"DEBUG: Sample keys: {sample_keys}")
                        elif isinstance(data, list):
                            logger.debug(f"DEBUG: {file_type} contains {len(data)} list items")
                            if len(data) == 0:
                                logger.warning(f"DEBUG: Empty list loaded from {latest_file}")
                    else:
                        logger.debug(f"Loaded {latest_file}")
                except Exception as e:
                    logger.error(f"Error loading {latest_file}: {e}")
            else:
                logger.warning(f"No {file_type} data files found")
    
    def analyze_stock_performance(self, stock_data, period=7):
        """
        Analyze stock performance over a given period.
        
        Args:
            stock_data (dict): Dictionary of stock data
            period (int): Analysis period in days
            
        Returns:
            dict: Performance metrics
        """
        performance = {}
        
        for ticker, data in stock_data.items():
            if 'history' not in data or not data['history']:
                continue
                
            try:
                # Convert to DataFrame
                df = pd.DataFrame(data['history'])
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                df.sort_index(inplace=True)
                
                # Get recent data
                recent = df.tail(period)
                if len(recent) < period:
                    continue
                    
                # Calculate metrics
                start_price = recent['Close'].iloc[0]
                end_price = recent['Close'].iloc[-1]
                max_price = recent['High'].max()
                min_price = recent['Low'].min()
                
                # Return metrics
                performance[ticker] = {
                    "return": (end_price - start_price) / start_price * 100,
                    "volatility": recent['Close'].pct_change().std() * 100,
                    "max_drawdown": ((recent['Close'].cummax() - recent['Close']) / recent['Close'].cummax()).max() * 100,
                    "volume_change": (recent['Volume'].iloc[-1] / recent['Volume'].iloc[0] - 1) * 100,
                    "avg_volume": recent['Volume'].mean(),
                    "latest_close": end_price,
                    "is_uptrend": end_price > start_price,
                }
                logger.debug(f"Analyzed performance for {ticker}")
            except Exception as e:
                logger.error(f"Error analyzing {ticker}: {e}")
        
        return performance
    
    def analyze_news_sentiment(self, news_data):
        """
        Analyze sentiment from news articles.
        
        Args:
            news_data (dict): Dictionary of news data
            
        Returns:
            dict: Sentiment scores by topic
        """
        sentiment = {}
        
        for topic, data in news_data.items():
            if 'articles' not in data or not data['articles']:
                continue
                
            try:
                articles = data['articles']
                scores = []
                
                for article in articles:
                    if not article.get('title') and not article.get('description'):
                        continue
                        
                    text = f"{article.get('title', '')} {article.get('description', '')}"
                    blob = TextBlob(text)
                    scores.append(blob.sentiment.polarity)
                
                if scores:
                    sentiment[topic] = {
                        "avg_sentiment": sum(scores) / len(scores),
                        "sentiment_std": np.std(scores) if len(scores) > 1 else 0,
                        "article_count": len(scores),
                    }
                    logger.debug(f"Analyzed sentiment for {topic}")
            except Exception as e:
                logger.error(f"Error analyzing sentiment for {topic}: {e}")
        
        return sentiment
    
    def analyze_technical_indicators(self, stock_data):
        """
        Calculate technical indicators for stocks.
        
        Args:
            stock_data (dict): Dictionary of stock data
            
        Returns:
            dict: Technical indicators by ticker
        """
        indicators = {}
        
        for ticker, data in stock_data.items():
            if 'history' not in data or not data['history']:
                continue
                
            try:
                # Convert to DataFrame
                df = pd.DataFrame(data['history'])
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                df.sort_index(inplace=True)
                
                if len(df) < 20:  # Need enough data for indicators
                    continue
                
                # Calculate indicators
                # Moving averages
                df['SMA20'] = df['Close'].rolling(window=20).mean()
                df['SMA50'] = df['Close'].rolling(window=50).mean()
                
                # RSI (Relative Strength Index)
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['RSI'] = 100 - (100 / (1 + rs))
                
                # MACD (Moving Average Convergence Divergence)
                df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
                df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
                df['MACD'] = df['EMA12'] - df['EMA26']
                df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
                
                # Bollinger Bands
                df['Middle Band'] = df['Close'].rolling(window=20).mean()
                df['Std Dev'] = df['Close'].rolling(window=20).std()
                df['Upper Band'] = df['Middle Band'] + (df['Std Dev'] * 2)
                df['Lower Band'] = df['Middle Band'] - (df['Std Dev'] * 2)
                
                # Get the latest values
                latest = df.iloc[-1]
                
                indicators[ticker] = {
                    "price_vs_sma20": (latest['Close'] / latest['SMA20'] - 1) * 100 if pd.notna(latest['SMA20']) else None,
                    "price_vs_sma50": (latest['Close'] / latest['SMA50'] - 1) * 100 if pd.notna(latest['SMA50']) else None,
                    "rsi": latest['RSI'] if pd.notna(latest['RSI']) else None,
                    "macd": latest['MACD'] if pd.notna(latest['MACD']) else None,
                    "macd_signal": latest['Signal'] if pd.notna(latest['Signal']) else None,
                    "bb_position": (latest['Close'] - latest['Lower Band']) / (latest['Upper Band'] - latest['Lower Band']) if pd.notna(latest['Upper Band']) and pd.notna(latest['Lower Band']) else None,
                }
                logger.debug(f"Calculated technical indicators for {ticker}")
            except Exception as e:
                logger.error(f"Error calculating indicators for {ticker}: {e}")
        
        return indicators
        
    def analyze_finnhub_data(self):
        """
        Analyze data from Finnhub for additional insights.
        
        Returns:
            dict: Analyzed Finnhub data by ticker
        """
        logger.info("Analyzing Finnhub data")
        finnhub_analysis = {}
        
        # Check if we have all the required Finnhub data
        required_data = ['finnhub_quotes', 'finnhub_sentiment', 'finnhub_earnings', 'finnhub_insider']
        if not all(data_type in self.data for data_type in required_data):
            missing_data = [data_type for data_type in required_data if data_type not in self.data]
            logger.warning(f"Missing some Finnhub data: {missing_data}")
            
            if DEBUG_MODE:
                logger.debug(f"DEBUG: Available Finnhub data: {[data_type for data_type in required_data if data_type in self.data]}")
                for data_type in self.data:
                    if data_type.startswith('finnhub_'):
                        logger.debug(f"DEBUG: {data_type} contains {len(self.data[data_type])} items")
            
            return finnhub_analysis
            
        # Process each stock with Finnhub data
        tickers = set(self.data['finnhub_quotes'].keys())
        
        for ticker in tickers:
            try:
                analysis = {}
                
                # Quote data
                if ticker in self.data['finnhub_quotes']:
                    quote = self.data['finnhub_quotes'][ticker]
                    price_change = quote.get('dp', 0)  # Daily percentage change
                    price = quote.get('c', 0)  # Current price
                    previous_close = quote.get('pc', 0)  # Previous close
                    
                    analysis['quote'] = {
                        'price': price,
                        'price_change': price_change,
                        'previous_close': previous_close
                    }
                
                # Sentiment data
                if ticker in self.data['finnhub_sentiment']:
                    sentiment = self.data['finnhub_sentiment'][ticker]
                    news_score = sentiment.get('sentiment', {}).get('newsScore', 0)
                    buzz = sentiment.get('buzz', {}).get('buzz', 0)
                    sentiment_change = sentiment.get('sentiment', {}).get('sentimentChange', 0)
                    
                    analysis['sentiment'] = {
                        'news_score': news_score,
                        'buzz': buzz,
                        'sentiment_change': sentiment_change
                    }
                
                # Earnings data
                if ticker in self.data['finnhub_earnings']:
                    earnings = self.data['finnhub_earnings'][ticker]
                    upcoming_earnings = None
                    latest_earnings = None
                    
                    if earnings and isinstance(earnings, list) and len(earnings) > 0:
                        for report in earnings:
                            if report.get('period') and datetime.datetime.strptime(report.get('period'), '%Y-%m-%d') > datetime.datetime.now():
                                upcoming_earnings = report
                                break
                        
                        if len(earnings) > 0:
                            latest_earnings = earnings[0]
                    
                    if upcoming_earnings:
                        analysis['upcoming_earnings'] = {
                            'date': upcoming_earnings.get('period'),
                            'estimate': upcoming_earnings.get('estimate')
                        }
                    
                    if latest_earnings:
                        surprise = latest_earnings.get('surprise', 0)
                        surprise_pct = latest_earnings.get('surprisePercent', 0)
                        
                        analysis['latest_earnings'] = {
                            'date': latest_earnings.get('period'),
                            'actual': latest_earnings.get('actual'),
                            'estimate': latest_earnings.get('estimate'),
                            'surprise': surprise,
                            'surprise_pct': surprise_pct
                        }
                
                # Insider trading data
                if ticker in self.data['finnhub_insider']:
                    insider = self.data['finnhub_insider'][ticker]
                    transactions = insider.get('data', [])
                    
                    if transactions and isinstance(transactions, list):
                        # Count buys and sells
                        buys = 0
                        sells = 0
                        buy_volume = 0
                        sell_volume = 0
                        
                        for tx in transactions:
                            if tx.get('change') > 0:
                                buys += 1
                                buy_volume += tx.get('change', 0)
                            elif tx.get('change') < 0:
                                sells += 1
                                sell_volume += abs(tx.get('change', 0))
                        
                        analysis['insider'] = {
                            'buy_count': buys,
                            'sell_count': sells,
                            'buy_volume': buy_volume,
                            'sell_volume': sell_volume,
                            'net_transactions': buys - sells,
                            'net_volume': buy_volume - sell_volume
                        }
                
                # Calculate an overall Finnhub score
                score = 0
                score_components = 0
                
                if 'sentiment' in analysis:
                    sentiment_score = analysis['sentiment']['news_score'] * 10  # Scale to 0-10
                    sentiment_weight = min(1.0, analysis['sentiment']['buzz'] / 1.0)  # Weight by buzz, max 1.0
                    score += sentiment_score * sentiment_weight
                    score_components += 1
                
                if 'latest_earnings' in analysis and analysis['latest_earnings'].get('surprise_pct') is not None:
                    earnings_score = min(10, max(-10, analysis['latest_earnings']['surprise_pct']))  # Scale to -10 to 10
                    score += earnings_score
                    score_components += 1
                
                if 'insider' in analysis:
                    # Positive if more buys than sells
                    net_tx = analysis['insider']['net_transactions']
                    insider_score = min(10, max(-10, net_tx * 2))  # Scale to -10 to 10
                    score += insider_score
                    score_components += 1
                
                if score_components > 0:
                    analysis['finnhub_score'] = score / score_components
                else:
                    analysis['finnhub_score'] = 0
                
                finnhub_analysis[ticker] = analysis
                logger.debug(f"Analyzed Finnhub data for {ticker}")
                
            except Exception as e:
                logger.error(f"Error analyzing Finnhub data for {ticker}: {e}")
        
        return finnhub_analysis
    
    def analyze_market(self, market_name):
        """
        Analyze a specific market (index + constituent stocks).
        
        Args:
            market_name (str): The name of the market to analyze
            
        Returns:
            dict: Market analysis results
        """
        if market_name not in self.markets:
            if DEBUG_MODE:
                logger.warning(f"DEBUG: Market {market_name} not found in available markets")
            return None
        
        market_data = self.markets[market_name]
        index_data = market_data["index"]  # Get the index data
        stocks_data = market_data["stocks"]
        
        if DEBUG_MODE:
            logger.debug(f"DEBUG: Analyzing market: {market_name}")
            logger.debug(f"DEBUG: Index ticker: {list(index_data.keys())[0]}")
            logger.debug(f"DEBUG: Number of stocks: {len(stocks_data)}")
        
        # Analyze index performance
        index_perf = self.analyze_stock_performance(index_data)
        if not index_perf:
            logger.warning(f"Failed to analyze index performance for {market_name}")
            return None
        
        # Analyze stocks performance
        stocks_perf = self.analyze_stock_performance(stocks_data)
        
        # Calculate technical indicators
        stocks_tech = self.analyze_technical_indicators(stocks_data)
        
        # Identify top performers in the market
        if stocks_perf:
            # Sort stocks by return
            sorted_stocks = sorted(
                [(ticker, data) for ticker, data in stocks_perf.items()],
                key=lambda x: x[1].get("return", 0),
                reverse=True
            )
            
            # Get top 5 performers
            top_performers = sorted_stocks[:5]
            
            # Get bottom 5 performers
            bottom_performers = sorted_stocks[-5:] if len(sorted_stocks) >= 5 else []
            
            # Calculate sector distribution of top performers
            sectors = {}
            for ticker, _ in top_performers:
                if ticker in stocks_data:
                    sector = stocks_data[ticker].get("info", {}).get("sector", "Unknown")
                    sectors[sector] = sectors.get(sector, 0) + 1
            
            # Find dominant sector
            dominant_sector = max(sectors.items(), key=lambda x: x[1])[0] if sectors else "Unknown"
            
            if DEBUG_MODE:
                logger.debug(f"DEBUG: Market {market_name} analysis complete")
                logger.debug(f"DEBUG: Top performers: {[t[0] for t in top_performers]}")
                logger.debug(f"DEBUG: Dominant sector: {dominant_sector}")
            
            return {
                "name": market_name,
                "index_performance": index_perf,
                "top_performers": top_performers,
                "bottom_performers": bottom_performers,
                "dominant_sector": dominant_sector,
                "stocks_performance": stocks_perf,
                "technical_indicators": stocks_tech
            }
        
        return None

    def generate_investment_ideas(self):
        """
        Generate investment ideas based on analyzed data.
        """
        logger.info("Generating investment ideas")
        if DEBUG_MODE:
            logger.debug("DEBUG: Starting investment idea generation")
            logger.debug(f"DEBUG: Available markets: {list(self.markets.keys())}")
            logger.debug(f"DEBUG: Available other data types: {list(self.data.keys())}")
        ideas = []
        
        # Analyze each market
        market_analyses = {}
        for market_name in self.markets.keys():
            analysis = self.analyze_market(market_name)
            if analysis:
                market_analyses[market_name] = analysis
        
        if DEBUG_MODE:
            logger.debug(f"DEBUG: Completed analysis for {len(market_analyses)} markets")
        
        # Generate market-specific ideas
        for market_name, analysis in market_analyses.items():
            # Market overview idea
            index_ticker = list(self.markets[market_name]["index"].keys())[0]
            index_perf = analysis["index_performance"].get(index_ticker, {})
            
            # Only add if we have valid performance data
            if "return" in index_perf:
                ideas.append({
                    "title": f"{market_name} Market Overview",
                    "type": "Market Analysis",
                    "asset": index_ticker,
                    "market": market_name,
                    "rationale": f"The {market_name} index has shown a {index_perf.get('return', 0):.2f}% return over the past week. The dominant sector among top performers is {analysis['dominant_sector']}.",
                    "risk_level": "Medium",
                    "time_horizon": "Medium-term",
                    "metrics": {
                        "return": index_perf.get("return", 0),
                        "volatility": index_perf.get("volatility", 0),
                    }
                })
            
            # Top performer idea
            if analysis["top_performers"]:
                top_ticker, top_data = analysis["top_performers"][0]
                ticker_data = self.markets[market_name]["stocks"].get(top_ticker, {})
                sector = ticker_data.get("info", {}).get("sector", "Unknown")
                
                # Add technical indicator data
                tech_indicators = analysis["technical_indicators"].get(top_ticker, {})
                rsi_value = tech_indicators.get("rsi", "N/A")
                rsi_str = f"{rsi_value:.1f}" if isinstance(rsi_value, (int, float)) else "N/A"
                macd = tech_indicators.get("macd", "N/A")
                
                tech_description = f" Technical indicators are supportive"
                if isinstance(rsi_value, (int, float)):
                    tech_description += f" with RSI at {rsi_str}"
                    if rsi_value < 30:
                        tech_description += " (oversold)"
                    elif rsi_value > 70:
                        tech_description += " (overbought)"
                tech_description += "."
                
                # Add the idea
                ideas.append({
                    "title": f"Top {market_name} Performer: {top_ticker}",
                    "type": "Stock",
                    "asset": top_ticker,
                    "sector": sector,
                    "market": market_name,
                    "rationale": f"{top_ticker} is the top performer in the {market_name} market with a {top_data.get('return', 0):.2f}% return over the past week.{tech_description}",
                    "risk_level": "Medium-High",
                    "time_horizon": "Short-term to Medium-term",
                    "metrics": {
                        "return": top_data.get("return", 0),
                        "volatility": top_data.get("volatility", 0),
                        "rsi": rsi_value if isinstance(rsi_value, (int, float)) else None,
                    }
                })
            
            # Sector rotation idea if we have dominant sectors
            if analysis["dominant_sector"] != "Unknown":
                # Get all stocks in the dominant sector
                sector_stocks = []
                for ticker, stock_data in self.markets[market_name]["stocks"].items():
                    sector = stock_data.get("info", {}).get("sector", "Unknown")
                    if sector == analysis["dominant_sector"]:
                        # Get performance data if available
                        if ticker in analysis["stocks_performance"]:
                            perf = analysis["stocks_performance"][ticker]
                            sector_stocks.append((ticker, perf))
                
                # Sort sector stocks by performance
                sector_stocks.sort(key=lambda x: x[1].get("return", 0), reverse=True)
                
                # List top 3 stocks in the sector
                top_sector_stocks = sector_stocks[:3]
                sector_stock_list = ", ".join([s[0] for s in top_sector_stocks])
                
                # Add the sector idea
                ideas.append({
                    "title": f"{analysis['dominant_sector']} Sector Strength in {market_name}",
                    "type": "Sector",
                    "asset": analysis["dominant_sector"],
                    "market": market_name,
                    "rationale": f"The {analysis['dominant_sector']} sector is showing strength in the {market_name} market, with multiple stocks among the top performers. Top {analysis['dominant_sector']} stocks include {sector_stock_list}.",
                    "risk_level": "Medium",
                    "time_horizon": "Medium-term",
                    "metrics": {
                        "stocks_count": len(sector_stocks),
                        "avg_return": sum(s[1].get("return", 0) for s in sector_stocks) / len(sector_stocks) if sector_stocks else 0,
                    }
                })
        
        # Analyze Finnhub data for additional insights
        finnhub_analysis = self.analyze_finnhub_data()
        
        # Generate Finnhub-specific ideas (keeping this part from the original)
        if finnhub_analysis:
            # Find stock with highest Finnhub score
            high_score_stocks = {ticker: data for ticker, data in finnhub_analysis.items() 
                              if 'finnhub_score' in data and data['finnhub_score'] > 5}
            
            if high_score_stocks:
                best_finnhub_stock = max(high_score_stocks.items(), key=lambda x: x[1]['finnhub_score'])
                ticker, fh_data = best_finnhub_stock
                
                # Check if this stock hasn't already been featured
                if not any(idea["asset"] == ticker for idea in ideas):
                    # Determine the rationale based on Finnhub data
                    rationale = f"{ticker} shows positive signals based on alternative data analysis."
                    
                    if 'sentiment' in fh_data and fh_data['sentiment']['news_score'] > 0.5:
                        rationale += f" Strong positive news sentiment ({fh_data['sentiment']['news_score']:.2f}/1.0)."
                    
                    if 'insider' in fh_data and fh_data['insider']['net_transactions'] > 0:
                        rationale += f" Insider buying detected with {fh_data['insider']['buy_count']} recent purchases."
                    
                    if 'latest_earnings' in fh_data and fh_data['latest_earnings'].get('surprise_pct', 0) > 0:
                        surprise = fh_data['latest_earnings']['surprise_pct']
                        rationale += f" Recent earnings beat expectations by {surprise:.2f}%."
                    
                    if 'upcoming_earnings' in fh_data:
                        earnings_date = fh_data['upcoming_earnings']['date']
                        rationale += f" Upcoming earnings report on {earnings_date}."
                    
                    # Add the Finnhub-based idea
                    ideas.append({
                        "title": f"Alternative Data Pick: {ticker}",
                        "type": "Stock",
                        "asset": ticker,
                        "rationale": rationale,
                        "risk_level": "Medium-High",
                        "time_horizon": "Medium-term",
                        "metrics": {
                            "finnhub_score": fh_data.get('finnhub_score'),
                            "sentiment": fh_data.get('sentiment', {}).get('news_score') if 'sentiment' in fh_data else None,
                            "insider_buys": fh_data.get('insider', {}).get('buy_count') if 'insider' in fh_data else None,
                            "earnings_surprise": fh_data.get('latest_earnings', {}).get('surprise_pct') if 'latest_earnings' in fh_data else None,
                        }
                    })
            
            # Find stocks with significant insider buying
            insider_stocks = {ticker: data for ticker, data in finnhub_analysis.items() 
                           if 'insider' in data and data['insider']['net_transactions'] > 2}
            
            if insider_stocks and not any(idea["title"].startswith("Insider Activity") for idea in ideas):
                # Get the stock with most net insider buys
                best_insider_stock = max(insider_stocks.items(), key=lambda x: x[1]['insider']['net_transactions'])
                ticker, insider_data = best_insider_stock
                
                # Add insider activity idea
                ideas.append({
                    "title": f"Insider Activity: {ticker}",
                    "type": "Stock",
                    "asset": ticker,
                    "rationale": f"Strong insider buying detected in {ticker} with {insider_data['insider']['buy_count']} purchases versus {insider_data['insider']['sell_count']} sales over the past 3 months. Insider buying often signals management's confidence in future prospects.",
                    "risk_level": "Medium",
                    "time_horizon": "Medium-term to Long-term",
                    "metrics": {
                        "net_buys": insider_data['insider']['net_transactions'],
                        "buy_volume": insider_data['insider']['buy_volume'],
                        "sell_volume": insider_data['insider']['sell_volume'],
                    }
                })
        
        # Process forex data
        if "forex" in self.data:
            forex_perf = self.analyze_stock_performance(self.data["forex"])
            
            if forex_perf:
                strongest_pair = max(forex_perf.items(), key=lambda x: x[1]["return"])
                pair_ticker, pair_perf = strongest_pair
                
                # Map ticker to readable name
                forex_names = {
                    "EURUSD=X": "EUR/USD",
                    "GBPUSD=X": "GBP/USD",
                    "USDJPY=X": "USD/JPY",
                    "USDCAD=X": "USD/CAD",
                    "AUDUSD=X": "AUD/USD",
                    "USDCNY=X": "USD/CNY",
                }
                pair_name = forex_names.get(pair_ticker, pair_ticker)
                
                # Add forex idea if the movement is significant
                if abs(pair_perf["return"]) > 1.0:  # Only if movement is >1%
                    direction = "bullish" if pair_perf["return"] > 0 else "bearish"
                    ideas.append({
                        "title": f"Forex Opportunity: {pair_name}",
                        "type": "Forex",
                        "asset": pair_name,
                        "direction": direction,
                        "rationale": f"The {pair_name} pair has shown a {direction} trend with a {pair_perf['return']:.2f}% move. Consider a {direction} position with appropriate risk management.",
                        "risk_level": "High",
                        "time_horizon": "Short-term",
                        "metrics": {
                            "return": pair_perf['return'],
                            "volatility": pair_perf['volatility'],
                        }
                    })
        
        # Process bond data
        if "bonds" in self.data:
            bond_perf = self.analyze_stock_performance(self.data["bonds"])
            
            # Bond yield interpretation
            if bond_perf and "^TNX" in bond_perf:
                ten_year = bond_perf["^TNX"]
                yield_change = ten_year["return"]
                
                if abs(yield_change) > 3:  # Significant yield change
                    direction = "higher" if yield_change > 0 else "lower"
                    impact = "negative" if yield_change > 0 else "positive"
                    ideas.append({
                        "title": "Bond Market Development",
                        "type": "Bonds",
                        "asset": "10-Year Treasury",
                        "rationale": f"10-Year Treasury yields are moving {direction} ({yield_change:.2f}%), which may have {impact} implications for growth stocks and rate-sensitive sectors.",
                        "risk_level": "Medium",
                        "time_horizon": "Medium-term",
                        "metrics": {
                            "yield_change": yield_change,
                        }
                    })
        
        # Finalize and save ideas
        self.ideas = ideas
        logger.info(f"Generated {len(ideas)} investment ideas")
    
    def save_ideas(self):
        """
        Save generated investment ideas to processed data directory.
        """
        PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        file_path = PROCESSED_DATA_DIR / f"investment_ideas_{TODAY}.json"
        
        if DEBUG_MODE:
            logger.debug(f"DEBUG: Saving {len(self.ideas)} investment ideas to {file_path}")
            # Log the ideas being saved
            for i, idea in enumerate(self.ideas):
                logger.debug(f"DEBUG: Idea {i+1} - Title: {idea.get('title')}, Type: {idea.get('type')}, Asset: {idea.get('asset')}")
                if 'metrics' in idea:
                    logger.debug(f"DEBUG:   Metrics: {list(idea['metrics'].keys())}")
        
        try:
            # Collect information about data sources used
            markets_used = set()
            sectors_used = set()
            data_types_used = set()
            
            for idea in self.ideas:
                if idea.get("market"):
                    markets_used.add(idea["market"])
                if idea.get("sector"):
                    sectors_used.add(idea["sector"])
                    
                # Check metrics for data types
                if "metrics" in idea:
                    metrics = idea["metrics"]
                    if "rsi" in metrics or "macd" in metrics:
                        data_types_used.add("Technical Indicators")
                    if "finnhub_score" in metrics:
                        data_types_used.add("Alternative Data")
                    if "net_buys" in metrics or "insider_trend" in metrics:
                        data_types_used.add("Insider Trading Data")
                    if "sentiment" in metrics:
                        data_types_used.add("News Sentiment")
            
            # Create data sources meta information
            data_sources = {
                "Stock Data": "Alpha Vantage, Twelve Data, and Finnhub APIs",
                "Market Indices": ", ".join(markets_used) if markets_used else "S&P 500, NASDAQ, FTSE 100",
                "Sectors Analyzed": ", ".join(sectors_used) if sectors_used else "Various sectors",
                "Economic Data": "FRED (Federal Reserve Economic Data)",
                "Technical Analysis": "RSI, MACD, Moving Averages" if "Technical Indicators" in data_types_used else "Not used",
                "News Sentiment": "News API" if "News Sentiment" in data_types_used else "Not used",
                "Insider Trading": "Finnhub API" if "Insider Trading Data" in data_types_used else "Not used"
            }
            
            # Markets with data
            markets_with_data = list(self.markets.keys()) if self.markets else ["Legacy format"]
            
            output_data = {
                "date": TODAY,
                "ideas": self.ideas,
                "data_sources": data_sources,
                "markets_analyzed": markets_with_data,
                "data_types_used": list(data_types_used),
                "generated_at": datetime.datetime.now().isoformat()
            }
            
            with open(file_path, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            logger.info(f"Saved investment ideas to {file_path}")
            
            if DEBUG_MODE:
                # Verify file was written correctly by reading it back
                try:
                    with open(file_path, 'r') as f:
                        verification_data = json.load(f)
                    logger.debug(f"DEBUG: Verification - read back {len(verification_data.get('ideas', []))} ideas from saved file")
                    logger.debug(f"DEBUG: Data sources included: {list(verification_data.get('data_sources', {}).keys())}")
                except Exception as verify_error:
                    logger.error(f"DEBUG: Error verifying saved file: {verify_error}")
        except Exception as e:
            logger.error(f"Error saving investment ideas: {e}")


def main():
    analyzer = DataAnalyzer()
    analyzer.load_data()
    analyzer.generate_investment_ideas()
    analyzer.save_ideas()


if __name__ == "__main__":
    import sys
    
    # Check for debug mode flag
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        # Enable debug mode
        DEBUG_MODE = True
        # Set logger level to DEBUG
        logger.setLevel(logging.DEBUG)
        # Add a console handler for more verbose output
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logger.addHandler(console)
        # Also set root logger level
        logging.getLogger().setLevel(logging.DEBUG)
        
        print("Running in DEBUG mode - analyzing data with verbose output")
        print("Debugging info will be printed throughout execution")
    
    # Backward compatibility for --verbose flag
    elif len(sys.argv) > 1 and sys.argv[1] == "--verbose":
        DEBUG_MODE = True
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logger.addHandler(console)
        print("Running with verbose output (legacy mode, use --debug for full debug info)")
    
    main()
