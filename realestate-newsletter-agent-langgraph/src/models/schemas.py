from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class URLData(BaseModel):
    """Data structure for URLs with their source information"""
    url: str
    source: str

class MarketMetrics(BaseModel):
    """Structure for real estate market metrics"""
    median_price: Optional[float] = None
    price_change: Optional[float] = None
    days_on_market: Optional[int] = None
    inventory: Optional[int] = None
    price_per_sqft: Optional[float] = None
    source_date: Optional[str] = None

class AgentState(BaseModel):
    """State management for the real estate newsletter agent"""
    location: str = Field(..., description="Target location for market analysis")
    search_urls: List[str] = Field(default_factory=list, description="Initial search results")
    filtered_urls: List[URLData] = Field(default_factory=list, description="Filtered and validated URLs")
    final_urls: List[URLData] = Field(default_factory=list, description="Final URLs for data extraction")
    market_data: Dict[str, MarketMetrics] = Field(default_factory=dict, description="Extracted market data")
    errors: List[str] = Field(default_factory=list, description="Error messages during processing")
    location_valid: bool = Field(default=False, description="Location validation status")
    analysis_complete: bool = Field(default=False, description="Analysis completion status")
    newsletter: Optional[str] = None 