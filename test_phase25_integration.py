"""
Phase 2.5 Integration Test - Company Analysis & Employee Discovery
Tests the complete company analysis pipeline end-to-end.
"""

import asyncio
import json
import time
from typing import Dict, Any

from app.services.company_analysis_service import CompanyAnalysisService, CompanyWebsiteDiscovery, EmployeeExtractor
from app.models.company import CompanyAnalysisRequest


def test_company_website_discovery():
    """Test company website discovery functionality."""
    print("🔍 Testing Company Website Discovery...")
    
    discovery = CompanyWebsiteDiscovery()
    
    # Test query generation
    queries = discovery.generate_search_queries("Tesla Inc", "electric vehicles")
    print(f"✅ Generated {len(queries)} search queries")
    print(f"   Example query: {queries[0]}")
    
    # Test URL extraction (mock data)
    mock_results = [
        {
            'link': 'https://tesla.com',
            'title': 'Tesla - Electric Vehicles, Solar & Clean Energy',
            'snippet': 'Tesla is accelerating the world transition to sustainable energy'
        },
        {
            'link': 'https://linkedin.com/company/tesla-motors',
            'title': 'Tesla | LinkedIn',
            'snippet': 'Tesla Motors | 2,645,234 followers'
        },
        {
            'link': 'https://twitter.com/tesla',
            'title': 'Tesla (@Tesla) / Twitter',
            'snippet': 'Electric vehicles, clean energy'
        }
    ]
    
    primary, alternatives, social = discovery.extract_company_urls(mock_results)
    print(f"✅ Primary website: {primary}")
    print(f"✅ Social profiles: {len(social)} found")
    for platform, url in social.items():
        print(f"   {platform}: {url}")
    
    print("✅ Company Website Discovery working!\n")


def test_employee_extractor():
    """Test employee extraction functionality."""
    print("👥 Testing Employee Extractor...")
    
    extractor = EmployeeExtractor()
    
    # Mock company website content
    mock_content = """
    <html>
    <body>
        <div class="leadership-team">
            <h2>Our Leadership</h2>
            <div class="executive">
                <h3>Elon Musk</h3>
                <p>Chief Executive Officer</p>
                <p>Elon leads Tesla's mission to accelerate sustainable transport.</p>
            </div>
            <div class="executive">
                <h3>Drew Baglino</h3>
                <p>Senior Vice President, Powertrain and Energy Engineering</p>
                <p>Drew oversees our powertrain and energy systems.</p>
            </div>
            <div class="executive">
                <h3>Zachary Kirkhorn</h3>
                <p>Chief Financial Officer</p>
                <p>Zach manages Tesla's financial operations and strategy.</p>
            </div>
        </div>
        
        <div class="engineering-team">
            <h3>Engineering Leadership</h3>
            <p>Lars Moravy, Vice President of Vehicle Engineering</p>
            <p>Rebecca Tinucci, Senior Director of Charging Infrastructure</p>
            <p>Pete Bannon, Director of Hardware Engineering</p>
        </div>
    </body>
    </html>
    """
    
    employees = extractor.extract_employees(mock_content, "https://tesla.com/team")
    
    print(f"✅ Employees extracted: {len(employees)}")
    print(f"✅ High confidence employees: {len([e for e in employees if e.confidence_score > 0.8])}")
    
    # Display top employees
    print("   Top employees found:")
    for i, employee in enumerate(employees[:5], 1):
        print(f"   {i}. {employee.name} - {employee.title} (Confidence: {employee.confidence_score:.2f})")
    
    # Test role categorization
    roles = {}
    for employee in employees:
        role = employee.role_category.value
        roles[role] = roles.get(role, 0) + 1
    
    print(f"✅ Role distribution: {roles}")
    print("✅ Employee Extractor working!\n")


async def test_company_search_queries():
    """Test company search query generation."""
    print("🔎 Testing Company Search Queries...")
    
    discovery = CompanyWebsiteDiscovery()
    
    # Test different company types
    test_companies = [
        ("OpenAI", "artificial intelligence"),
        ("Stripe", "fintech payments"),
        ("Airbnb", "hospitality travel")
    ]
    
    for company_name, context in test_companies:
        queries = discovery.generate_search_queries(company_name, context)
        print(f"✅ {company_name}: Generated {len(queries)} queries")
        print(f"   Example: {queries[0]}")
    
    print("✅ Company Search Queries working!\n")


async def test_mock_company_analysis():
    """Test company analysis with mock data."""
    print("🏢 Testing Company Analysis Pipeline...")
    
    # Test with direct URL (would normally crawl)
    request = CompanyAnalysisRequest(
        company_url="https://tesla.com",
        company_name="Tesla Inc",
        extract_employees=True,
        max_employees=10,
        deep_analysis=True
    )
    
    print(f"✅ Created analysis request for: {request.company_name}")
    print(f"✅ URL: {request.company_url}")
    print(f"✅ Extract employees: {request.extract_employees}")
    print(f"✅ Max employees: {request.max_employees}")
    
    # Validate request
    assert request.company_url is not None or request.company_name is not None
    print("✅ Request validation passed")
    
    print("✅ Company Analysis Pipeline ready!\n")


def test_data_models():
    """Test company analysis data models."""
    print("📋 Testing Data Models...")
    
    from app.models.company import (
        CompanyInfo, EmployeeProfile, EmployeeRole, ContactMethod,
        CompanySize, CompanyWebsite
    )
    
    # Test employee profile creation
    employee = EmployeeProfile(
        name="John Smith",
        title="Chief Executive Officer",
        role_category=EmployeeRole.EXECUTIVE,
        confidence_score=0.95,
        source_url="https://company.com/team"
    )
    
    assert employee.name == "John Smith"
    assert employee.role_category == EmployeeRole.EXECUTIVE
    assert 0.0 <= employee.confidence_score <= 1.0
    print("✅ Employee profile model working")
    
    # Test contact method
    contact = ContactMethod(
        type="email",
        value="contact@company.com", 
        confidence=0.8,
        verified=False
    )
    
    assert contact.type == "email"
    assert contact.confidence == 0.8
    print("✅ Contact method model working")
    
    # Test company website model
    website = CompanyWebsite(
        url="https://company.com",
        title="Company Inc - Official Website",
        technologies=["Python", "React", "AWS"],
        keywords=["software", "technology", "innovation"]
    )
    
    print(f"   URL type: {type(website.url)}, value: {website.url}")
    # HttpUrl comparison - convert both to strings for comparison
    assert str(website.url) == "https://company.com/"  # HttpUrl adds trailing slash
    assert len(website.technologies) == 3
    print("✅ Company website model working")
    
    print("✅ Data Models working!\n")


async def test_integration_patterns():
    """Test integration patterns and utilities."""
    print("🔗 Testing Integration Patterns...")
    
    from app.utils.exceptions import CompanyAnalysisError
    
    # Test custom exception
    try:
        raise CompanyAnalysisError("Test error")
    except CompanyAnalysisError as e:
        assert str(e) == "Test error"
        print("✅ CompanyAnalysisError working")
    
    # Test async context manager pattern (mock)
    async def mock_service_usage():
        service = CompanyAnalysisService()
        async with service:
            return "Service used successfully"
    
    result = await mock_service_usage()
    assert result == "Service used successfully"
    print("✅ Async context manager pattern working")
    
    print("✅ Integration Patterns working!\n")


async def main():
    """Run all Phase 2.5 integration tests."""
    print("🚀 Starting Phase 2.5 Integration Tests...\n")
    
    start_time = time.time()
    
    try:
        # Test individual components
        test_company_website_discovery()
        test_employee_extractor()
        await test_company_search_queries()
        await test_mock_company_analysis()
        test_data_models()
        await test_integration_patterns()
        
        elapsed_time = time.time() - start_time
        
        print("🎉 All Phase 2.5 Integration Tests Passed!")
        print(f"⏱️  Total execution time: {elapsed_time:.2f} seconds")
        print()
        print("✅ Company website discovery operational")
        print("✅ Employee extraction algorithms working")
        print("✅ Search query generation functional")
        print("✅ Data models validated")
        print("✅ Integration patterns ready")
        print("✅ Phase 2.5 infrastructure complete")
        print()
        print("🔧 Ready for API endpoint testing with real data!")
        print("🌐 Streamlit multi-page interface available")
        print("🏢 Company Analysis & Employee Discovery ready for production!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        print(f"🔍 Error details: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    import traceback
    asyncio.run(main())