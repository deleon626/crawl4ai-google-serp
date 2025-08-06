"""
Pagination utilities for Google SERP API.

This module provides helper functions and classes for handling pagination
in search results, calculating metadata, and validating pagination parameters.
"""

import logging
import math
import re
from typing import Optional, Tuple, Dict, Any
from app.models.serp import PaginationMetadata

# Set up logging
logger = logging.getLogger(__name__)


class PaginationHelper:
    """
    Helper class for pagination calculations and utilities.
    
    Provides methods for calculating pagination metadata, validating parameters,
    and extracting total results from Google search pages.
    """
    
    # Common Google results patterns
    GOOGLE_RESULTS_PATTERNS = [
        r'About\s+([\d,]+)\s+results',              # "About 1,234,567 results"
        r'([\d,]+)\s+results',                       # "1,234,567 results"  
        r'Showing\s+[\d,]+-[\d,]+\s+of\s+([\d,]+)', # "Showing 1-10 of 1,234,567"
        r'Page\s+\d+\s+of\s+about\s+([\d,]+)',      # "Page 1 of about 1,234,567"
    ]
    
    @staticmethod
    def calculate_start_index(page: int, results_per_page: int) -> int:
        """
        Calculate the starting index for a given page.
        
        Args:
            page: Page number (1-based)
            results_per_page: Number of results per page
            
        Returns:
            Starting index for the page (0-based for Google's start parameter)
        """
        if page < 1:
            raise ValueError("Page number must be >= 1")
        if results_per_page < 1:
            raise ValueError("Results per page must be >= 1")
            
        return (page - 1) * results_per_page
    
    @staticmethod
    def calculate_total_pages(total_results: Optional[int], results_per_page: int) -> Optional[int]:
        """
        Calculate total pages based on total results.
        
        Args:
            total_results: Total number of results (None if unknown)
            results_per_page: Number of results per page
            
        Returns:
            Total pages (None if total_results is None)
        """
        if total_results is None:
            return None
            
        if results_per_page < 1:
            raise ValueError("Results per page must be >= 1")
            
        return math.ceil(total_results / results_per_page)
    
    @staticmethod
    def calculate_page_range(page: int, results_per_page: int, actual_results_count: int) -> Tuple[int, int]:
        """
        Calculate the range of result numbers for a page.
        
        Args:
            page: Page number (1-based)
            results_per_page: Number of results per page
            actual_results_count: Actual number of results on this page
            
        Returns:
            Tuple of (start_number, end_number) for result range
        """
        if page < 1:
            raise ValueError("Page number must be >= 1")
        if results_per_page < 1:
            raise ValueError("Results per page must be >= 1")
        if actual_results_count < 0:
            raise ValueError("Actual results count must be >= 0")
            
        start = (page - 1) * results_per_page + 1
        end = start + actual_results_count - 1
        
        # Handle edge case of no results
        if actual_results_count == 0:
            start = 0
            end = 0
            
        return start, end
    
    @staticmethod
    def extract_total_results_from_text(text: str) -> Optional[int]:
        """
        Extract total results count from Google search page text.
        
        Args:
            text: Text content from Google search page
            
        Returns:
            Total results count or None if not found
        """
        if not text:
            return None
            
        # Try each pattern
        for pattern in PaginationHelper.GOOGLE_RESULTS_PATTERNS:
            try:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Extract number and remove commas
                    number_str = match.group(1).replace(',', '').replace(' ', '')
                    total_results = int(number_str)
                    
                    # Basic validation - Google results should be reasonable
                    if 0 <= total_results <= 10**12:  # Up to 1 trillion results
                        logger.debug(f"Extracted total results: {total_results:,} using pattern: {pattern}")
                        return total_results
                    else:
                        logger.warning(f"Extracted unreasonable result count: {total_results}")
                        
            except (ValueError, AttributeError) as e:
                logger.debug(f"Pattern '{pattern}' failed: {str(e)}")
                continue
        
        logger.debug("No total results pattern matched in text")
        return None
    
    @staticmethod
    def generate_pagination_metadata(
        current_page: int,
        results_per_page: int,
        actual_results_count: int,
        total_results_estimate: Optional[int] = None,
        max_page_limit: int = 1000
    ) -> PaginationMetadata:
        """
        Generate comprehensive pagination metadata.
        
        Args:
            current_page: Current page number (1-based)
            results_per_page: Number of results per page  
            actual_results_count: Actual results on current page
            total_results_estimate: Estimated total results (optional)
            max_page_limit: Maximum reasonable page limit for Google
            
        Returns:
            PaginationMetadata object with all pagination information
        """
        if current_page < 1:
            raise ValueError("Current page must be >= 1")
        if results_per_page < 1:
            raise ValueError("Results per page must be >= 1")
        if actual_results_count < 0:
            raise ValueError("Actual results count must be >= 0")
            
        # Calculate total pages estimate
        total_pages_estimate = None
        if total_results_estimate is not None:
            total_pages_estimate = PaginationHelper.calculate_total_pages(
                total_results_estimate, results_per_page
            )
            # Apply reasonable limit (Google typically shows max 1000 pages)
            if total_pages_estimate and total_pages_estimate > max_page_limit:
                total_pages_estimate = max_page_limit
        
        # Calculate page range
        page_start, page_end = PaginationHelper.calculate_page_range(
            current_page, results_per_page, actual_results_count
        )
        
        # Determine navigation availability
        has_previous_page = current_page > 1
        has_next_page = True  # Default assumption
        
        # Refine has_next_page based on available information
        if total_pages_estimate is not None:
            has_next_page = current_page < total_pages_estimate
        elif actual_results_count < results_per_page:
            # If we got fewer results than requested, likely no more pages
            has_next_page = False
            
        # Apply max page limit
        if current_page >= max_page_limit:
            has_next_page = False
        
        return PaginationMetadata(
            current_page=current_page,
            results_per_page=results_per_page,
            total_results_estimate=total_results_estimate,
            total_pages_estimate=total_pages_estimate,
            has_next_page=has_next_page,
            has_previous_page=has_previous_page,
            page_range_start=page_start,
            page_range_end=page_end
        )
    
    @staticmethod
    def validate_pagination_params(
        page: int,
        results_per_page: int,
        max_page: int = 100,
        max_results_per_page: int = 100
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate pagination parameters.
        
        Args:
            page: Page number to validate
            results_per_page: Results per page to validate
            max_page: Maximum allowed page number
            max_results_per_page: Maximum results per page
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(page, int) or page < 1:
            return False, "Page must be a positive integer >= 1"
            
        if not isinstance(results_per_page, int) or results_per_page < 1:
            return False, "Results per page must be a positive integer >= 1"
            
        if page > max_page:
            return False, f"Page cannot exceed {max_page}"
            
        if results_per_page > max_results_per_page:
            return False, f"Results per page cannot exceed {max_results_per_page}"
        
        return True, None
    
    @staticmethod
    def calculate_batch_pagination_summary(
        query: str,
        start_page: int,
        pages_requested: int,
        pages_fetched: int,
        results_per_page: int,
        total_results_estimate: Optional[int] = None,
        processing_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate summary metadata for batch pagination requests.
        
        Args:
            query: Search query
            start_page: Starting page number
            pages_requested: Number of pages requested
            pages_fetched: Number of pages successfully fetched
            results_per_page: Results per page
            total_results_estimate: Estimated total results
            processing_time: Total processing time in seconds
            
        Returns:
            Dictionary with batch pagination summary
        """
        end_page = start_page + pages_requested - 1
        
        return {
            "total_results_estimate": total_results_estimate,
            "results_per_page": results_per_page,
            "pages_requested": pages_requested,
            "pages_fetched": pages_fetched,
            "start_page": start_page,
            "end_page": end_page,
            "batch_processing_time": processing_time,
            "success_rate": pages_fetched / pages_requested if pages_requested > 0 else 0.0
        }


class PaginationError(Exception):
    """Exception raised for pagination-related errors."""
    pass


def create_pagination_helper() -> PaginationHelper:
    """Factory function to create a PaginationHelper instance."""
    return PaginationHelper()