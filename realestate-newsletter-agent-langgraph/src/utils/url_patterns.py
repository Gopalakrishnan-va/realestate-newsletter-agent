"""URL patterns for real estate market data sources"""

# Regular expression patterns for validating real estate market URLs
URL_PATTERNS = {
    "zillow": r"zillow\.com/(?:home-values/\d+/[^/]+(?:-[a-z]{2})?|[^/]+-[a-z]{2}/home-values|[^/]+/home-values)/?$",
    "redfin": r"redfin\.com/(?:city/\d+/[A-Z]{2}/[^/]+/housing-market|[^/]+/housing-market)/?$",
    "realtor": r"realtor\.com/(?:realestateandhomes-search/[^/]+(?:_[A-Z]{2})?/overview|market-trends/[^/]+)/?$",
    "rapid": r"(?:rocket|rapid)\.com/(?:homes/market-reports|market-trends)/(?:[a-z]{2}/)?[^/]+/?$"
}

# Search query templates for each source
SEARCH_QUERIES = {
    "zillow": "{location} real estate market home values site:zillow.com",
    "redfin": "{location} housing market trends site:redfin.com",
    "realtor": "{location} real estate market overview site:realtor.com",
    "rapid": "{location} housing market report site:rocket.com"
}

# Maximum number of URLs to process per source
MAX_URLS_PER_SOURCE = 1

# Required sources for complete analysis
REQUIRED_SOURCES = ["zillow", "redfin", "realtor", "rapid"] 