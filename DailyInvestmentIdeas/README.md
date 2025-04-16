# ALLMBA - Daily Investment Ideas

An automated system that generates daily investment ideas by analyzing data from various financial markets and sources.

## Overview

This service pulls data from multiple APIs to analyze Asian, European, American, and Canadian markets across various asset classes including FX, bonds, stocks, and other investment mechanisms. It uses a combination of market data, trends, and sentiment analysis to generate informed investment recommendations.

## Data Sources

- **Yahoo Finance**: Real-time and historical market data (no API key required)
- **Alpha Vantage API**: Financial data and technical indicators (API key: ZMUZQIRZWJKML99P)
- **FRED API**: Economic indicators and data (API key: fb670d7e87729f288ed7ffb40f986bb9)
- **News API**: News headlines for sentiment analysis (API key: b8851f0d4dc5462bbdddebc446bbfe89)
- **Finnhub API**: Alternative data including insider transactions, earnings, and sentiment (API key: d000cm9r01qud9ql2jagd000cm9r01qud9ql2jb0)
- **Google Trends API**: Interest trends in various assets and companies (no API key required)
- **CoinGecko API**: Cryptocurrency market data (no API key required)

## Architecture

- **Data Collection**: Python scripts fetch data from various APIs
- **Data Processing**: Analyze and process data to identify opportunities
- **Recommendation Engine**: Generate investment ideas based on processed data
- **API**: Serve recommendations via a simple REST API
- **Deployment**: Google Cloud Platform (Cloud Run, Cloud Functions, Cloud Scheduler)

## Local Development

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Set up environment variables in `.env` file (see `.env.example`) - API keys are already hardcoded

3. Run the data collection script:
```
python src/collect_data.py
```

4. Run the analysis script:
```
python src/analyze_data.py
```

5. Start the API locally:
```
python src/api.py
```

## Deployment

### Google Cloud Platform Setup

1. Set up a new GCP project
2. Enable required APIs (Cloud Run, Cloud Functions, Cloud Scheduler, etc.)
3. Set up service account with appropriate permissions
4. Deploy using the provided scripts in the `deploy` directory

```
cd deploy
./deploy_to_gcp.sh
```

## Integration with GitHub Pages

The GitHub Pages website can connect to this API by updating the Daily Investment Ideas page to fetch and display the recommendations. The integration code is provided in `integration/github_pages_integration.js`. See the detailed integration guide in `README-integration.md`.

## License

This project is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

## Contact

For more information, contact info@allmba.com