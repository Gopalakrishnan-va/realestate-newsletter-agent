"""
Search Agent Module - Handles finding relevant real estate market sources
"""

import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from decimal import Decimal
from apify import Actor
from apify_client import ApifyClient
from openai import AsyncOpenAI
import os

logger = logging.getLogger(__name__)

@dataclass
class URLData:
    url: str
    source: str

class SearchAgent:
    # URL validation patterns focusing on essential subdirectories and formats
    URL_PATTERNS = {
        "zillow": r"zillow\.com/home-values/\d+/[a-zA-Z0-9-]+(?:/)?$",
        "redfin": r"redfin\.com/city/\d+/[A-Z]{2}/[A-Za-z-]+/housing-market(?:/)?$",
        "realtor": r"realtor\.com/realestateandhomes-search/[A-Za-z-]+_[A-Z]{2}/overview(?:/)?$",
        "rocket": r"rocket\.com/homes/market-reports/[a-z]{2}/[a-z-]+(?:/)?$"
    }

    def __init__(self, client: AsyncOpenAI):
        """Initialize the SearchAgent with an OpenAI client.
        
        Args:
            client (AsyncOpenAI): The OpenAI client instance to use for API calls
        """
        self.client = client
        self.apify_client = ApifyClient(token=os.environ["APIFY_TOKEN"])

    def _normalize_location(self, location: str) -> Optional[str]:
        """Normalize location input to a standardized format."""
        try:
            # Remove extra whitespace and convert to lowercase
            location = " ".join(location.strip().lower().split())
            
            # Extract state code (assuming 2-letter state code)
            state_match = re.search(r'[,\s]+([a-zA-Z]{2})$', location)
            if not state_match:
                logger.warning(f"No valid state code found in location: {location}")
                return None
                
            state = state_match.group(1).upper()
            
            # Remove state code and clean up remaining location
            base_location = location[:state_match.start()].strip()
            
            # Remove only non-essential location words and special characters
            base_location = re.sub(r'\b(town|village|township|metropolitan|area)\b', '', base_location)
            base_location = re.sub(r'[^\w\s-]', '', base_location).strip()
            
            # Convert spaces to hyphens and remove multiple hyphens
            normalized = f"{'-'.join(base_location.split())}-{state}"
            normalized = re.sub(r'-+', '-', normalized)
            
            logger.info(f"Normalized location '{location}' to '{normalized}'")
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing location '{location}': {str(e)}")
            return None

    async def find_sources(self, location: str) -> Dict[str, str]:
        """Find relevant real estate market sources for the given location.
        
        Args:
            location (str): The city and state to search for
            
        Returns:
            Dict[str, str]: Dictionary of source names to URLs
        """
        try:
            # Charge for search initialization
            await Actor.charge('search-init')
            
            # Get normalized location
            normalized_location = self._normalize_location(location)
            if not normalized_location:
                raise ValueError(f"Could not normalize location: {location}")
            
            # Search for URLs using Google Search
            all_urls = await self.search_urls(location)
            
            # Filter and validate URLs
            filtered_urls = await self.filter_urls(all_urls)
            if not filtered_urls:
                raise ValueError("No valid URLs found after filtering")
            
            # Convert to dictionary format
            return {url_data.source: url_data.url for url_data in filtered_urls}
            
        except Exception as e:
            logger.error(f"Error finding sources: {str(e)}")
            raise  # Re-raise the error instead of returning empty dict

    async def search_urls(self, location: str) -> List[str]:
        """Search for market research URLs using Apify Google Search Scraper"""
        all_urls = []
        
        try:
            normalized_location = self._normalize_location(location)
            if not normalized_location:
                raise ValueError(f"Could not normalize location: {location}")
                
            # Simple search query focusing on main domains
            search_query = f"{normalized_location} real estate market site:zillow.com OR site:redfin.com OR site:realtor.com OR site:rocket.com"
            logger.info(f"Searching with query: {search_query}")
            
            # Run Google Search scraper
            run = self.apify_client.actor("apify/google-search-scraper").call(
                run_input={
                    "queries": search_query,
                    "maxPagesPerQuery": 2,
                    "resultsPerPage": 10,
                    "languageCode": "en",
                    "countryCode": "us",
                    "mobileResults": False
                }
            )
            
            # Get results from dataset
            dataset_id = run["defaultDatasetId"]
            items = self.apify_client.dataset(dataset_id).list_items().items
            
            if items and len(items) > 0:
                for item in items:
                    for result in item.get("organicResults", []):
                        url = result.get("url", "").strip()
                        if url:
                            all_urls.append(url)
                            logger.info(f"Found URL: {url}")
                            await Actor.charge('url-processed')
                            
        except Exception as e:
            logger.error(f"Error searching URLs: {str(e)}")
            raise  # Raise the error instead of falling back to templates
            
        if not all_urls:
            logger.warning("No URLs found in search")
            raise ValueError("No URLs found in search")  # Raise error instead of falling back
            
        logger.info(f"Found {len(all_urls)} URLs in total")
        return all_urls

    async def filter_urls(self, urls: List[str]) -> List[URLData]:
        """Filter and validate URLs by source"""
        filtered_urls = []
        source_counts = {source: 0 for source in self.URL_PATTERNS.keys()}
        
        for url in urls:
            for source, pattern in self.URL_PATTERNS.items():
                if re.search(pattern, url, re.IGNORECASE):
                    if source_counts[source] == 0:  # Only take first valid URL per source
                        filtered_urls.append(URLData(url=url, source=source))
                        source_counts[source] += 1
                        logger.info(f"Found valid {source} URL: {url}")
                        await Actor.charge('url-processed')
                    break
        
        if not filtered_urls:
            logger.warning("No valid URLs found after filtering")
        else:
            logger.info(f"Found {len(filtered_urls)} valid URLs")
            
        return filtered_urls

    def _get_template_urls(self, normalized_location: str) -> Dict[str, str]:
        """Get template URLs as fallback"""
        return {
            "zillow": f"https://www.zillow.com/homes/{normalized_location}_rb/",
            "redfin": f"https://www.redfin.com/city/{normalized_location}",
            "realtor": f"https://www.realtor.com/realestateandhomes-search/{normalized_location}"
        } 