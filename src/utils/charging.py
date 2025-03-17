"""
Shared utilities for pay-per-event charging
"""

import logging
from decimal import Decimal
from typing import Dict
from apify import Actor

logger = logging.getLogger(__name__)

# Define all chargeable events and their prices
EVENTS = {
    'search-initialized': '0.02',
    'url-processed': '0.02',
    'data-extracted': '0.02',
    'market-analyzed': '0.02',
    'newsletter-generated': '0.50'
}

def register_events():
    """Register all chargeable events with their prices"""
    try:
        charging_manager = Actor.get_charging_manager()
        for event_name, price in EVENTS.items():
            charging_manager.register_event(event_name, price)
        logger.info("Successfully registered all chargeable events")
    except Exception as e:
        logger.error(f"Error registering events: {str(e)}")

async def charge_event(event_name: str, count: int = 1) -> bool:
    """Charge for an event using predefined prices
    
    Args:
        event_name: Name of the event to charge for
        count: Number of events to charge for (default: 1)
        
    Returns:
        bool: True if charging was successful, False otherwise
    """
    try:
        if event_name not in EVENTS:
            logger.warning(f"Unknown event: {event_name}")
            return False
            
        await Actor.charge(event_name, count)
        logger.info(f"Successfully charged for {count} {event_name} event(s)")
        return True
    except Exception as e:
        logger.warning(f"Failed to charge for {event_name}: {str(e)}")
        return False 