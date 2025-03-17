"""
Analysis Agent Module - Handles market data analysis and metrics calculation
"""

import logging
import re
from typing import Dict
from apify import Actor

logger = logging.getLogger(__name__)

class AnalysisAgent:
    def __init__(self):
        self.high_cost_markets = ["new york", "san francisco", "los angeles", "seattle", "boston", "miami"]

    async def charge_event(self, event_name: str, amount: float):
        """Helper function to handle pay-per-event charging"""
        try:
            await Actor.charge(event_name, amount)
            logger.info(f"Charged {amount} for {event_name}")
        except Exception as e:
            logger.warning(f"Failed to charge for {event_name}: {str(e)}")

    async def analyze_market_data(self, market_data: Dict, location: str = "") -> Dict:
        """Analyze the extracted market data and extract key metrics"""
        metrics = {
            "zillow": {},
            "redfin": {},
            "realtor": {},
            "rapid": {}
        }
        
        await self.charge_event('analysis-init', 0.02)
        
        is_high_cost = any(market.lower() in location.lower() for market in self.high_cost_markets)
        
        min_price = 10000
        max_price = 10000000 if is_high_cost else 2000000
        min_valid_price = 100000
        max_valid_price = 5000000 if is_high_cost else 1000000
        
        try:
            for source, data in market_data.items():
                text = data.get("text", "").lower()
                
                if not text:
                    continue
                    
                metrics_found = False
                
                # Extract and validate metrics
                metrics[source].update(self._extract_price_metrics(text, min_price, max_price))
                metrics[source].update(self._extract_price_change(text))
                metrics[source].update(self._extract_market_metrics(text))
                
                if metrics[source]:
                    metrics_found = True
                    await self.charge_event('market-analyzed', 0.02)
                
                metrics[source]["source_date"] = data.get("metadata", {}).get("loadedTime", "")
                
        except Exception as e:
            logger.error(f"Error analyzing market data: {str(e)}")
        
        metrics["_meta"] = {
            "min_valid_price": min_valid_price,
            "max_valid_price": max_valid_price,
            "is_high_cost": is_high_cost
        }
        
        source_urls = {
            source: data.get("metadata", {}).get("canonicalUrl") or data.get("metadata", {}).get("loadedUrl", "")
            for source, data in market_data.items()
        }
        
        return {"metrics": metrics, "source_urls": source_urls}

    def _extract_price_metrics(self, text: str, min_price: int, max_price: int) -> Dict:
        """Extract and validate price metrics"""
        metrics = {}
        price_patterns = [
            r"median (?:sale )?price.*?\$([0-9,.]+)[MK]?",
            r"average.*?home value.*?\$([0-9,.]+)[MK]?",
            r"median.*?home value.*?\$([0-9,.]+)[MK]?",
            r"\$([0-9,.]+)[MK]?(?=.*median)",
        ]
        
        for pattern in price_patterns:
            price_match = re.search(pattern, text)
            if price_match:
                try:
                    price = float(price_match.group(1).replace(",", ""))
                    if min_price <= price <= max_price:
                        if "m" in text[price_match.end():price_match.end()+2].lower():
                            metrics["median_price"] = price * 1000000
                        elif "k" in text[price_match.end():price_match.end()+2].lower():
                            metrics["median_price"] = price * 1000
                        else:
                            metrics["median_price"] = price
                        break
                except ValueError:
                    continue
        
        return metrics

    def _extract_price_change(self, text: str) -> Dict:
        """Extract and validate price change percentage"""
        metrics = {}
        change_patterns = [
            r"(up|down)\s+([0-9.]+)%\s+(?:since|compared to|over|in the) last year",
            r"([0-9.]+)%\s+(increase|decrease)\s+(?:since|compared to|over|in the) last year",
            r"([+-]?[0-9.]+)%\s+1-yr"
        ]
        
        for pattern in change_patterns:
            change_match = re.search(pattern, text)
            if change_match:
                try:
                    if len(change_match.groups()) == 2:
                        change = float(change_match.group(2))
                        if "down" in change_match.group(1).lower() or "decrease" in change_match.group(2).lower():
                            change = -change
                    else:
                        change = float(change_match.group(1))
                    if abs(change) <= 50:
                        metrics["price_change"] = change
                        break
                except ValueError:
                    continue
        
        return metrics

    def _extract_market_metrics(self, text: str) -> Dict:
        """Extract and validate market metrics (days on market, price per sqft, inventory)"""
        metrics = {}
        
        # Days on market
        dom_patterns = [
            r"(?:sell|sold) (?:in|after) (?:around )?([0-9]+) days",
            r"(?:average|median) (?:of )?([0-9]+) days on (?:the )?market",
            r"([0-9]+) days on (?:the )?market",
            r"pending in (?:around )?([0-9]+) days"
        ]
        
        for pattern in dom_patterns:
            dom_match = re.search(pattern, text)
            if dom_match:
                try:
                    days = int(dom_match.group(1))
                    if 0 <= days <= 365:
                        metrics["days_on_market"] = days
                        break
                except ValueError:
                    continue
        
        # Price per sqft
        sqft_patterns = [
            r"\$([0-9,.]+) per square (?:foot|feet|ft)",
            r"price per (?:square )?(?:foot|feet|ft).*?\$([0-9,.]+)"
        ]
        
        for pattern in sqft_patterns:
            sqft_match = re.search(pattern, text)
            if sqft_match:
                try:
                    price_sqft = float(sqft_match.group(1).replace(",", ""))
                    if 50 <= price_sqft <= 2000:
                        metrics["price_per_sqft"] = price_sqft
                        break
                except ValueError:
                    continue
        
        # Inventory
        inv_patterns = [
            r"([0-9,]+) homes? (?:for sale|available|active)",
            r"inventory of ([0-9,]+) homes",
            r"([0-9,]+) properties? (?:for sale|available|active)"
        ]
        
        for pattern in inv_patterns:
            inv_match = re.search(pattern, text)
            if inv_match:
                try:
                    inventory = int(inv_match.group(1).replace(",", ""))
                    if 0 <= inventory <= 10000:
                        metrics["inventory"] = inventory
                        break
                except ValueError:
                    continue
        
        return metrics 