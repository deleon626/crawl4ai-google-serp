#!/usr/bin/env python3
"""
Company Information Extraction Demo

This example demonstrates how to use the CompanyExtractionService to extract
comprehensive company information from the web.
"""

import asyncio
import json
from app.services.company_service import CompanyExtractionService
from app.models.company import CompanyInformationRequest, ExtractionMode


async def demonstrate_company_extraction():
    """Demonstrate company information extraction."""
    
    print("🏢 Company Information Extraction Demo")
    print("=" * 50)
    
    # Example 1: Comprehensive extraction for a well-known company
    print("\n1. Comprehensive Extraction Example")
    print("-" * 35)
    
    request = CompanyInformationRequest(
        company_name="OpenAI",
        domain="openai.com",
        extraction_mode=ExtractionMode.COMPREHENSIVE,
        country="US",
        language="en",
        include_social_media=True,
        include_financial_data=True,
        include_contact_info=True,
        include_key_personnel=False,  # Skip to avoid too much data
        max_pages_to_crawl=3,
        timeout_seconds=30
    )
    
    print(f"🔍 Extracting information for: {request.company_name}")
    print(f"   Mode: {request.extraction_mode}")
    print(f"   Max pages: {request.max_pages_to_crawl}")
    print(f"   Domain hint: {request.domain}")
    
    try:
        async with CompanyExtractionService() as service:
            response = await service.extract_company_information(request)
            
            print(f"\n📊 Extraction Results:")
            print(f"   ✅ Success: {response.success}")
            print(f"   ⏱️  Processing time: {response.processing_time:.2f}s")
            print(f"   📄 Pages crawled: {response.extraction_metadata.pages_crawled}")
            print(f"   🔄 Pages attempted: {response.extraction_metadata.pages_attempted}")
            print(f"   ❌ Errors: {len(response.errors)}")
            print(f"   ⚠️  Warnings: {len(response.warnings)}")
            
            if response.company_information:
                info = response.company_information
                print(f"\n🏢 Company Information:")
                print(f"   Name: {info.basic_info.name}")
                print(f"   Website: {info.basic_info.website}")
                print(f"   Description: {info.basic_info.description[:100]}..." if info.basic_info.description else "   Description: None")
                print(f"   Industry: {info.basic_info.industry}")
                print(f"   Headquarters: {info.basic_info.headquarters}")
                print(f"   Founded: {info.basic_info.founded_year}")
                
                if info.contact:
                    print(f"\n📞 Contact Information:")
                    print(f"   Email: {info.contact.email}")
                    print(f"   Phone: {info.contact.phone}")
                    print(f"   Address: {info.contact.address}")
                
                if info.social_media:
                    print(f"\n🌐 Social Media ({len(info.social_media)} profiles):")
                    for social in info.social_media:
                        print(f"   {social.platform.value}: {social.url}")
                
                print(f"\n📈 Quality Scores:")
                print(f"   Confidence: {info.confidence_score:.2f}")
                print(f"   Data Quality: {info.data_quality_score:.2f}")
                print(f"   Completeness: {info.completeness_score:.2f}")
            
            if response.errors:
                print(f"\n❌ Errors encountered:")
                for error in response.errors:
                    print(f"   - {error.error_type}: {error.error_message}")
            
            if response.warnings:
                print(f"\n⚠️  Warnings:")
                for warning in response.warnings:
                    print(f"   - {warning}")
    
    except Exception as e:
        print(f"❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


async def demonstrate_focused_extraction():
    """Demonstrate focused extraction modes."""
    
    print("\n\n2. Focused Extraction Examples")
    print("-" * 35)
    
    # Contact-focused extraction
    print("\n📞 Contact-Focused Extraction:")
    
    contact_request = CompanyInformationRequest(
        company_name="Stripe",
        extraction_mode=ExtractionMode.CONTACT_FOCUSED,
        include_social_media=False,
        include_financial_data=False,
        include_contact_info=True,
        max_pages_to_crawl=2,
        timeout_seconds=20
    )
    
    try:
        async with CompanyExtractionService() as service:
            response = await service.extract_company_information(contact_request)
            
            print(f"   Success: {response.success}")
            print(f"   Processing time: {response.processing_time:.2f}s")
            
            if response.company_information and response.company_information.contact:
                contact = response.company_information.contact
                print(f"   Email: {contact.email}")
                print(f"   Phone: {contact.phone}")
                print(f"   Address: {contact.address}")
            else:
                print("   No contact information extracted")
    
    except Exception as e:
        print(f"   ❌ Contact extraction failed: {str(e)}")


def demonstrate_query_generation():
    """Demonstrate search query generation."""
    
    print("\n\n3. Search Query Generation Demo")
    print("-" * 35)
    
    service = CompanyExtractionService()
    
    # Different extraction modes
    modes = [
        (ExtractionMode.BASIC, "Basic Mode"),
        (ExtractionMode.COMPREHENSIVE, "Comprehensive Mode"),
        (ExtractionMode.CONTACT_FOCUSED, "Contact-Focused Mode"),
        (ExtractionMode.FINANCIAL_FOCUSED, "Financial-Focused Mode")
    ]
    
    for mode, mode_name in modes:
        print(f"\n🔍 {mode_name}:")
        
        request = CompanyInformationRequest(
            company_name="TechStartup Inc",
            domain="techstartup.com",
            extraction_mode=mode,
            include_social_media=True,
            include_financial_data=True,
            include_contact_info=True,
            include_key_personnel=True
        )
        
        queries = service._generate_search_queries(request)
        print(f"   Generated {len(queries)} queries:")
        for i, query in enumerate(queries[:5], 1):  # Show first 5
            print(f"   {i}. {query}")
        if len(queries) > 5:
            print(f"   ... and {len(queries) - 5} more")


def demonstrate_url_scoring():
    """Demonstrate URL priority scoring."""
    
    print("\n\n4. URL Priority Scoring Demo")
    print("-" * 35)
    
    service = CompanyExtractionService()
    
    request = CompanyInformationRequest(
        company_name="TechCorp",
        domain="techcorp.com"
    )
    
    # Test URLs with different characteristics
    test_urls = [
        ("https://techcorp.com/about", "TechCorp - About Us", "Learn about TechCorp"),
        ("https://techcorp.com/contact", "TechCorp - Contact", "Contact TechCorp team"),  
        ("https://linkedin.com/company/techcorp", "TechCorp | LinkedIn", "TechCorp on LinkedIn"),
        ("https://crunchbase.com/organization/techcorp", "TechCorp - Crunchbase", "TechCorp funding"),
        ("https://news-site.com/techcorp-article", "TechCorp News", "TechCorp in the news"),
        ("https://facebook.com/techcorp", "TechCorp Facebook", "TechCorp Facebook page")
    ]
    
    print("🎯 URL Priority Scores:")
    scored_urls = []
    
    for url, title, description in test_urls:
        score = service._score_url_priority(url, title, description, request)
        scored_urls.append((score, url, title))
        print(f"   {score:.3f} - {url}")
        print(f"          {title}")
    
    print("\n📊 Ranked by Priority:")
    scored_urls.sort(reverse=True)
    for i, (score, url, title) in enumerate(scored_urls, 1):
        print(f"   {i}. {score:.3f} - {title}")


async def main():
    """Main demo function."""
    try:
        # Note: These demos use mocked data for demonstration
        # In a real environment, they would make actual web requests
        
        print("⚠️  NOTE: This demo uses mocked data to avoid making real web requests.")
        print("   In production, the service would perform actual SERP searches and web crawling.")
        
        # Run the demonstrations
        await demonstrate_company_extraction()
        await demonstrate_focused_extraction()
        demonstrate_query_generation()
        demonstrate_url_scoring()
        
        print("\n" + "=" * 50)
        print("✅ Company Extraction Demo Completed!")
        print("\nTo use this service in production:")
        print("1. Set up your BRIGHT_DATA_TOKEN environment variable")
        print("2. Configure proper timeouts and rate limits")
        print("3. Handle errors gracefully in your application")
        print("4. Consider caching results to avoid redundant requests")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())