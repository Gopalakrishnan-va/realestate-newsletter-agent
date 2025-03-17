"""
Extraction Agent Module - Handles data extraction from validated sources
"""

import logging
from typing import Dict, List
from dataclasses import dataclass
from decimal import Decimal
from apify import Actor
from apify_client import ApifyClient
from openai import AsyncOpenAI
import os
import re

logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    median_price: float
    price_change: float
    inventory: int
    days_on_market: int
    source: str

class ExtractionAgent:
    def __init__(self, client: AsyncOpenAI):
        """Initialize the ExtractionAgent with OpenAI client"""
        self.client = client
        self.apify_client = ApifyClient(token=os.environ["APIFY_TOKEN"])
        
    def _extract_price_metrics(self, text: str) -> Dict:
        """Extract price metrics from text"""
        metrics = {}
        price_patterns = [
            r"(?:median|average).*?(?:home value|sale price|sold price)[^\$]*\$([0-9,.]+)([KM]?)",
            r"\$([0-9,.]+)([KM]?)(?=.*median)",
            r"typical home value.*?\$([0-9,.]+)([KM]?)",
            r"median list price.*?\$([0-9,.]+)([KM]?)"
        ]
        
        for pattern in price_patterns:
            price_match = re.search(pattern, text.lower())
            if price_match:
                try:
                    price_str = price_match.group(1).replace(",", "")
                    price = float(price_str)
                    suffix = price_match.group(2).upper() if len(price_match.groups()) > 1 else ""
                    
                    # Handle price multipliers
                    if suffix == "M":
                        price *= 1000000
                    elif suffix == "K":
                        price *= 1000
                    
                    # Validate price range (100k to 2M for normal markets)
                    if 100000 <= price <= 2000000:
                        metrics["median_price"] = price
                        logger.info(f"Extracted price: ${price:,.2f}")
                        break
                    else:
                        logger.warning(f"Price {price} outside valid range")
                except ValueError:
                    continue
        
        return metrics

    def _extract_price_change(self, text: str) -> Dict:
        """Extract price change percentage from text"""
        metrics = {}
        change_patterns = [
            r"(?:down|decreased)\s+([0-9.]+)%",
            r"([0-9.]+)%\s+(?:decrease)",
            r"-([0-9.]+)%",
            r"(?:up|increased)\s+([0-9.]+)%",
            r"([0-9.]+)%\s+(?:increase)",
            r"\+([0-9.]+)%"
        ]
        
        for pattern in change_patterns:
            change_match = re.search(pattern, text.lower())
            if change_match:
                try:
                    change = float(change_match.group(1))
                    # Make negative if pattern indicates decrease
                    if any(word in pattern.lower() for word in ["down", "decrease", "-"]):
                        change = -change
                    
                    # Validate change range (-20% to +20% is reasonable)
                    if abs(change) <= 20:
                        metrics["price_change"] = change
                        logger.info(f"Extracted price change: {change}%")
                        break
                    else:
                        logger.warning(f"Price change {change}% outside valid range")
                except ValueError:
                    continue
        
        return metrics

    def _extract_market_metrics(self, text: str) -> Dict:
        """Extract market metrics from text"""
        metrics = {}
        
        # Days on market
        dom_patterns = [
            r"(?:median |average )?(?:days on market|dom)[:\s]+([0-9]+)",
            r"(?:sell|sold|pending) (?:in|after) (?:around )?([0-9]+) days",
            r"(?:average|median) (?:of )?([0-9]+) days on (?:the )?market",
            r"([0-9]+) days? on (?:the )?market",
            r"average listing age of ([0-9]+) days"
        ]
        
        for pattern in dom_patterns:
            dom_match = re.search(pattern, text.lower())
            if dom_match:
                try:
                    days = int(dom_match.group(1))
                    if 0 <= days <= 180:  # Most markets are under 180 days
                        metrics["days_on_market"] = days
                        logger.info(f"Extracted days on market: {days}")
                        break
                    else:
                        logger.warning(f"Days on market {days} outside valid range")
                except ValueError:
                    continue
        
        # Inventory
        inv_patterns = [
            r"([0-9,]+)\s+(?:homes?|properties?|listings?|houses?)?\s+(?:for sale|available|active)",
            r"inventory of ([0-9,]+)",
            r"([0-9,]+) total listings",
            r"([0-9,]+) properties found",
            r"([0-9,]+) homes sold"
        ]
        
        for pattern in inv_patterns:
            inv_match = re.search(pattern, text.lower())
            if inv_match:
                try:
                    inventory = int(inv_match.group(1).replace(",", ""))
                    if 0 <= inventory <= 50000:  # Increased max for larger markets
                        metrics["inventory"] = inventory
                        logger.info(f"Extracted inventory: {inventory}")
                        break
                    else:
                        logger.warning(f"Inventory {inventory} outside valid range")
                except ValueError:
                    continue
        
        return metrics

    async def extract_data(self, urls: Dict[str, str]) -> List[MarketData]:
        """Extract market data from the filtered URLs"""
        market_data = []
        
        try:
            # Convert URLs dict to list of URLData for crawler
            url_list = [{"url": url, "method": "GET"} for url in urls.values()]
            
            crawler_input = {
                "startUrls": url_list,
                "crawlerType": "playwright",  # Changed to playwright for better JS support
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
                "waitUntil": "networkidle",  # Wait for network to be idle
                "browserPoolOptions": {
                    "maxOpenPagesPerBrowser": 1,
                    "retireInstanceAfterRequestCount": 5
                }
            }
            
            logger.info("Starting Website Content Crawler...")
            run = self.apify_client.actor("apify/website-content-crawler").call(
                run_input=crawler_input,
                memory_mbytes=4096
            )
            
            dataset_id = run["defaultDatasetId"]
            items = self.apify_client.dataset(dataset_id).list_items().items
            
            for source, url in urls.items():
                logger.info(f"Processing {source} URL: {url}")
                extracted = False
                
                for item in items:
                    if item.get("url") == url:
                        text_content = item.get("text", "")
                        
                        if not text_content:
                            logger.warning(f"No content extracted from {source}")
                            continue
                        
                        # Log first 500 chars of content for debugging
                        logger.debug(f"{source} content preview: {text_content[:500]}")
                            
                        # Extract metrics using parsing logic
                        price_metrics = self._extract_price_metrics(text_content)
                        price_change = self._extract_price_change(text_content)
                        market_metrics = self._extract_market_metrics(text_content)
                        
                        if price_metrics or price_change or market_metrics:
                            await Actor.charge('data-extracted')
                            logger.info(f"Successfully extracted data from {source}")
                            
                            market_data.append(MarketData(
                                median_price=price_metrics.get("median_price", 0),
                                price_change=price_change.get("price_change", 0),
                                inventory=market_metrics.get("inventory", 0),
                                days_on_market=market_metrics.get("days_on_market", 0),
                                source=source
                            ))
                            extracted = True
                            break
                
                if not extracted:
                    logger.error(f"Failed to extract valid data from {source}")
                        
        except Exception as e:
            logger.error(f"Error extracting market data: {str(e)}")
            
        return market_data 