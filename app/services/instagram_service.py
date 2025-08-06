"""Instagram-specific search and analysis service."""

import logging
import re
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class InstagramQueryBuilder:
    """Build Instagram-specific search queries with business indicators."""
    
    def __init__(self):
        """Initialize Instagram query builder."""
        self.base_site_query = "site:instagram.com"
        self.business_keywords = {
            "contact": ["contact", "email", "phone", "call", "dm", "message", "whatsapp", "telegram"],
            "services": ["book", "appointment", "service", "services", "business", "shop", "store"],
            "location": ["location", "address", "near", "area", "city", "local"],
            "professional": ["professional", "certified", "licensed", "expert", "specialist"],
            "business_types": [
                "restaurant", "cafe", "shop", "store", "salon", "spa", "gym", "fitness",
                "photographer", "artist", "designer", "coach", "trainer", "consultant",
                "agency", "studio", "clinic", "doctor", "dentist", "lawyer", "realtor"
            ]
        }
    
    def build_instagram_profile_query(
        self,
        business_type: Optional[str] = None,
        location: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        include_contact_info: bool = True
    ) -> str:
        """
        Build Instagram profile search query with business indicators.
        
        Args:
            business_type: Type of business (restaurant, salon, etc.)
            location: Location filter (city, area, etc.)
            keywords: Additional keywords to search for
            include_contact_info: Include contact information indicators
            
        Returns:
            Optimized Google search query for Instagram business profiles
        """
        query_parts = [self.base_site_query]
        
        # Add business type
        if business_type:
            if business_type.lower() in [t.lower() for t in self.business_keywords["business_types"]]:
                query_parts.append(f'"{business_type}"')
            else:
                query_parts.append(business_type)
        
        # Add location
        if location:
            query_parts.append(f'"{location}"')
        
        # Add contact information indicators
        if include_contact_info:
            contact_terms = " OR ".join([f'"{term}"' for term in self.business_keywords["contact"][:4]])
            query_parts.append(f"({contact_terms})")
        
        # Add business service indicators
        service_terms = " OR ".join([f'"{term}"' for term in self.business_keywords["services"][:4]])
        query_parts.append(f"({service_terms})")
        
        # Add custom keywords
        if keywords:
            for keyword in keywords[:3]:  # Limit to avoid query length issues
                query_parts.append(f'"{keyword}"')
        
        return " ".join(query_parts)
    
    def build_bio_business_query(self, business_indicators: List[str]) -> str:
        """
        Build query focusing on Instagram bios with specific business indicators.
        
        Args:
            business_indicators: List of business-related terms to search for
            
        Returns:
            Search query for Instagram profiles with business bios
        """
        query_parts = [self.base_site_query]
        
        # Focus on bio section and business indicators
        bio_terms = " OR ".join([f'"{indicator}"' for indicator in business_indicators[:5]])
        query_parts.append(f"({bio_terms})")
        
        # Add common bio business patterns
        query_parts.append('("DM for" OR "contact" OR "book" OR "order" OR "inquiries")')
        
        return " ".join(query_parts)
    
    def build_location_business_query(self, location: str, radius_keywords: List[str] = None) -> str:
        """
        Build location-specific business discovery query.
        
        Args:
            location: Target location (city, neighborhood, etc.)
            radius_keywords: Keywords for nearby/area searches
            
        Returns:
            Location-focused Instagram business search query
        """
        query_parts = [self.base_site_query]
        
        # Primary location
        query_parts.append(f'"{location}"')
        
        # Location variations
        if radius_keywords:
            location_terms = " OR ".join([f'"{location} {keyword}"' for keyword in radius_keywords[:3]])
            query_parts.append(f"({location_terms})")
        
        # Business location indicators
        query_parts.append('("located" OR "based" OR "serving" OR "area")')
        
        # Business identifiers
        query_parts.append('("business" OR "shop" OR "store" OR "service")')
        
        return " ".join(query_parts)


class InstagramPatternAnalyzer:
    """Analyze Instagram profile content for business patterns."""
    
    def __init__(self):
        """Initialize Instagram pattern analyzer."""
        self.business_patterns = self._compile_business_patterns()
        self.contact_patterns = self._compile_contact_patterns()
        self.professional_indicators = self._compile_professional_patterns()
    
    def _compile_business_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for business detection."""
        patterns = {
            "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', re.IGNORECASE),
            "phone": re.compile(r'(\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})', re.IGNORECASE),
            "website": re.compile(r'(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)', re.IGNORECASE),
            "dm_booking": re.compile(r'\b(dm|message|book|appointment|order|inquir[yi]es?)\b', re.IGNORECASE),
            "business_hours": re.compile(r'\b(open|closed|hours?|mon|tue|wed|thu|fri|sat|sun|\d+am|\d+pm)\b', re.IGNORECASE),
            "location_address": re.compile(r'\b\d+\s+[a-zA-Z\s]+(street|st|avenue|ave|road|rd|drive|dr|lane|ln|way|blvd|boulevard)\b', re.IGNORECASE),
            "price_indicators": re.compile(r'(\$\d+|\d+\$|price|cost|rate|fee|starting\s+at)', re.IGNORECASE)
        }
        return patterns
    
    def _compile_contact_patterns(self) -> Dict[str, re.Pattern]:
        """Compile contact-specific patterns."""
        patterns = {
            "whatsapp": re.compile(r'\b(whatsapp|wa\.me|whats?app)\b', re.IGNORECASE),
            "telegram": re.compile(r'\b(telegram|t\.me|@\w+)\b', re.IGNORECASE),
            "social_handle": re.compile(r'@[a-zA-Z0-9_]+', re.IGNORECASE),
            "call_to_action": re.compile(r'\b(call|text|dm|message|contact|book|order|visit)\b', re.IGNORECASE)
        }
        return patterns
    
    def _compile_professional_patterns(self) -> Dict[str, re.Pattern]:
        """Compile professional service patterns."""
        patterns = {
            "certifications": re.compile(r'\b(certified|licensed|professional|expert|specialist|qualified)\b', re.IGNORECASE),
            "experience": re.compile(r'\b(\d+\+?\s*(years?|yrs?)|experience[d]?|since\s+\d{4})\b', re.IGNORECASE),
            "services_offered": re.compile(r'\b(services?|consultation|treatment|therapy|training|coaching)\b', re.IGNORECASE),
            "business_model": re.compile(r'\b(freelance|agency|studio|clinic|practice|company|llc|inc)\b', re.IGNORECASE)
        }
        return patterns
    
    def analyze_bio_content(self, bio_text: str) -> Dict[str, Any]:
        """
        Analyze Instagram bio text for business indicators.
        
        Args:
            bio_text: Instagram bio/description text
            
        Returns:
            Dict with business analysis results and confidence scores
        """
        if not bio_text:
            return {"is_business": False, "confidence": 0.0, "indicators": {}}
        
        analysis = {
            "is_business": False,
            "confidence": 0.0,
            "indicators": {
                "contact_info": [],
                "business_signals": [],
                "professional_markers": [],
                "location_info": []
            },
            "extracted_data": {
                "emails": [],
                "phones": [],
                "websites": [],
                "social_handles": []
            }
        }
        
        # Extract contact information
        emails = self.business_patterns["email"].findall(bio_text)
        phones = self.business_patterns["phone"].findall(bio_text)
        websites = self.business_patterns["website"].findall(bio_text)
        
        analysis["extracted_data"]["emails"] = emails
        analysis["extracted_data"]["phones"] = phones
        analysis["extracted_data"]["websites"] = websites
        
        # Business signal scoring
        score = 0.0
        max_score = 10.0  # Maximum possible score
        
        # Contact information (high weight)
        if emails:
            analysis["indicators"]["contact_info"].append("email")
            score += 2.5
        if phones:
            analysis["indicators"]["contact_info"].append("phone")
            score += 2.5
        if websites:
            analysis["indicators"]["contact_info"].append("website")
            score += 2.0
        
        # Business patterns
        for pattern_name, pattern in self.business_patterns.items():
            if pattern_name in ["email", "phone", "website"]:
                continue
            if pattern.search(bio_text):
                analysis["indicators"]["business_signals"].append(pattern_name)
                score += 0.8
        
        # Professional patterns
        for pattern_name, pattern in self._compile_professional_patterns().items():
            if pattern.search(bio_text):
                analysis["indicators"]["professional_markers"].append(pattern_name)
                score += 0.6
        
        # Contact patterns
        for pattern_name, pattern in self._compile_contact_patterns().items():
            if pattern.search(bio_text):
                analysis["indicators"]["business_signals"].append(f"contact_{pattern_name}")
                score += 0.5
        
        # Calculate confidence
        analysis["confidence"] = min(score / max_score, 1.0)
        analysis["is_business"] = analysis["confidence"] > 0.3  # 30% threshold
        
        return analysis
    
    def extract_business_category(self, bio_text: str, title: str = "") -> Optional[str]:
        """
        Extract likely business category from bio and title.
        
        Args:
            bio_text: Instagram bio text
            title: Profile title/name
            
        Returns:
            Detected business category or None
        """
        combined_text = f"{title} {bio_text}".lower()
        
        categories = {
            "food_beverage": ["restaurant", "cafe", "bar", "catering", "food", "chef", "bakery", "pizza"],
            "beauty_wellness": ["salon", "spa", "beauty", "massage", "wellness", "skincare", "makeup", "nails"],
            "fitness_health": ["gym", "fitness", "trainer", "yoga", "pilates", "health", "nutrition", "coach"],
            "retail_fashion": ["shop", "store", "boutique", "fashion", "clothing", "jewelry", "accessories"],
            "professional_services": ["lawyer", "doctor", "dentist", "consultant", "agency", "marketing", "design"],
            "creative_arts": ["photographer", "artist", "designer", "studio", "creative", "photography", "art"],
            "home_services": ["cleaning", "repair", "construction", "plumbing", "electrical", "landscaping"]
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in combined_text:
                    return category
        
        return None


class InstagramSearchService:
    """Main service for Instagram profile search and analysis."""
    
    def __init__(self):
        """Initialize Instagram search service."""
        self.query_builder = InstagramQueryBuilder()
        self.pattern_analyzer = InstagramPatternAnalyzer()
    
    async def build_business_search_queries(
        self,
        business_type: Optional[str] = None,
        location: Optional[str] = None,
        keywords: Optional[List[str]] = None
    ) -> List[str]:
        """
        Build multiple Instagram business search queries for comprehensive coverage.
        
        Args:
            business_type: Type of business to search for
            location: Geographic location filter
            keywords: Additional search keywords
            
        Returns:
            List of optimized search queries
        """
        queries = []
        
        # Primary business query
        primary_query = self.query_builder.build_instagram_profile_query(
            business_type=business_type,
            location=location,
            keywords=keywords,
            include_contact_info=True
        )
        queries.append(primary_query)
        
        # Bio-focused query
        if business_type or keywords:
            bio_indicators = []
            if business_type:
                bio_indicators.append(business_type)
            if keywords:
                bio_indicators.extend(keywords[:3])
            
            bio_query = self.query_builder.build_bio_business_query(bio_indicators)
            queries.append(bio_query)
        
        # Location-specific query
        if location:
            location_query = self.query_builder.build_location_business_query(
                location=location,
                radius_keywords=["near", "area", "local"]
            )
            queries.append(location_query)
        
        logger.info(f"Generated {len(queries)} Instagram search queries")
        return queries
    
    async def analyze_instagram_profile(
        self,
        profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze Instagram profile data for business indicators.
        
        Args:
            profile_data: Profile data from crawling (title, description, etc.)
            
        Returns:
            Business analysis results with confidence scores
        """
        bio_text = profile_data.get("description", "")
        title = profile_data.get("title", "")
        
        # Analyze bio content
        bio_analysis = self.pattern_analyzer.analyze_bio_content(bio_text)
        
        # Extract business category
        business_category = self.pattern_analyzer.extract_business_category(bio_text, title)
        
        # Combine results
        analysis_result = {
            "profile_url": profile_data.get("url"),
            "profile_title": title,
            "business_analysis": bio_analysis,
            "business_category": business_category,
            "analysis_timestamp": profile_data.get("timestamp"),
            "metadata": {
                "has_bio": bool(bio_text),
                "bio_length": len(bio_text) if bio_text else 0,
                "has_contact_info": bool(bio_analysis.get("extracted_data", {}).get("emails") or 
                                      bio_analysis.get("extracted_data", {}).get("phones")),
                "confidence_tier": self._get_confidence_tier(bio_analysis.get("confidence", 0))
            }
        }
        
        return analysis_result
    
    def _get_confidence_tier(self, confidence: float) -> str:
        """Get confidence tier label."""
        if confidence >= 0.8:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        elif confidence >= 0.3:
            return "low"
        else:
            return "very_low"