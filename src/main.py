"""
Main entry point for the Apify Actor.
Orchestrates the autonomous real estate market research process.
"""

from __future__ import annotations

import logging
import os
from apify import Actor
from apify_client import ApifyClient
from openai import AsyncOpenAI

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
        logger.info("Starting real estate market analysis actor")
        
        # Get input
        actor_input = await Actor.get_input() or {}
        logger.info(f"Received input with keys: {', '.join(actor_input.keys())}")
        
        # Set API keys from input
        openai_api_key = actor_input.get("openaiApiKey")
        apify_api_key = actor_input.get("apifyApiKey")
        
        if not openai_api_key:
            logger.error("OpenAI API key is required in input")
            return
        logger.info("OpenAI API key validated")
            
        if not apify_api_key:
            logger.error("Apify API key is required in input")
            return
        logger.info("Apify API key validated")
        
        # Get location
        location = actor_input.get("location")
        if not location:
            logger.error("Location is required")
            return
        logger.info(f"Processing location: {location}")
            
        # Set environment variables for API keys
        os.environ["OPENAI_API_KEY"] = openai_api_key
        os.environ["APIFY_TOKEN"] = apify_api_key
        logger.info("Environment variables set")
            
        # Initialize OpenAI client
        try:
            openai_client = AsyncOpenAI(api_key=openai_api_key)
            logger.info("OpenAI client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            return
        
        # Initialize Apify client
        try:
            apify_client = ApifyClient(token=apify_api_key)
            logger.info("Apify client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Apify client: {str(e)}")
            return
            
        # Initialize agents with shared OpenAI client
        try:
            newsletter_agent = NewsletterAgent(client=openai_client)
            search_agent = SearchAgent(client=openai_client)
            extraction_agent = ExtractionAgent(client=openai_client)
            analysis_agent = AnalysisAgent(client=openai_client)
            logger.info("All agents initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agents: {str(e)}")
            return
        
        try:
            # Execute workflow
            logger.info("Starting source search...")
            urls = await search_agent.find_sources(location)
            if not urls:
                logger.error("No valid URLs found for the location")
                return
            logger.info(f"Found {len(urls)} valid URLs")
                
            logger.info("Starting data extraction...")
            market_data = await extraction_agent.extract_data(urls)
            if not market_data:
                logger.error("No market data could be extracted from URLs")
                return
            logger.info(f"Extracted market data from {len(market_data) if isinstance(market_data, list) else len(market_data.keys())} sources")
                
            logger.info("Starting market analysis...")
            analysis = await analysis_agent.analyze_market(market_data)
            if not analysis:
                logger.error("Market analysis failed to produce results")
                return
            logger.info("Market analysis completed successfully")
                
            logger.info("Generating newsletter...")
            newsletter = await newsletter_agent.generate_newsletter(location, market_data, analysis)
            if not newsletter:
                logger.error("Newsletter generation failed")
                return
            logger.info("Newsletter generated successfully")
            
            # Save output
            logger.info("Saving results...")
            await Actor.push_data({
                "location": location,
                "filtered_urls": urls,
                "market_data": market_data,
                "analysis": analysis,
                "newsletter": newsletter
            })
            logger.info("Results saved successfully")
            
        except Exception as e:
            logger.error(f"Actor failed with error: {str(e)}")
            logger.exception("Detailed error traceback:")
            raise

if __name__ == "__main__":
    Actor.main(main)
