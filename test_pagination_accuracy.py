#!/usr/bin/env python3
"""
Pagination Mathematical Accuracy Test

This script validates the mathematical accuracy of pagination calculations
and URL building logic to ensure proper result continuity.
"""

import asyncio
import sys
import os
import logging
from typing import Dict, Any, List
from urllib.parse import parse_qs, urlparse

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.models.serp import SearchRequest
from app.clients.bright_data import BrightDataClient
from app.utils.pagination import PaginationHelper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PaginationAccuracyTester:
    """Test pagination mathematical accuracy and URL building logic."""
    
    def __init__(self):
        """Initialize the tester."""
        self.pagination_helper = PaginationHelper()
        self.bright_data_client = BrightDataClient()
    
    def test_pagination_calculations(self) -> Dict[str, Any]:
        """Test core pagination calculation functions."""
        logger.info("🧮 Testing pagination mathematical calculations")
        
        test_cases = [
            # (page, results_per_page, expected_start_index)
            (1, 10, 0),
            (1, 100, 0),
            (2, 10, 10),
            (2, 100, 100),
            (3, 10, 20),
            (3, 100, 200),
            (5, 50, 200),
            (10, 100, 900),
        ]
        
        results = []
        all_passed = True
        
        for page, results_per_page, expected_start in test_cases:
            try:
                actual_start = self.pagination_helper.calculate_start_index(page, results_per_page)
                passed = actual_start == expected_start
                all_passed &= passed
                
                status = "✅" if passed else "❌"
                results.append({
                    'page': page,
                    'results_per_page': results_per_page,
                    'expected_start': expected_start,
                    'actual_start': actual_start,
                    'passed': passed
                })
                
                logger.info(f"{status} Page {page}, {results_per_page}/page → start={actual_start} (expected {expected_start})")
                
            except Exception as e:
                logger.error(f"❌ Error calculating start index for page {page}: {str(e)}")
                all_passed = False
                results.append({
                    'page': page,
                    'results_per_page': results_per_page,
                    'error': str(e),
                    'passed': False
                })
        
        return {
            'test_name': 'pagination_calculations',
            'all_passed': all_passed,
            'test_cases': results,
            'total_tests': len(test_cases),
            'passed_tests': sum(1 for r in results if r.get('passed', False))
        }
    
    def test_url_building_logic(self) -> Dict[str, Any]:
        """Test URL building logic for different pagination scenarios."""
        logger.info("🔗 Testing URL building logic")
        
        test_cases = [
            {
                'query': 'fashion',
                'country': 'ID',
                'language': 'id',
                'page': 1,
                'results_per_page': 100,
                'expected_params': {'start': '0', 'num': '100'}
            },
            {
                'query': 'fashion',
                'country': 'ID', 
                'language': 'id',
                'page': 2,
                'results_per_page': 100,
                'expected_params': {'start': '100', 'num': '100'}
            },
            {
                'query': 'fashion',
                'country': 'US',
                'language': 'en', 
                'page': 3,
                'results_per_page': 50,
                'expected_params': {'start': '100', 'num': '50'}
            },
            {
                'query': 'test query',
                'country': 'JP',
                'language': 'ja',
                'page': 5,
                'results_per_page': 20,
                'expected_params': {'start': '80', 'num': '20'}
            }
        ]
        
        results = []
        all_passed = True
        
        for test_case in test_cases:
            try:
                # Create SearchRequest
                search_request = SearchRequest(
                    query=test_case['query'],
                    country=test_case['country'],
                    language=test_case['language'],
                    page=test_case['page'],
                    results_per_page=test_case['results_per_page']
                )
                
                # Build URL using BrightData client logic
                google_url = self.bright_data_client._build_google_url(search_request)
                
                # Parse URL to extract parameters
                parsed_url = urlparse(google_url)
                url_params = parse_qs(parsed_url.query)
                
                # Extract single values from lists
                actual_params = {k: v[0] if v else '' for k, v in url_params.items()}
                expected_params = test_case['expected_params']
                
                # Check key parameters
                start_correct = actual_params.get('start') == expected_params['start']
                num_correct = actual_params.get('num') == expected_params['num']
                query_correct = actual_params.get('q') == test_case['query']
                country_correct = actual_params.get('gl') == test_case['country'].lower()
                
                all_params_correct = start_correct and num_correct and query_correct and country_correct
                all_passed &= all_params_correct
                
                status = "✅" if all_params_correct else "❌"
                results.append({
                    'query': test_case['query'],
                    'page': test_case['page'],
                    'results_per_page': test_case['results_per_page'],
                    'country': test_case['country'],
                    'expected_start': expected_params['start'],
                    'actual_start': actual_params.get('start'),
                    'expected_num': expected_params['num'],
                    'actual_num': actual_params.get('num'),
                    'start_correct': start_correct,
                    'num_correct': num_correct,
                    'query_correct': query_correct,
                    'country_correct': country_correct,
                    'all_params_correct': all_params_correct,
                    'built_url': google_url,
                    'passed': all_params_correct
                })
                
                logger.info(f"{status} Page {test_case['page']} ({test_case['country']}): "
                           f"start={actual_params.get('start')}, num={actual_params.get('num')}")
                
                if not all_params_correct:
                    logger.warning(f"   Expected: start={expected_params['start']}, num={expected_params['num']}")
                    logger.warning(f"   Actual  : start={actual_params.get('start')}, num={actual_params.get('num')}")
                
            except Exception as e:
                logger.error(f"❌ Error building URL for test case: {str(e)}")
                all_passed = False
                results.append({
                    'query': test_case['query'],
                    'page': test_case['page'],
                    'error': str(e),
                    'passed': False
                })
        
        return {
            'test_name': 'url_building_logic',
            'all_passed': all_passed,
            'test_cases': results,
            'total_tests': len(test_cases),
            'passed_tests': sum(1 for r in results if r.get('passed', False))
        }
    
    def test_total_pages_calculation(self) -> Dict[str, Any]:
        """Test total pages calculation logic."""
        logger.info("📊 Testing total pages calculation")
        
        test_cases = [
            # (total_results, results_per_page, expected_total_pages)
            (100, 10, 10),
            (100, 100, 1),
            (150, 100, 2),
            (999, 100, 10),
            (1000, 100, 10),
            (1001, 100, 11),
            (50, 10, 5),
            (55, 10, 6),  # Should round up
            (0, 10, 0),
            (None, 10, None),  # Unknown total
        ]
        
        results = []
        all_passed = True
        
        for total_results, results_per_page, expected_pages in test_cases:
            try:
                actual_pages = self.pagination_helper.calculate_total_pages(total_results, results_per_page)
                passed = actual_pages == expected_pages
                all_passed &= passed
                
                status = "✅" if passed else "❌"
                results.append({
                    'total_results': total_results,
                    'results_per_page': results_per_page,
                    'expected_total_pages': expected_pages,
                    'actual_total_pages': actual_pages,
                    'passed': passed
                })
                
                logger.info(f"{status} {total_results} results, {results_per_page}/page → "
                           f"{actual_pages} pages (expected {expected_pages})")
                
            except Exception as e:
                logger.error(f"❌ Error calculating total pages: {str(e)}")
                all_passed = False
                results.append({
                    'total_results': total_results,
                    'results_per_page': results_per_page,
                    'error': str(e),
                    'passed': False
                })
        
        return {
            'test_name': 'total_pages_calculation',
            'all_passed': all_passed,
            'test_cases': results,
            'total_tests': len(test_cases),
            'passed_tests': sum(1 for r in results if r.get('passed', False))
        }
    
    def test_page_range_calculation(self) -> Dict[str, Any]:
        """Test page range calculation (result number ranges)."""
        logger.info("📍 Testing page range calculation")
        
        test_cases = [
            # (page, results_per_page, actual_results, expected_start, expected_end)
            (1, 10, 10, 1, 10),
            (1, 100, 100, 1, 100),
            (1, 100, 85, 1, 85),  # Partial results
            (2, 10, 10, 11, 20),
            (2, 100, 100, 101, 200),
            (2, 100, 75, 101, 175),  # Partial results on page 2
            (3, 50, 50, 101, 150),
            (5, 20, 20, 81, 100),
            (1, 10, 0, 0, 0),  # No results
        ]
        
        results = []
        all_passed = True
        
        for page, results_per_page, actual_results, expected_start, expected_end in test_cases:
            try:
                actual_start, actual_end = self.pagination_helper.calculate_page_range(
                    page, results_per_page, actual_results
                )
                
                start_correct = actual_start == expected_start
                end_correct = actual_end == expected_end
                passed = start_correct and end_correct
                all_passed &= passed
                
                status = "✅" if passed else "❌"
                results.append({
                    'page': page,
                    'results_per_page': results_per_page,
                    'actual_results': actual_results,
                    'expected_start': expected_start,
                    'actual_start': actual_start,
                    'expected_end': expected_end,
                    'actual_end': actual_end,
                    'start_correct': start_correct,
                    'end_correct': end_correct,
                    'passed': passed
                })
                
                logger.info(f"{status} Page {page}, {actual_results} results → "
                           f"range {actual_start}-{actual_end} (expected {expected_start}-{expected_end})")
                
            except Exception as e:
                logger.error(f"❌ Error calculating page range: {str(e)}")
                all_passed = False
                results.append({
                    'page': page,
                    'results_per_page': results_per_page,
                    'actual_results': actual_results,
                    'error': str(e),
                    'passed': False
                })
        
        return {
            'test_name': 'page_range_calculation',
            'all_passed': all_passed,
            'test_cases': results,
            'total_tests': len(test_cases),
            'passed_tests': sum(1 for r in results if r.get('passed', False))
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all pagination accuracy tests."""
        logger.info("🚀 Starting pagination mathematical accuracy test suite")
        logger.info("=" * 70)
        
        test_suite_results = {
            'test_suite': 'Pagination Mathematical Accuracy',
            'tests': {}
        }
        
        # Run all test categories
        tests = [
            self.test_pagination_calculations,
            self.test_url_building_logic,
            self.test_total_pages_calculation,
            self.test_page_range_calculation
        ]
        
        overall_success = True
        
        for test_func in tests:
            try:
                logger.info(f"\n--- {test_func.__name__.replace('test_', '').replace('_', ' ').title()} ---")
                test_result = test_func()
                test_suite_results['tests'][test_result['test_name']] = test_result
                overall_success &= test_result['all_passed']
                
                logger.info(f"Result: {test_result['passed_tests']}/{test_result['total_tests']} tests passed")
                
            except Exception as e:
                logger.error(f"❌ Test function {test_func.__name__} failed: {str(e)}")
                overall_success = False
                test_suite_results['tests'][test_func.__name__] = {
                    'error': str(e),
                    'all_passed': False
                }
        
        test_suite_results['overall_success'] = overall_success
        
        # Generate summary
        logger.info("\n" + "=" * 70)
        if overall_success:
            logger.info("✅ ALL PAGINATION MATHEMATICAL TESTS PASSED")
            logger.info("   Pagination calculations are mathematically accurate")
            logger.info("   URL building logic is correct")
            logger.info("   Page ranges are calculated properly")
        else:
            logger.info("⚠️  SOME PAGINATION TESTS FAILED")
            logger.info("   Check individual test results above for details")
        logger.info("=" * 70)
        
        return test_suite_results


async def main():
    """Main test runner."""
    logger.info("📐 Pagination Mathematical Accuracy Tester")
    logger.info("This script validates pagination calculation accuracy")
    
    tester = PaginationAccuracyTester()
    
    try:
        # Run all tests
        results = tester.run_all_tests()
        
        # Save results to file
        import json
        from datetime import datetime
        
        output_file = f"pagination_accuracy_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"\n📄 Detailed results saved to: {output_file}")
        
        return 0 if results['overall_success'] else 1
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  Test interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n💥 Test suite failed: {str(e)}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Test runner failed: {str(e)}")
        sys.exit(1)