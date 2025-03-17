"""
Newsletter Agent Module - Handles report generation using OpenAI
"""

import logging
import os
from datetime import datetime
from typing import Dict
from openai import AsyncOpenAI
from apify import Actor

logger = logging.getLogger(__name__)

class NewsletterAgent:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    async def charge_event(self, event_name: str, amount: float):
        """Helper function to handle pay-per-event charging"""
        try:
            await Actor.charge(event_name, amount)
            logger.info(f"Charged {amount} for {event_name}")
        except Exception as e:
            logger.warning(f"Failed to charge for {event_name}: {str(e)}")

    async def generate_newsletter(self, location: str, market_data: Dict, analysis: Dict) -> str:
        """Generate a real estate market newsletter using OpenAI"""
        try:
            current_date = datetime.now().strftime("%B %Y")
            
            metrics = analysis.get("metrics", {})
            source_urls = analysis.get("source_urls", {})
            meta = metrics.get("_meta", {})
            min_valid_price = meta.get("min_valid_price", 100000)
            max_valid_price = meta.get("max_valid_price", 1000000)
            
            formatted_data = self._format_source_data(metrics)
            formatted_urls = self._format_source_urls(source_urls)
            avg_metrics = self._calculate_averages(metrics, min_valid_price, max_valid_price)
            
            system_content = self._get_system_prompt()
            user_content = self._get_user_prompt(location, current_date, formatted_data, avg_metrics, formatted_urls)
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            newsletter = response.choices[0].message.content
            
            await self.charge_event('newsletter-generated', 0.50)
            
            return newsletter
            
        except Exception as e:
            logger.error(f"Error generating newsletter: {str(e)}")
            return f"Error generating newsletter: {str(e)}"

    def _format_price(self, price):
        """Format price with proper formatting"""
        if price and isinstance(price, (int, float)):
            return f"${price:,.0f}"
        return "N/A"

    def _format_percent(self, value):
        """Format percentage with proper formatting"""
        if value is not None:
            return f"{value:+.1f}%" if value >= 0 else f"{value:.1f}%"
        return "N/A"

    def _format_source_data(self, metrics: Dict) -> str:
        """Format market data from each source"""
        formatted_data = ""
        for source in ["zillow", "redfin", "realtor", "rapid"]:
            source_data = metrics.get(source, {})
            if source_data:
                formatted_data += f"""
{source.capitalize()}:
- Median Price: {self._format_price(source_data.get('median_price'))}
- Price Change: {self._format_percent(source_data.get('price_change'))}
- Days on Market: {source_data.get('days_on_market', 'N/A')}
- Price Per SqFt: {self._format_price(source_data.get('price_per_sqft'))}
- Inventory: {source_data.get('inventory', 'N/A')}
"""
        return formatted_data

    def _format_source_urls(self, source_urls: Dict) -> str:
        """Format source URLs"""
        return "\n".join(f"- {source.capitalize()}: {url}" for source, url in source_urls.items() if url)

    def _calculate_averages(self, metrics: Dict, min_valid_price: int, max_valid_price: int) -> Dict:
        """Calculate average metrics across sources"""
        def calculate_average(metric_name):
            values = []
            for source, source_data in metrics.items():
                if source == "_meta":
                    continue
                value = source_data.get(metric_name)
                if value and isinstance(value, (int, float)):
                    if metric_name == "median_price" and (value < min_valid_price or value > max_valid_price):
                        continue
                    if metric_name == "price_change" and abs(value) > 20:
                        continue
                    values.append(value)
            return sum(values) / len(values) if values else None
        
        return {
            "avg_price": calculate_average("median_price"),
            "avg_price_change": calculate_average("price_change"),
            "avg_dom": calculate_average("days_on_market")
        }

    def _get_system_prompt(self) -> str:
        """Get system prompt for newsletter generation"""
        return """You are an expert real estate newsletter writer. Create a professional, polished, and well-structured newsletter using the provided market data.

Format the newsletter in Markdown with the following requirements:
1. Begin with a main heading (#) that includes the location name and "Real Estate Market Update - [Month Year]"
2. Add a "Last Updated" line right after the title
3. Use subheadings (##) for different sections with proper spacing
4. Include a well-formatted Markdown table comparing data sources
5. Use emoji icons to highlight key points
6. Format all prices with dollar signs and commas
7. Include percentages with % symbol and +/- signs
8. Use proper spacing between sections
9. Use **bold** for critical information and *italic* for secondary emphasis
10. If data is limited or inconsistent, acknowledge this and focus on reliable metrics

Include these sections:
- Executive Summary (3-4 sentences)
- Market Overview (with validated average metrics)
- Market Data Comparison (table)
- Price Analysis
- Market Activity
- Market Forecast
- Recommendations for Buyers and Sellers
- Additional Resources"""

    def _get_user_prompt(self, location: str, current_date: str, formatted_data: str, avg_metrics: Dict, formatted_urls: str) -> str:
        """Get user prompt for newsletter generation"""
        return f"""Create a real estate market newsletter for {location} for {current_date}.

MARKET DATA:
{formatted_data}

AVERAGE METRICS (excluding outliers):
- Average Price: {self._format_price(avg_metrics['avg_price'])}
- Average Price Change: {self._format_percent(avg_metrics['avg_price_change'])}
- Average Days on Market: {int(avg_metrics['avg_dom']) if avg_metrics['avg_dom'] else 'N/A'}

SOURCE URLS:
{formatted_urls}

Please generate a comprehensive newsletter following the format in the system instructions. Make sure to:
1. Focus on the most reliable data points
2. Acknowledge any data inconsistencies
3. Provide specific insights based on validated metrics
4. Include actionable recommendations
5. Format all numbers properly
6. Use appropriate spacing and visual elements
7. Bold important findings
8. If certain metrics are missing or unreliable, explain the limitations""" 