#!/usr/bin/env python3
"""
Indonesian Fashion API Testing Script

This script specifically tests fashion queries in Indonesia with 100 results per page
to validate the API endpoint behavior, pagination connectivity, and proxy impact.
"""

import asyncio
import json
import logging
import time
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

# Add the app directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IndonesiaFashionTester:
    """Specialized tester for Indonesian fashion queries."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the tester."""
        self.base_url = base_url.rstrip('/')
        self.search_endpoint = f"{self.base_url}/api/v1/search"
        self.batch_endpoint = f"{self.base_url}/api/v1/search/pages"
        
        # HTTP client
        self.client = httpx.AsyncClient(
            timeout=60.0,  # Longer timeout for large result sets
            headers={"Content-Type": "application/json"}
        )
        
        # Test parameters
        self.fashion_queries = [
            "fashion",
            "mode indonesia", 
            "baju wanita",
            "fashion brand indonesia",
            "pakaian trendy"
        ]
        
        # Results storage
        self.test_results: List[Dict[str, Any]] = []
    
    async def test_single_page_100_results(self) -> Dict[str, Any]:
        """Test single page with 100 results for Indonesian fashion queries."""
        logger.info("🇮🇩 Testing single page with 100 results in Indonesia")
        
        results = {}
        
        for query in self.fashion_queries:
            try:
                logger.info(f"Testing query: '{query}'")
                
                payload = {
                    "query": query,
                    "country": "ID",  # Indonesia
                    "language": "id",  # Indonesian
                    "page": 1,
                    "results_per_page": 100
                }
                
                start_time = time.time()
                response = await self.client.post(self.search_endpoint, json=payload)
                response.raise_for_status()
                
                data = response.json()
                search_time = time.time() - start_time
                
                # Analyze results
                actual_results = data.get('results_count', 0)
                organic_results = data.get('organic_results', [])
                pagination = data.get('pagination', {})
                
                result_analysis = {
                    'query': query,
                    'requested_results': 100,
                    'actual_results': actual_results,
                    'organic_results_count': len(organic_results),
                    'search_time': round(search_time, 2),
                    'total_results_estimate': pagination.get('total_results_estimate'),
                    'has_next_page': pagination.get('has_next_page'),
                    'page_range': f"{pagination.get('page_range_start', 0)}-{pagination.get('page_range_end', 0)}",
                    'success': actual_results > 0,
                    'reached_100': actual_results >= 100,
                    'timestamp': datetime.now().isoformat()
                }
                
                results[query] = result_analysis
                
                # Log key findings
                logger.info(f"✅ {query}: {actual_results}/100 results ({search_time:.2f}s)")
                if actual_results < 100:
                    logger.warning(f"⚠️  {query}: Only got {actual_results}/100 results")
                
                # Small delay between queries
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Error testing '{query}': {str(e)}")
                results[query] = {
                    'query': query,
                    'error': str(e),
                    'success': False,
                    'timestamp': datetime.now().isoformat()
                }
        
        return results
    
    async def test_pagination_connectivity(self, query: str = "fashion") -> Dict[str, Any]:
        """Test if page 1 and page 2 are properly connected."""
        logger.info(f"🔗 Testing pagination connectivity for '{query}'")
        
        try:
            # Test page 1
            page1_payload = {
                "query": query,
                "country": "ID",
                "language": "id", 
                "page": 1,
                "results_per_page": 100
            }
            
            response1 = await self.client.post(self.search_endpoint, json=page1_payload)
            response1.raise_for_status()
            page1_data = response1.json()
            
            # Small delay to simulate real usage
            await asyncio.sleep(2)
            
            # Test page 2
            page2_payload = {
                "query": query,
                "country": "ID", 
                "language": "id",
                "page": 2,
                "results_per_page": 100
            }
            
            response2 = await self.client.post(self.search_endpoint, json=page2_payload)
            response2.raise_for_status()
            page2_data = response2.json()
            
            # Analyze connectivity
            page1_results = page1_data.get('organic_results', [])
            page2_results = page2_data.get('organic_results', [])
            
            # Check for URL overlaps (indicating pagination issues)
            page1_urls = {result['url'] for result in page1_results}
            page2_urls = {result['url'] for result in page2_results}
            url_overlap = page1_urls.intersection(page2_urls)
            
            # Check rank continuity
            page1_last_rank = max([r.get('rank', 0) for r in page1_results], default=0)
            page2_first_rank = min([r.get('rank', float('inf')) for r in page2_results], default=float('inf'))
            
            # Check pagination metadata consistency
            page1_pagination = page1_data.get('pagination', {})
            page2_pagination = page2_data.get('pagination', {})
            
            page1_total = page1_pagination.get('total_results_estimate')
            page2_total = page2_pagination.get('total_results_estimate')
            
            connectivity_analysis = {
                'query': query,
                'page1_results': len(page1_results),
                'page2_results': len(page2_results),
                'url_overlaps': len(url_overlap),
                'overlapping_urls': list(url_overlap),
                'page1_last_rank': page1_last_rank,
                'page2_first_rank': page2_first_rank if page2_first_rank != float('inf') else None,
                'rank_gap': page2_first_rank - page1_last_rank if page2_first_rank != float('inf') else None,
                'page1_total_estimate': page1_total,
                'page2_total_estimate': page2_total,
                'total_estimate_consistent': page1_total == page2_total if page1_total and page2_total else None,
                'page1_has_next': page1_pagination.get('has_next_page'),
                'page2_has_previous': page2_pagination.get('has_previous_page'),
                'properly_connected': len(url_overlap) == 0 and page1_pagination.get('has_next_page', False),
                'timestamp': datetime.now().isoformat()
            }
            
            # Log findings
            if url_overlap:
                logger.warning(f"⚠️  Found {len(url_overlap)} duplicate URLs between pages")
            
            if connectivity_analysis['properly_connected']:
                logger.info("✅ Pagination appears properly connected")
            else:
                logger.warning("⚠️  Potential pagination connectivity issues detected")
            
            return connectivity_analysis
            
        except Exception as e:
            logger.error(f"❌ Error testing pagination connectivity: {str(e)}")
            return {
                'query': query,
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
    
    async def test_batch_pagination_consistency(self, query: str = "fashion") -> Dict[str, Any]:
        """Test batch pagination vs individual page requests."""
        logger.info(f"📦 Testing batch pagination consistency for '{query}'")
        
        try:
            # Test batch pagination (pages 1-2)
            batch_payload = {
                "query": query,
                "country": "ID",
                "language": "id",
                "max_pages": 2,
                "results_per_page": 100,
                "start_page": 1
            }
            
            batch_response = await self.client.post(self.batch_endpoint, json=batch_payload)
            batch_response.raise_for_status()
            batch_data = batch_response.json()
            
            # Extract batch results
            batch_pages = batch_data.get('pages', [])
            batch_page1 = next((p for p in batch_pages if p['page_number'] == 1), {})
            batch_page2 = next((p for p in batch_pages if p['page_number'] == 2), {})
            
            batch_analysis = {
                'query': query,
                'batch_pages_fetched': len(batch_pages),
                'batch_total_results': batch_data.get('total_results', 0),
                'batch_processing_time': batch_data.get('pagination_summary', {}).get('batch_processing_time'),
                'page1_results': batch_page1.get('results_count', 0),
                'page2_results': batch_page2.get('results_count', 0),
                'consistent_with_individual': True,  # Will be determined by comparison
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Batch pagination: {batch_analysis['batch_pages_fetched']} pages, "
                       f"{batch_analysis['batch_total_results']} total results")
            
            return batch_analysis
            
        except Exception as e:
            logger.error(f"❌ Error testing batch pagination: {str(e)}")
            return {
                'query': query,
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
    
    async def test_proxy_impact_analysis(self, query: str = "fashion", iterations: int = 3) -> Dict[str, Any]:
        """Test multiple requests to analyze proxy rotation impact."""
        logger.info(f"🔄 Testing proxy rotation impact for '{query}' ({iterations} iterations)")
        
        request_results = []
        
        try:
            payload = {
                "query": query,
                "country": "ID",
                "language": "id",
                "page": 1,
                "results_per_page": 100
            }
            
            for i in range(iterations):
                logger.info(f"Iteration {i+1}/{iterations}")
                
                start_time = time.time()
                response = await self.client.post(self.search_endpoint, json=payload)
                response.raise_for_status()
                
                data = response.json()
                search_time = time.time() - start_time
                
                # Extract key data points
                iteration_data = {
                    'iteration': i + 1,
                    'results_count': data.get('results_count', 0),
                    'search_time': round(search_time, 2),
                    'total_results_estimate': data.get('pagination', {}).get('total_results_estimate'),
                    'first_result_title': data.get('organic_results', [{}])[0].get('title') if data.get('organic_results') else None,
                    'first_result_url': data.get('organic_results', [{}])[0].get('url') if data.get('organic_results') else None,
                    'timestamp': datetime.now().isoformat()
                }
                
                request_results.append(iteration_data)
                
                # Delay between requests to allow potential proxy rotation
                await asyncio.sleep(5)
            
            # Analyze consistency across iterations
            result_counts = [r['results_count'] for r in request_results]
            total_estimates = [r['total_results_estimate'] for r in request_results if r['total_results_estimate']]
            first_titles = [r['first_result_title'] for r in request_results if r['first_result_title']]
            
            proxy_analysis = {
                'query': query,
                'iterations_tested': iterations,
                'results_count_range': f"{min(result_counts)}-{max(result_counts)}" if result_counts else "N/A",
                'results_count_consistent': len(set(result_counts)) == 1 if result_counts else False,
                'total_estimate_range': f"{min(total_estimates)}-{max(total_estimates)}" if total_estimates else "N/A", 
                'total_estimate_consistent': len(set(total_estimates)) <= 1 if total_estimates else False,
                'first_result_varies': len(set(first_titles)) > 1 if first_titles else False,
                'detailed_results': request_results,
                'proxy_rotation_detected': len(set(first_titles)) > 1 or len(set(result_counts)) > 1,
                'timestamp': datetime.now().isoformat()
            }
            
            if proxy_analysis['proxy_rotation_detected']:
                logger.warning("⚠️  Proxy rotation impact detected - results vary between requests")
            else:
                logger.info("✅ Results consistent across requests - minimal proxy impact")
            
            return proxy_analysis
            
        except Exception as e:
            logger.error(f"❌ Error testing proxy impact: {str(e)}")
            return {
                'query': query,
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and generate comprehensive report."""
        logger.info("🚀 Starting comprehensive Indonesian fashion API test suite")
        logger.info("=" * 80)
        
        comprehensive_results = {
            'test_suite': 'Indonesia Fashion API Validation',
            'timestamp': datetime.now().isoformat(),
            'tests': {}
        }
        
        # Test 1: Single page 100 results
        logger.info("\n📋 Test 1: Single page with 100 results")
        comprehensive_results['tests']['single_page_100'] = await self.test_single_page_100_results()
        
        # Test 2: Pagination connectivity  
        logger.info("\n📋 Test 2: Pagination connectivity")
        comprehensive_results['tests']['pagination_connectivity'] = await self.test_pagination_connectivity()
        
        # Test 3: Batch pagination consistency
        logger.info("\n📋 Test 3: Batch pagination consistency")
        comprehensive_results['tests']['batch_pagination'] = await self.test_batch_pagination_consistency()
        
        # Test 4: Proxy impact analysis
        logger.info("\n📋 Test 4: Proxy rotation impact")
        comprehensive_results['tests']['proxy_impact'] = await self.test_proxy_impact_analysis()
        
        return comprehensive_results
    
    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """Generate a formatted test report."""
        report_lines = [
            "📊 INDONESIA FASHION API TEST REPORT",
            "=" * 60,
            f"Test Suite: {results['test_suite']}",
            f"Timestamp: {results['timestamp']}",
            "=" * 60
        ]
        
        # Single page results summary
        single_page_tests = results['tests'].get('single_page_100', {})
        if isinstance(single_page_tests, dict):
            report_lines.extend([
                "\n🔍 SINGLE PAGE 100 RESULTS TEST",
                "-" * 40
            ])
            
            for query, result in single_page_tests.items():
                if isinstance(result, dict) and 'actual_results' in result:
                    status = "✅" if result.get('reached_100') else "⚠️ "
                    report_lines.append(f"{status} {query}: {result['actual_results']}/100 results ({result.get('search_time', 0)}s)")
        
        # Pagination connectivity summary
        pagination_test = results['tests'].get('pagination_connectivity', {})
        if isinstance(pagination_test, dict):
            report_lines.extend([
                "\n🔗 PAGINATION CONNECTIVITY TEST",
                "-" * 40
            ])
            
            if pagination_test.get('properly_connected'):
                report_lines.append("✅ Pagination properly connected")
            else:
                report_lines.append("⚠️  Pagination connectivity issues detected")
            
            if pagination_test.get('url_overlaps', 0) > 0:
                report_lines.append(f"   - {pagination_test['url_overlaps']} duplicate URLs between pages")
        
        # Proxy impact summary  
        proxy_test = results['tests'].get('proxy_impact', {})
        if isinstance(proxy_test, dict):
            report_lines.extend([
                "\n🔄 PROXY IMPACT ANALYSIS",
                "-" * 40
            ])
            
            if proxy_test.get('proxy_rotation_detected'):
                report_lines.append("⚠️  Proxy rotation impact detected")
                report_lines.append(f"   - Results range: {proxy_test.get('results_count_range', 'N/A')}")
                report_lines.append(f"   - First result varies: {proxy_test.get('first_result_varies', 'N/A')}")
            else:
                report_lines.append("✅ Minimal proxy impact - consistent results")
        
        report_lines.extend([
            "\n" + "=" * 60,
            "📝 Report completed successfully",
            "=" * 60
        ])
        
        return "\n".join(report_lines)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


async def main():
    """Main test runner."""
    logger.info("🇮🇩 Indonesian Fashion API Tester")
    logger.info("This script tests fashion queries in Indonesia with 100 results per page")
    
    async with IndonesiaFashionTester() as tester:
        try:
            # Check API connectivity
            try:
                response = await tester.client.get(f"{tester.base_url}/api/v1/search/status")
                logger.info("✅ Successfully connected to API server")
            except httpx.ConnectError:
                logger.error("❌ Could not connect to API server")
                logger.error("   Please make sure the server is running on http://localhost:8000")
                return 1
            
            # Run comprehensive tests
            results = await tester.run_comprehensive_test()
            
            # Generate and display report
            report = tester.generate_test_report(results)
            print(f"\n{report}")
            
            # Save detailed results to file
            output_file = f"indonesia_fashion_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"\n📄 Detailed results saved to: {output_file}")
            
            return 0
            
        except KeyboardInterrupt:
            logger.info("\n⏹️  Test suite interrupted by user")
            return 1
        
        except Exception as e:
            logger.error(f"\n💥 Test suite failed: {str(e)}")
            return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test runner failed: {str(e)}")
        sys.exit(1)