"""
Main entry point for the Apify Actor.
Orchestrates the autonomous real estate market research process.
"""

from __future__ import annotations

import logging
import os
from apify import Actor
from apify_client import ApifyClient

from .agents.search_agent import SearchAgent
from .agents.extraction_agent import ExtractionAgent
from .agents.analysis_agent import AnalysisAgent
from .agents.newsletter_agent import NewsletterAgent
from .models.schemas import AgentState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main() -> None:
    """Main entry point for the Apify Actor."""
    async with Actor:
        # Get input
        actor_input = await Actor.get_input() or {}
        location = actor_input.get("location", "San Jose, CA")
        if actor_input.get('debug', False):
            Actor.log.setLevel(logging.DEBUG)

        # Initialize state
        state = AgentState(location=location)
        
        try:
            # Initialize Apify client
            client = ApifyClient(token=os.environ.get("APIFY_TOKEN"))
            
            # Ensure OpenAI API key is set
            if not os.environ.get("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY environment variable is not set")
            
            # Initialize agents
            search_agent = SearchAgent(client)
            extraction_agent = ExtractionAgent(client)
            analysis_agent = AnalysisAgent()
            newsletter_agent = NewsletterAgent()
            
            # Search for URLs
            logger.info(f"Searching for market data URLs for location: {location}")
            urls = await search_agent.search_urls(location)
            state.search_urls = urls
            
            if not urls:
                state.errors.append("No URLs found in initial search")
                logger.error("No URLs found in initial search")
                return
            
            # Filter and validate URLs
            filtered_urls = await search_agent.filter_urls(urls)
            state.filtered_urls = filtered_urls
            
            if not filtered_urls:
                state.errors.append("No valid URLs found after filtering")
                logger.error("No valid URLs found after filtering")
                return
            
            # Extract market data from filtered URLs
            logger.info("Extracting market data from filtered URLs...")
            market_data = await extraction_agent.extract_market_data(filtered_urls)
            
            # Analyze market data
            logger.info("Analyzing market data...")
            analysis = await analysis_agent.analyze_market_data(market_data, location)
            
            # Generate newsletter
            logger.info("Generating newsletter...")
            newsletter = await newsletter_agent.generate_newsletter(location, market_data, analysis)
            
            # Save results to default dataset
            await Actor.push_data({
                "location": location,
                "filtered_urls": {
                    url_data.source: url_data.url 
                    for url_data in filtered_urls
                },
                "market_data": market_data,
                "analysis": analysis,
                "newsletter": newsletter
            })
            
        except Exception as e:
            logger.error(f"Error in actor execution: {str(e)}")
            state.errors.append(f"Error in actor execution: {str(e)}")
        
        finally:
            # Always exit properly
            await Actor.exit()

# Run the actor
if __name__ == "__main__":
    Actor.main(main)
