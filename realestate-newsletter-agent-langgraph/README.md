# Real Estate Market Research Agent

An autonomous Apify actor that generates comprehensive real estate market research reports by analyzing data from multiple authoritative sources.

## 🤖 Autonomous Capabilities

The agent operates through a series of autonomous modules, each handling specific aspects of market research:

1. **Search Agent**
   - Autonomously discovers relevant market research URLs
   - Filters and validates sources based on authority and relevance
   - Supports major real estate platforms (Zillow, Redfin, Realtor.com)

2. **Data Extraction Agent**
   - Scrapes market data from validated sources
   - Handles different page structures and data formats
   - Memory-efficient crawling with residential proxy support

3. **Market Analysis Agent**
   - Validates and normalizes price data
   - Detects high-cost markets automatically
   - Calculates key metrics with outlier detection
   - Cross-references data points for accuracy

4. **Newsletter Generation Agent**
   - Creates professional market reports using AI
   - Formats data in a consistent, readable structure
   - Provides actionable insights and recommendations
   - Includes source citations and data comparisons

## 💰 Pay-Per-Event Pricing

The actor uses a transparent pay-per-event pricing model:

- Search initialization: $0.02
- URL processing: $0.02 per valid URL
- Data extraction: $0.02 per source
- Market analysis: $0.02 per source
- Newsletter generation: $0.50

Total cost per run: $0.72 - $0.80 (depending on number of sources)

## 🚀 Input Parameters

```json
{
    "location": "City, State",
    "debug": false
}
```

## 📊 Output Format

```json
{
    "location": "City, State",
    "filtered_urls": {
        "zillow": "url",
        "redfin": "url",
        "realtor": "url"
    },
    "market_data": {
        // Raw extracted data from each source
    },
    "analysis": {
        "metrics": {
            // Processed market metrics
        },
        "source_urls": {
            // Source attribution
        }
    },
    "newsletter": "Formatted markdown report"
}
```

## 🔧 Technical Requirements

- Python 3.13+
- OpenAI API key
- Apify Platform account
- Residential proxy access (provided by Apify)

## 🛠️ Environment Variables

Required:
- `APIFY_TOKEN`: Your Apify API token
- `OPENAI_API_KEY`: Your OpenAI API key

## 📝 Newsletter Format

The generated newsletter includes:
- Executive Summary
- Market Overview
- Market Data Comparison
- Price Analysis
- Market Activity
- Market Forecast
- Recommendations
- Additional Resources

## 🏗️ Architecture

The actor is built with a modular architecture:
```
src/
├── agents/
│   ├── search_agent.py
│   ├── extraction_agent.py
│   ├── analysis_agent.py
│   └── newsletter_agent.py
├── models/
│   └── schemas.py
├── utils/
│   └── url_patterns.py
└── main.py
```

## 📈 Validation & Error Handling

- Price validation ranges adjust automatically for high-cost markets
- Outlier detection in price and market metrics
- Comprehensive error logging and state tracking
- Graceful handling of missing or invalid data

## 🔄 Continuous Updates

The agent automatically:
- Updates search patterns for current year
- Validates data freshness
- Adapts to source website changes
- Handles new market conditions

## 📚 Usage Example

```python
from apify_client import ApifyClient

# Initialize the client
client = ApifyClient('YOUR_API_TOKEN')

# Run the actor
run = client.actor('username/real-estate-market-research').call(run_input={
    'location': 'San Jose, CA'
})

# Get results
output = client.dataset(run['defaultDatasetId']).list_items().items[0]
print(output['newsletter'])
```

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
