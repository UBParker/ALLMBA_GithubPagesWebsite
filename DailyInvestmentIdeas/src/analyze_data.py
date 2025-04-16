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

# Set up paths
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
TODAY = datetime.datetime.now().strftime("%Y-%m-%d")

class DataAnalyzer:
    def __init__(self):
        self.data = {}
        self.ideas = []
        self.trends = {}
        self.sentiment = {}
    
    def load_data(self):
        """
        Load collected data from raw data directory.
        """
        logger.info("Loading raw data")
        
        # Find the most recent data files
        for file_type in ["indices", "tech_stocks", "finance_stocks", "energy_stocks", 
                         "forex", "bonds", "news", "trends", "crypto", "fred", "alpha_vantage",
                         "finnhub_quotes", "finnhub_company", "finnhub_sentiment", 
                         "finnhub_earnings", "finnhub_insider"]:
            pattern = f"{file_type}_*.json"
            files = sorted(RAW_DATA_DIR.glob(pattern), reverse=True)
            
            if files:
                latest_file = files[0]
                try:
                    with open(latest_file, 'r') as f:
                        self.data[file_type] = json.load(f)
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
            logger.warning("Missing some Finnhub data")
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
    
    def generate_investment_ideas(self):
        """
        Generate investment ideas based on analyzed data.
        """
        logger.info("Generating investment ideas")
        ideas = []
        
        # Process indices data
        if "indices" in self.data:
            indices_perf = self.analyze_stock_performance(self.data["indices"])
            
            # Identify strongest and weakest markets
            if indices_perf:
                strongest_market = max(indices_perf.items(), key=lambda x: x[1]["return"])
                weakest_market = min(indices_perf.items(), key=lambda x: x[1]["return"])
                
                market_names = {
                    "^DJI": "US (Dow Jones)",
                    "^GSPC": "US (S&P 500)",
                    "^IXIC": "US (NASDAQ)",
                    "^FTSE": "UK (FTSE 100)",
                    "^GDAXI": "Germany (DAX)",
                    "^FCHI": "France (CAC 40)",
                    "^N225": "Japan (Nikkei 225)",
                    "^HSI": "Hong Kong (Hang Seng)",
                    "000001.SS": "China (Shanghai Composite)",
                    "^GSPTSE": "Canada (S&P/TSX Composite)",
                }
                
                # Add regional market idea
                strongest_name = market_names.get(strongest_market[0], strongest_market[0])
                ideas.append({
                    "title": f"Regional Market Focus: {strongest_name}",
                    "type": "Regional Market",
                    "asset": strongest_market[0],
                    "market": strongest_name,
                    "rationale": f"The {strongest_name} market has shown strong performance with a {strongest_market[1]['return']:.2f}% return over the past week, outperforming other major markets. Consider increasing exposure to this region.",
                    "risk_level": "Medium",
                    "time_horizon": "Medium-term",
                    "metrics": {
                        "return": strongest_market[1]['return'],
                        "volatility": strongest_market[1]['volatility'],
                    }
                })
        
        # Analyze Finnhub data for additional insights
        finnhub_analysis = self.analyze_finnhub_data()
        
        # Process sector data
        sectors = {
            "tech": {"name": "Technology", "data": self.data.get("tech_stocks", {})},
            "finance": {"name": "Financial", "data": self.data.get("finance_stocks", {})},
            "energy": {"name": "Energy", "data": self.data.get("energy_stocks", {})},
        }
        
        # Calculate sector performance
        sector_performance = {}
        for sector_key, sector_info in sectors.items():
            if sector_info["data"]:
                performance = self.analyze_stock_performance(sector_info["data"])
                technical = self.analyze_technical_indicators(sector_info["data"])
                
                # Calculate average sector return
                returns = [p["return"] for p in performance.values() if "return" in p]
                if returns:
                    avg_return = sum(returns) / len(returns)
                    sector_performance[sector_key] = {
                        "name": sector_info["name"],
                        "avg_return": avg_return,
                        "stocks": performance,
                        "technical": technical
                    }
        
        # Find strongest sector
        if sector_performance:
            strongest_sector = max(sector_performance.items(), key=lambda x: x[1]["avg_return"])
            sector_key, sector_data = strongest_sector
            
            # Find best stock in the strongest sector
            if sector_data["stocks"]:
                best_stock = max(sector_data["stocks"].items(), key=lambda x: x[1]["return"])
                stock_ticker, stock_perf = best_stock
                
                stock_tech = sector_data["technical"].get(stock_ticker, {})
                rsi_value = stock_tech.get("rsi", "N/A")
                rsi_str = f"{rsi_value:.1f}" if isinstance(rsi_value, (int, float)) else "N/A"
                
                # Add Finnhub data if available
                finnhub_info = ""
                finnhub_metrics = {}
                if stock_ticker in finnhub_analysis:
                    fh_data = finnhub_analysis[stock_ticker]
                    
                    # Add sentiment info if available
                    if 'sentiment' in fh_data:
                        sentiment_score = fh_data['sentiment']['news_score']
                        sentiment_str = "positive" if sentiment_score > 0.5 else "neutral" if sentiment_score >= 0.3 else "negative"
                        finnhub_info += f" News sentiment is {sentiment_str} ({sentiment_score:.2f}/1.0)."
                        finnhub_metrics["sentiment_score"] = sentiment_score
                    
                    # Add upcoming earnings if available
                    if 'upcoming_earnings' in fh_data:
                        earnings_date = fh_data['upcoming_earnings']['date']
                        finnhub_info += f" Upcoming earnings on {earnings_date}."
                        finnhub_metrics["earnings_date"] = earnings_date
                    
                    # Add insider info if available
                    if 'insider' in fh_data and fh_data['insider']['net_transactions'] != 0:
                        net_tx = fh_data['insider']['net_transactions']
                        insider_str = "buying" if net_tx > 0 else "selling"
                        finnhub_info += f" Insiders have been net {insider_str} recently."
                        finnhub_metrics["insider_trend"] = insider_str
                    
                    # Add overall score
                    if 'finnhub_score' in fh_data:
                        finnhub_metrics["finnhub_score"] = fh_data['finnhub_score']
                
                # Add sector stock idea
                ideas.append({
                    "title": f"Strong {sector_data['name']} Stock: {stock_ticker}",
                    "type": "Stock",
                    "asset": stock_ticker,
                    "sector": sector_data['name'],
                    "rationale": f"{stock_ticker} has shown strong performance in the {sector_data['name']} sector with a {stock_perf['return']:.2f}% return. Technical indicators are supportive with RSI at {rsi_str}.{finnhub_info}",
                    "risk_level": "Medium-High",
                    "time_horizon": "Medium-term",
                    "metrics": {
                        "return": stock_perf['return'],
                        "volatility": stock_perf['volatility'],
                        "rsi": rsi_value if isinstance(rsi_value, (int, float)) else None,
                        **finnhub_metrics
                    }
                })
        
        # Generate Finnhub-specific ideas
        if finnhub_analysis:
            # Find stock with highest Finnhub score (if not already featured)
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
            
            # Find stocks with upcoming earnings
            earnings_stocks = {ticker: data for ticker, data in finnhub_analysis.items() 
                            if 'upcoming_earnings' in data and data['upcoming_earnings']['date']}
            
            if earnings_stocks and not any(idea["title"].startswith("Earnings Play") for idea in ideas):
                # Sort by closest earnings date
                sorted_earnings = sorted(
                    earnings_stocks.items(),
                    key=lambda x: datetime.datetime.strptime(x[1]['upcoming_earnings']['date'], '%Y-%m-%d')
                )
                
                if sorted_earnings:
                    ticker, earnings_data = sorted_earnings[0]
                    earnings_date = earnings_data['upcoming_earnings']['date']
                    
                    # Check if date is within next 10 days
                    earnings_datetime = datetime.datetime.strptime(earnings_date, '%Y-%m-%d')
                    today = datetime.datetime.now()
                    days_until = (earnings_datetime - today).days
                    
                    if 0 <= days_until <= 10:
                        # Add earnings play idea
                        estimate = earnings_data['upcoming_earnings'].get('estimate', 'N/A')
                        estimate_str = f"{estimate}" if estimate and estimate != 'N/A' else "N/A"
                        
                        # Check past earnings performance if available
                        surprise_info = ""
                        if 'latest_earnings' in earnings_data:
                            surprise_pct = earnings_data['latest_earnings'].get('surprise_pct', 0)
                            if surprise_pct > 0:
                                surprise_info = f" In the previous quarter, {ticker} beat expectations by {surprise_pct:.2f}%."
                            elif surprise_pct < 0:
                                surprise_info = f" In the previous quarter, {ticker} missed expectations by {abs(surprise_pct):.2f}%."
                        
                        ideas.append({
                            "title": f"Earnings Play: {ticker}",
                            "type": "Event-Driven",
                            "asset": ticker,
                            "rationale": f"{ticker} is reporting earnings on {earnings_date} ({days_until} days from now). EPS estimate is {estimate_str}.{surprise_info} Consider a short-term position based on your earnings expectations.",
                            "risk_level": "High",
                            "time_horizon": "Short-term",
                            "metrics": {
                                "earnings_date": earnings_date,
                                "days_until": days_until,
                                "eps_estimate": estimate if estimate and estimate != 'N/A' else None,
                                "previous_surprise": earnings_data.get('latest_earnings', {}).get('surprise_pct') if 'latest_earnings' in earnings_data else None,
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
        
        # Process crypto data
        if "crypto" in self.data:
            crypto_perf = {}
            for coin, data in self.data["crypto"].items():
                if "history" in data and "prices" in data["history"]:
                    try:
                        prices = data["history"]["prices"]
                        if len(prices) > 7:  # At least a week of data
                            start_price = prices[-7][1]  # [timestamp, price]
                            end_price = prices[-1][1]
                            return_pct = (end_price - start_price) / start_price * 100
                            
                            # Calculate volatility
                            price_series = [p[1] for p in prices[-7:]]
                            returns = [price_series[i] / price_series[i-1] - 1 for i in range(1, len(price_series))]
                            volatility = np.std(returns) * 100
                            
                            crypto_perf[coin] = {
                                "return": return_pct,
                                "volatility": volatility,
                                "current_price": end_price,
                            }
                    except Exception as e:
                        logger.error(f"Error processing crypto data for {coin}: {e}")
            
            if crypto_perf:
                # Find crypto with best risk-adjusted return
                risk_adjusted = {coin: data["return"] / data["volatility"] if data["volatility"] > 0 else 0 
                                for coin, data in crypto_perf.items()}
                best_crypto = max(risk_adjusted.items(), key=lambda x: x[1])
                coin_name, _ = best_crypto
                coin_perf = crypto_perf[coin_name]
                
                coin_display_names = {
                    "bitcoin": "Bitcoin (BTC)",
                    "ethereum": "Ethereum (ETH)",
                    "xrp": "XRP",
                    "cardano": "Cardano (ADA)",
                    "solana": "Solana (SOL)",
                }
                coin_display = coin_display_names.get(coin_name, coin_name.capitalize())
                
                # Add crypto idea
                if coin_perf["return"] > 5:  # Only if return is significant
                    ideas.append({
                        "title": f"Cryptocurrency Focus: {coin_display}",
                        "type": "Cryptocurrency",
                        "asset": coin_display,
                        "rationale": f"{coin_display} has shown strong performance with a {coin_perf['return']:.2f}% return and favorable risk-adjusted metrics.",
                        "risk_level": "Very High",
                        "time_horizon": "Short-term",
                        "metrics": {
                            "return": coin_perf['return'],
                            "volatility": coin_perf['volatility'],
                            "price": coin_perf['current_price'],
                        }
                    })
        
        # Process news sentiment
        if "news" in self.data:
            sentiment = self.analyze_news_sentiment(self.data["news"])
            
            if sentiment:
                # Find topic with most positive sentiment
                positive_topic = max(sentiment.items(), key=lambda x: x[1]["avg_sentiment"])
                topic, sentiment_data = positive_topic
                
                if sentiment_data["avg_sentiment"] > 0.2:  # Significantly positive
                    # Map topic to investment theme
                    topic_themes = {
                        "stock market": "broad market equities",
                        "interest rates": "rate-sensitive sectors",
                        "inflation": "inflation hedges like commodities or TIPS",
                        "recession": "defensive stocks and quality companies",
                        "economic growth": "cyclical sectors",
                        "federal reserve": "financial sector and rate-sensitive instruments",
                        "central bank": "bonds and financial stocks",
                        "earnings season": "companies with strong earnings potential",
                    }
                    theme = topic_themes.get(topic, topic)
                    
                    ideas.append({
                        "title": f"Sentiment-Based Opportunity: {topic.title()}",
                        "type": "Thematic",
                        "asset": topic.title(),
                        "rationale": f"News sentiment around {topic} is highly positive ({sentiment_data['avg_sentiment']:.2f}), which may create opportunities in {theme}.",
                        "risk_level": "Medium",
                        "time_horizon": "Medium-term",
                        "metrics": {
                            "sentiment": sentiment_data['avg_sentiment'],
                            "article_count": sentiment_data['article_count'],
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
        
        try:
            with open(file_path, 'w') as f:
                json.dump({
                    "date": TODAY,
                    "ideas": self.ideas,
                }, f, indent=2)
            logger.info(f"Saved investment ideas to {file_path}")
        except Exception as e:
            logger.error(f"Error saving investment ideas: {e}")


def main():
    analyzer = DataAnalyzer()
    analyzer.load_data()
    analyzer.generate_investment_ideas()
    analyzer.save_ideas()


if __name__ == "__main__":
    import sys
    
    # Check if the verbose flag is set
    verbose = False
    if len(sys.argv) > 1 and sys.argv[1] == "--verbose":
        verbose = True
        print("Running with verbose output")
    
    # Set up a console handler for verbose output
    if verbose:
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logger.addHandler(console)
    
    main()
