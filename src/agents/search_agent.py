"""
Search Agent Module - Handles URL discovery and validation
"""

import logging
import re
from typing import List, Optional
from dataclasses import dataclass
from apify import Actor
from apify_client import ApifyClient

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

    def __init__(self, client: ApifyClient):
        self.client = client

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

    async def charge_event(self, event_name: str, amount: float):
        """Helper function to handle pay-per-event charging"""
        try:
            await Actor.charge(event_name, amount)
            logger.info(f"Charged {amount} for {event_name}")
        except Exception as e:
            logger.warning(f"Failed to charge for {event_name}: {str(e)}")

    async def search_urls(self, location: str) -> List[str]:
        """Search for market research URLs"""
        all_urls = []
        
        try:
            normalized_location = self._normalize_location(location)
            if not normalized_location:
                raise ValueError(f"Could not normalize location: {location}")
                
            # Simple search query focusing on main domains
            search_query = f"{normalized_location} real estate market site:zillow.com OR site:redfin.com OR site:realtor.com OR site:rocket.com"
            logger.info(f"Searching with query: {search_query}")
            
            await self.charge_event('search-init', 0.02)
            
            run = self.client.actor("apify/google-search-scraper").call(
                run_input={
                    "queries": search_query,
                    "maxPagesPerQuery": 2,
                    "resultsPerPage": 10,
                    "languageCode": "en",
                    "countryCode": "us",
                    "mobileResults": False
                }
            )
            
            dataset_id = run["defaultDatasetId"]
            items = self.client.dataset(dataset_id).list_items().items
            
            if items and len(items) > 0:
                for item in items:
                    for result in item.get("organicResults", []):
                        url = result.get("url", "").strip()
                        if url:
                            all_urls.append(url)
                            logger.info(f"Found URL: {url}")
                            
        except Exception as e:
            logger.error(f"Error searching URLs: {str(e)}")
            
        if not all_urls:
            logger.warning("No URLs found in search")
        else:
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
                        await self.charge_event('url-processed', 0.02)
                    break
        
        if not filtered_urls:
            logger.warning("No valid URLs found after filtering")
        else:
            logger.info(f"Found {len(filtered_urls)} valid URLs")
            
        return filtered_urls 