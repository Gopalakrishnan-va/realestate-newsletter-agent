class NewsletterWriter:
    def __init__(self, openai_client):
        self.client = openai_client
        self.required_metrics = ['median_price', 'price_change', 'days_on_market']

    def _validate_source_data(self, market_data):
        """Validate and consolidate data from different sources."""
        valid_sources = {}
        
        for source, data in market_data.items():
            if not data or not isinstance(data, dict):
                continue
                
            metrics = {}
            # Extract core metrics if they exist
            if 'median_price' in data and data['median_price']:
                metrics['median_price'] = data['median_price']
            if 'price_change' in data and data['price_change']:
                metrics['price_change'] = data['price_change']
            if 'days_on_market' in data and data['days_on_market']:
                metrics['days_on_market'] = data['days_on_market']
            if 'price_per_sqft' in data and data['price_per_sqft']:
                metrics['price_per_sqft'] = data['price_per_sqft']
            
            # Extract additional metrics from Rocket data
            if source == 'rocket' and isinstance(data.get('text'), str):
                text = data['text']
                if "Neutral Market" in text:
                    metrics['market_type'] = "Neutral Market"
                elif "Seller's Market" in text:
                    metrics['market_type'] = "Seller's Market"
                elif "Buyer's Market" in text:
                    metrics['market_type'] = "Buyer's Market"
                
                # Extract inventory and sales data if available
                if "homes for sale" in text:
                    metrics['inventory'] = self._extract_inventory(text)
                if "homes sold" in text:
                    metrics['sales_volume'] = self._extract_sales(text)
                
            # Only include sources with actual data
            if metrics:
                valid_sources[source] = metrics
                
        return valid_sources

    def _extract_inventory(self, text):
        """Extract inventory numbers from text."""
        try:
            # Add logic to extract inventory numbers
            return None
        except:
            return None

    def _extract_sales(self, text):
        """Extract sales volume from text."""
        try:
            # Add logic to extract sales numbers
            return None
        except:
            return None

    def _format_market_data(self, market_data):
        """Format market data into sections for the newsletter."""
        valid_sources = self._validate_source_data(market_data)
        
        if not valid_sources:
            return "Error: No valid market data available"

        # Calculate averages across sources
        avg_metrics = {
            'median_price': [],
            'price_change': [],
            'days_on_market': [],
            'price_per_sqft': []
        }
        
        for source_data in valid_sources.values():
            for metric, values in avg_metrics.items():
                if metric in source_data:
                    values.append(source_data[metric])

        # Format market insights
        insights = []
        
        # Add price insights
        if avg_metrics['median_price']:
            median_price = sum(avg_metrics['median_price']) / len(avg_metrics['median_price'])
            insights.append(f"The median home price is ${median_price:,.0f}")
        
        if avg_metrics['price_change']:
            avg_change = sum(avg_metrics['price_change']) / len(avg_metrics['price_change'])
            insights.append(f"Prices have changed by {avg_change:.1f}% over the past year")
        
        if avg_metrics['days_on_market']:
            avg_dom = sum(avg_metrics['days_on_market']) / len(avg_metrics['days_on_market'])
            insights.append(f"Homes are selling in an average of {avg_dom:.0f} days")

        # Add market type if available from Rocket
        rocket_data = valid_sources.get('rocket', {})
        if 'market_type' in rocket_data:
            insights.append(f"The area is currently a {rocket_data['market_type']}")

        # Add inventory insights if available
        if 'inventory' in rocket_data:
            insights.append(f"There are currently {rocket_data['inventory']:,} homes for sale")

        return {
            'insights': insights,
            'averages': {
                'median_price': sum(avg_metrics['median_price']) / len(avg_metrics['median_price']) if avg_metrics['median_price'] else None,
                'price_change': sum(avg_metrics['price_change']) / len(avg_metrics['price_change']) if avg_metrics['price_change'] else None,
                'days_on_market': sum(avg_metrics['days_on_market']) / len(avg_metrics['days_on_market']) if avg_metrics['days_on_market'] else None
            },
            'sources': list(valid_sources.keys())
        }

    def write_newsletter(self, location, market_data):
        """Generate a real estate market newsletter."""
        try:
            formatted_data = self._format_market_data(market_data)
            
            if isinstance(formatted_data, str) and formatted_data.startswith("Error"):
                return formatted_data

            # Create system prompt for the model
            system_prompt = """You are a professional real estate market analyst writing a newsletter.
            IMPORTANT FORMATTING RULES:
            1. DO NOT include any tables or grid-like data presentations
            2. Present all data in a narrative, paragraph format
            3. Use bullet points sparingly and only for recommendations
            4. Write in a clear, flowing style that connects insights naturally
            5. Keep the tone professional and avoid emojis
            6. Focus on telling the market story rather than listing data points
            7. Keep sections concise and impactful
            8. When presenting numbers, integrate them smoothly into sentences
            9. Avoid markdown formatting except for section headers
            10. Do not include comparison grids or charts"""

            # Create user prompt with formatted data
            user_prompt = f"""Write a real estate market newsletter for {location} that weaves these insights into a cohesive narrative:

            Available Market Insights:
            {chr(10).join('- ' + insight for insight in formatted_data['insights'])}
            
            Based on data from: {', '.join(formatted_data['sources']).title()}
            
            Structure the newsletter as follows:
            1. Title and Date
            2. Executive Summary (2-3 sentences on key trends)
            3. Current Market Conditions (integrate price and market type insights)
            4. Market Activity and Trends (blend sales pace and price trends)
            5. Future Outlook (brief forecast based on current trends)
            6. Buyer and Seller Recommendations (3-4 actionable points each)
            
            IMPORTANT:
            - DO NOT include any tables or data grids
            - Present all metrics within flowing paragraphs
            - Focus on telling a coherent market story
            - Keep the writing style professional and straightforward
            - Integrate numbers naturally into sentences
            - Use minimal formatting - only use ## for section headers"""

            # Generate newsletter using OpenAI
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Error generating newsletter: {str(e)}" 