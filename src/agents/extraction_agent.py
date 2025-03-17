"""
Extraction Agent Module - Handles data extraction from validated sources
"""

import logging
from typing import Dict, List
from apify import Actor
from apify_client import ApifyClient

from ..models.schemas import URLData

logger = logging.getLogger(__name__)

class ExtractionAgent:
    def __init__(self, client: ApifyClient):
        self.client = client

    async def charge_event(self, event_name: str, amount: float):
        """Helper function to handle pay-per-event charging"""
        try:
            await Actor.charge(event_name, amount)
            logger.info(f"Charged {amount} for {event_name}")
        except Exception as e:
            logger.warning(f"Failed to charge for {event_name}: {str(e)}")

    async def extract_market_data(self, urls: List[URLData]) -> Dict:
        """Extract market data from the filtered URLs"""
        market_data = {}
        
        try:
            await self.charge_event('extraction-init', 0.02)
            
            crawler_input = {
                "startUrls": [{"url": url.url, "method": "GET"} for url in urls],
                "crawlerType": "cheerio",
                "maxCrawlPages": len(urls),
                "maxCrawlDepth": 0,
                "saveMarkdown": True,
                "maxRequestRetries": 3,
                "maxConcurrency": 1,
                "proxyConfiguration": {
                    "useApifyProxy": True,
                    "apifyProxyGroups": ["RESIDENTIAL"]
                },
                "removeElementsCssSelector": "nav, footer, script, style, noscript, svg, img[src^='data:']",
                "htmlTransformer": "readableText",
                "browserPoolOptions": {
                    "maxOpenPagesPerBrowser": 1,
                    "retireInstanceAfterRequestCount": 5
                }
            }
            
            logger.info("Starting Website Content Crawler...")
            run = self.client.actor("apify/website-content-crawler").call(
                run_input=crawler_input,
                memory_mbytes=4096
            )
            
            dataset_id = run["defaultDatasetId"]
            items = self.client.dataset(dataset_id).list_items().items
            
            for item in items:
                url = item.get("url", "")
                for url_data in urls:
                    if url == url_data.url:
                        market_data[url_data.source] = {
                            "text": item.get("text", ""),
                            "markdown": item.get("markdown", ""),
                            "metadata": item.get("metadata", {})
                        }
                        logger.info(f"Successfully extracted data from {url_data.source}")
                        await self.charge_event('data-extracted', 0.02)
                        break
                        
        except Exception as e:
            logger.error(f"Error extracting market data: {str(e)}")
            
        return market_data 