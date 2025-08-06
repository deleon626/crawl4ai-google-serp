"""Keyword extraction and consolidation service."""

import logging
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass
import math

logger = logging.getLogger(__name__)


@dataclass
class KeywordInfo:
    """Information about an extracted keyword."""
    keyword: str
    frequency: int
    relevance_score: float
    category: str
    variations: List[str]
    context_examples: List[str]


class TextPreprocessor:
    """Preprocess text for keyword extraction."""
    
    def __init__(self):
        """Initialize text preprocessor."""
        self.stop_words = self._get_stop_words()
        self.business_keywords = self._get_business_keywords()
        
    def _get_stop_words(self) -> Set[str]:
        """Get common English stop words."""
        return {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 
            'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 
            'will', 'with', 'we', 'you', 'your', 'our', 'my', 'me', 'i', 'am', 
            'this', 'these', 'those', 'they', 'them', 'their', 'his', 'her', 'him',
            'but', 'or', 'if', 'can', 'could', 'would', 'should', 'may', 'might',
            'get', 'got', 'have', 'had', 'do', 'did', 'does', 'done', 'go', 'went'
        }
    
    def _get_business_keywords(self) -> Dict[str, List[str]]:
        """Get business-related keywords by category."""
        return {
            "services": [
                "service", "services", "consultation", "consultations", "appointment", 
                "appointments", "booking", "bookings", "treatment", "treatments",
                "session", "sessions", "class", "classes", "workshop", "workshops"
            ],
            "business_types": [
                "restaurant", "cafe", "bar", "salon", "spa", "gym", "fitness", "studio",
                "shop", "store", "boutique", "clinic", "office", "agency", "company",
                "business", "enterprise", "practice", "firm", "center", "centre"
            ],
            "professional": [
                "professional", "certified", "licensed", "expert", "specialist", "qualified",
                "experienced", "trained", "skilled", "master", "certified", "accredited"
            ],
            "contact": [
                "contact", "call", "phone", "email", "message", "dm", "book", "order",
                "inquire", "inquiry", "inquiries", "appointment", "schedule", "reserve"
            ],
            "location": [
                "located", "based", "serving", "area", "local", "near", "city", "town",
                "neighborhood", "district", "region", "zone", "address", "location"
            ]
        }
    
    def preprocess_text(self, text: str) -> List[str]:
        """
        Preprocess text for keyword extraction.
        
        Args:
            text: Input text to preprocess
            
        Returns:
            List of cleaned tokens
        """
        if not text:
            return []
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs, emails, and special characters but keep important punctuation
        text = re.sub(r'https?://[^\s]+', '', text)
        text = re.sub(r'\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b', '', text)
        text = re.sub(r'[^\w\s&-]', ' ', text)
        
        # Split into tokens
        tokens = text.split()
        
        # Filter tokens
        filtered_tokens = []
        for token in tokens:
            # Remove pure numbers unless they seem meaningful
            if token.isdigit() and len(token) < 4:
                continue
            
            # Remove very short tokens
            if len(token) < 2:
                continue
            
            # Remove stop words
            if token in self.stop_words:
                continue
            
            # Clean token
            token = token.strip('-&')
            if token:
                filtered_tokens.append(token)
        
        return filtered_tokens
    
    def extract_phrases(self, text: str, max_phrase_length: int = 3) -> List[str]:
        """
        Extract meaningful phrases from text.
        
        Args:
            text: Input text
            max_phrase_length: Maximum words per phrase
            
        Returns:
            List of extracted phrases
        """
        tokens = self.preprocess_text(text)
        phrases = []
        
        # Extract n-grams
        for n in range(1, max_phrase_length + 1):
            for i in range(len(tokens) - n + 1):
                phrase = " ".join(tokens[i:i + n])
                phrases.append(phrase)
        
        return phrases


class KeywordExtractor:
    """Extract keywords using TF-IDF-like scoring."""
    
    def __init__(self):
        """Initialize keyword extractor."""
        self.preprocessor = TextPreprocessor()
    
    def extract_keywords(
        self, 
        text: str, 
        max_keywords: int = 20,
        include_phrases: bool = True
    ) -> List[KeywordInfo]:
        """
        Extract keywords from text using frequency and relevance scoring.
        
        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords to return
            include_phrases: Whether to include multi-word phrases
            
        Returns:
            List of KeywordInfo objects sorted by relevance
        """
        if not text:
            return []
        
        # Get single words and phrases
        single_words = self.preprocessor.preprocess_text(text)
        phrases = self.preprocessor.extract_phrases(text, max_phrase_length=3) if include_phrases else []
        
        # Combine and count
        all_terms = single_words + phrases
        term_counts = Counter(all_terms)
        
        # Calculate relevance scores
        keywords = []
        for term, frequency in term_counts.items():
            if frequency > 0:  # Basic filtering
                relevance_score = self._calculate_relevance_score(
                    term, frequency, len(all_terms), text
                )
                
                if relevance_score > 0.1:  # Minimum relevance threshold
                    category = self._categorize_keyword(term)
                    variations = self._find_variations(term, term_counts)
                    context_examples = self._extract_context(term, text)
                    
                    keywords.append(KeywordInfo(
                        keyword=term,
                        frequency=frequency,
                        relevance_score=relevance_score,
                        category=category,
                        variations=variations,
                        context_examples=context_examples
                    ))
        
        # Sort by relevance score and limit results
        keywords.sort(key=lambda x: x.relevance_score, reverse=True)
        return keywords[:max_keywords]
    
    def _calculate_relevance_score(
        self, term: str, frequency: int, total_terms: int, full_text: str
    ) -> float:
        """Calculate relevance score for a term."""
        # Base TF score
        tf_score = frequency / total_terms
        
        # Length bonus (prefer meaningful terms)
        length_bonus = min(len(term) / 10, 1.0)
        
        # Business relevance bonus
        business_bonus = self._get_business_relevance_bonus(term)
        
        # Position bonus (terms at beginning/end might be more important)
        position_bonus = self._get_position_bonus(term, full_text)
        
        # Phrase bonus (multi-word terms often more meaningful)
        phrase_bonus = 0.2 if " " in term else 0.0
        
        # Combine scores
        relevance_score = (
            tf_score * 0.4 + 
            length_bonus * 0.2 + 
            business_bonus * 0.2 + 
            position_bonus * 0.1 + 
            phrase_bonus * 0.1
        )
        
        return min(relevance_score, 1.0)
    
    def _get_business_relevance_bonus(self, term: str) -> float:
        """Get bonus score for business-relevant terms."""
        business_keywords = self.preprocessor.business_keywords
        term_lower = term.lower()
        
        bonus = 0.0
        for category, keywords in business_keywords.items():
            for keyword in keywords:
                if keyword in term_lower or term_lower in keyword:
                    # Higher bonus for exact matches
                    if keyword == term_lower:
                        bonus = max(bonus, 0.8)
                    else:
                        bonus = max(bonus, 0.4)
        
        # Additional bonuses for common business patterns
        if any(pattern in term_lower for pattern in ["& ", " and ", "professional", "certified"]):
            bonus = max(bonus, 0.3)
        
        return bonus
    
    def _get_position_bonus(self, term: str, full_text: str) -> float:
        """Get bonus for term position in text."""
        text_lower = full_text.lower()
        term_lower = term.lower()
        
        # Find first occurrence position
        index = text_lower.find(term_lower)
        if index == -1:
            return 0.0
        
        text_length = len(text_lower)
        relative_position = index / text_length if text_length > 0 else 0
        
        # Bonus for early positions (bio starts are important)
        if relative_position < 0.2:
            return 0.3
        elif relative_position < 0.5:
            return 0.1
        else:
            return 0.0
    
    def _categorize_keyword(self, term: str) -> str:
        """Categorize keyword by business type."""
        term_lower = term.lower()
        business_keywords = self.preprocessor.business_keywords
        
        for category, keywords in business_keywords.items():
            for keyword in keywords:
                if keyword in term_lower or term_lower == keyword:
                    return category
        
        # Additional categorization logic
        if any(word in term_lower for word in ["food", "restaurant", "cafe", "bar"]):
            return "food_beverage"
        elif any(word in term_lower for word in ["beauty", "salon", "spa", "makeup"]):
            return "beauty_wellness"
        elif any(word in term_lower for word in ["fitness", "gym", "training", "coach"]):
            return "fitness_health"
        elif any(word in term_lower for word in ["photo", "photography", "creative", "design"]):
            return "creative"
        else:
            return "general"
    
    def _find_variations(self, term: str, term_counts: Counter) -> List[str]:
        """Find variations of a term in the text."""
        variations = []
        term_lower = term.lower()
        
        # Look for similar terms
        for other_term in term_counts:
            if other_term.lower() != term_lower:
                # Check if terms are related (contain each other)
                if (term_lower in other_term.lower() or 
                    other_term.lower() in term_lower):
                    variations.append(other_term)
        
        return variations[:3]  # Limit variations
    
    def _extract_context(self, term: str, full_text: str, context_length: int = 50) -> List[str]:
        """Extract context examples for a term."""
        term_lower = term.lower()
        text_lower = full_text.lower()
        contexts = []
        
        # Find all occurrences
        start = 0
        while True:
            index = text_lower.find(term_lower, start)
            if index == -1:
                break
            
            # Extract context around the term
            context_start = max(0, index - context_length)
            context_end = min(len(full_text), index + len(term) + context_length)
            context = full_text[context_start:context_end].strip()
            
            if context and context not in contexts:
                contexts.append(context)
            
            start = index + len(term_lower)
        
        return contexts[:2]  # Limit context examples


class KeywordGrouper:
    """Group related keywords together."""
    
    def __init__(self):
        """Initialize keyword grouper."""
        self.semantic_groups = {
            "business_services": ["service", "services", "consultation", "appointment", "booking"],
            "contact_info": ["contact", "call", "email", "message", "dm", "phone"],
            "location": ["location", "located", "address", "area", "local", "near"],
            "professional": ["professional", "expert", "certified", "licensed", "qualified"],
            "business_type": ["business", "company", "shop", "store", "studio", "clinic"]
        }
    
    def group_keywords(self, keywords: List[KeywordInfo]) -> Dict[str, List[KeywordInfo]]:
        """
        Group related keywords together.
        
        Args:
            keywords: List of extracted keywords
            
        Returns:
            Dict mapping group names to lists of related keywords
        """
        groups = defaultdict(list)
        ungrouped = []
        
        for keyword in keywords:
            keyword_lower = keyword.keyword.lower()
            grouped = False
            
            # Try to match to semantic groups
            for group_name, group_terms in self.semantic_groups.items():
                if any(term in keyword_lower for term in group_terms):
                    groups[group_name].append(keyword)
                    grouped = True
                    break
            
            # Use category as group if not semantically grouped
            if not grouped:
                if keyword.category != "general":
                    groups[keyword.category].append(keyword)
                    grouped = True
            
            if not grouped:
                ungrouped.append(keyword)
        
        # Add ungrouped keywords to a general category
        if ungrouped:
            groups["other"] = ungrouped
        
        # Sort groups by total relevance
        for group_keywords in groups.values():
            group_keywords.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return dict(groups)


class KeywordExtractionService:
    """Main service for keyword extraction and consolidation."""
    
    def __init__(self):
        """Initialize keyword extraction service."""
        self.extractor = KeywordExtractor()
        self.grouper = KeywordGrouper()
    
    async def extract_and_group_keywords(
        self, 
        text: str,
        max_keywords: int = 20,
        include_phrases: bool = True,
        group_keywords: bool = True
    ) -> Dict[str, Any]:
        """
        Extract keywords from text and group them by relevance and category.
        
        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords to extract
            include_phrases: Whether to include multi-word phrases
            group_keywords: Whether to group related keywords
            
        Returns:
            Dict with extracted keywords and groupings
        """
        # Extract keywords
        keywords = self.extractor.extract_keywords(
            text=text,
            max_keywords=max_keywords,
            include_phrases=include_phrases
        )
        
        # Group keywords if requested
        groups = {}
        if group_keywords and keywords:
            groups = self.grouper.group_keywords(keywords)
        
        # Generate summary statistics
        total_keywords = len(keywords)
        high_relevance_count = len([k for k in keywords if k.relevance_score > 0.6])
        business_keywords = [k for k in keywords if k.category in [
            "services", "business_types", "professional", "contact", "location"
        ]]
        
        result = {
            "keywords": keywords,
            "groups": groups,
            "summary": {
                "total_keywords": total_keywords,
                "high_relevance_count": high_relevance_count,
                "business_keywords_count": len(business_keywords),
                "top_categories": self._get_top_categories(keywords),
                "avg_relevance_score": sum(k.relevance_score for k in keywords) / total_keywords if total_keywords > 0 else 0.0
            },
            "top_business_keywords": business_keywords[:10]
        }
        
        logger.info(f"Extracted {total_keywords} keywords, {len(business_keywords)} business-relevant")
        return result
    
    def _get_top_categories(self, keywords: List[KeywordInfo]) -> List[Tuple[str, int]]:
        """Get top categories by keyword count."""
        category_counts = Counter(keyword.category for keyword in keywords)
        return category_counts.most_common(5)