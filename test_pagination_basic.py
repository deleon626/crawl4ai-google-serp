#!/usr/bin/env python3
"""
Quick test script for pagination functionality.
Run this to verify the pagination enhancements are working correctly.
"""

import asyncio
import sys
import os
import logging

# Add the app directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.models.serp import SearchRequest, PaginationMetadata
from app.utils.pagination import PaginationHelper

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_pagination_models():
    """Test that pagination models work correctly."""
    print("🧪 Testing Pagination Models...")
    
    # Test SearchRequest with new pagination fields
    try:
        search_request = SearchRequest(
            query="test pagination",
            page=2,
            results_per_page=15
        )
        print(f"✅ SearchRequest: page={search_request.page}, results_per_page={search_request.results_per_page}")
    except Exception as e:
        print(f"❌ SearchRequest failed: {str(e)}")
        return False
    
    # Test PaginationMetadata
    try:
        pagination = PaginationMetadata(
            current_page=2,
            results_per_page=10,
            total_results_estimate=150000,
            total_pages_estimate=15000,
            has_next_page=True,
            has_previous_page=True,
            page_range_start=11,
            page_range_end=20
        )
        print(f"✅ PaginationMetadata: page {pagination.current_page}, "
              f"total estimate {pagination.total_results_estimate:,}")
    except Exception as e:
        print(f"❌ PaginationMetadata failed: {str(e)}")
        return False
    
    return True


def test_pagination_utilities():
    """Test pagination utility functions."""
    print("\n🛠️ Testing Pagination Utilities...")
    
    helper = PaginationHelper()
    
    # Test calculate_start_index
    try:
        start_index = helper.calculate_start_index(page=3, results_per_page=10)
        expected = 20  # (3-1) * 10 = 20
        assert start_index == expected, f"Expected {expected}, got {start_index}"
        print(f"✅ calculate_start_index: page 3 → start index {start_index}")
    except Exception as e:
        print(f"❌ calculate_start_index failed: {str(e)}")
        return False
    
    # Test calculate_total_pages
    try:
        total_pages = helper.calculate_total_pages(total_results=95, results_per_page=10)
        expected = 10  # ceil(95/10) = 10
        assert total_pages == expected, f"Expected {expected}, got {total_pages}"
        print(f"✅ calculate_total_pages: 95 results → {total_pages} pages")
    except Exception as e:
        print(f"❌ calculate_total_pages failed: {str(e)}")
        return False
    
    # Test extract_total_results_from_text
    try:
        test_text = "About 1,234,567 results (0.45 seconds)"
        total_results = helper.extract_total_results_from_text(test_text)
        expected = 1234567
        assert total_results == expected, f"Expected {expected}, got {total_results}"
        print(f"✅ extract_total_results_from_text: extracted {total_results:,}")
    except Exception as e:
        print(f"❌ extract_total_results_from_text failed: {str(e)}")
        return False
    
    # Test generate_pagination_metadata
    try:
        pagination = helper.generate_pagination_metadata(
            current_page=1,
            results_per_page=10,
            actual_results_count=10,
            total_results_estimate=150000
        )
        print(f"✅ generate_pagination_metadata: page {pagination.current_page}, "
              f"has_next={pagination.has_next_page}, range={pagination.page_range_start}-{pagination.page_range_end}")
    except Exception as e:
        print(f"❌ generate_pagination_metadata failed: {str(e)}")
        return False
    
    return True


def test_batch_pagination_models():
    """Test batch pagination models."""
    print("\n📦 Testing Batch Pagination Models...")
    
    try:
        from app.models.serp import BatchPaginationRequest, BatchPaginationResponse, BatchPaginationSummary
        
        # Test BatchPaginationRequest
        batch_request = BatchPaginationRequest(
            query="test batch pagination",
            max_pages=3,
            results_per_page=10,
            start_page=1
        )
        print(f"✅ BatchPaginationRequest: {batch_request.max_pages} pages, "
              f"{batch_request.results_per_page} results/page")
        
        # Test BatchPaginationSummary
        summary = BatchPaginationSummary(
            total_results_estimate=150000,
            results_per_page=10,
            pages_requested=3,
            pages_fetched=3,
            start_page=1,
            end_page=3
        )
        print(f"✅ BatchPaginationSummary: {summary.pages_fetched}/{summary.pages_requested} pages")
        
    except Exception as e:
        print(f"❌ Batch pagination models failed: {str(e)}")
        return False
    
    return True


def test_url_building():
    """Test that URL building includes pagination parameters."""
    print("\n🔗 Testing URL Building...")
    
    try:
        search_request = SearchRequest(
            query="test",
            page=3,
            results_per_page=20
        )
        
        # Import and test the URL building logic
        from app.clients.bright_data import BrightDataClient
        client = BrightDataClient()
        
        url = client._build_google_url(search_request)
        
        # Check that the URL contains expected parameters
        assert "start=40" in url, f"Expected start=40 in URL: {url}"  # (3-1)*20 = 40
        assert "num=20" in url, f"Expected num=20 in URL: {url}"
        assert "q=test" in url, f"Expected q=test in URL: {url}"
        
        print(f"✅ URL building: {url}")
        
    except Exception as e:
        print(f"❌ URL building failed: {str(e)}")
        return False
    
    return True


async def main():
    """Run all pagination tests."""
    print("🚀 Testing Enhanced Pagination Functionality")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Run all tests
    tests = [
        test_pagination_models,
        test_pagination_utilities,
        test_batch_pagination_models,
        test_url_building,
    ]
    
    for test_func in tests:
        try:
            result = test_func()
            if not result:
                all_tests_passed = False
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {str(e)}")
            all_tests_passed = False
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 All pagination tests passed!")
        print("\nPagination functionality is ready to use:")
        print("- Enhanced SearchRequest/SearchResponse models with pagination metadata")
        print("- Comprehensive pagination utilities and validation")
        print("- Batch pagination support for multi-page requests") 
        print("- Google SERP parser with total results extraction")
        print("- Updated API endpoints with pagination support")
    else:
        print("⚠️ Some pagination tests failed. Check the output above.")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner failed: {str(e)}")
        sys.exit(1)