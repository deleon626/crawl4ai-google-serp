#!/usr/bin/env python3
"""
Example usage of the CompanyInformationParser.

This example demonstrates how to use the CompanyInformationParser to extract
structured company information from web content.
"""

import sys
import os
import asyncio

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.parsers.company_parser import create_company_parser
from app.clients.crawl4ai_client import Crawl4aiClient


async def example_company_extraction():
    """Example of extracting company information from a website."""
    
    print("🏢 Company Information Parser Example")
    print("=" * 50)
    
    # Create parser instance
    parser = create_company_parser()
    
    # Example URLs to test (use publicly available company pages)
    test_urls = [
        "https://openai.com",
        "https://anthropic.com",
        "https://github.com/about",
    ]
    
    # Create crawl client for fetching HTML content
    crawl_client = Crawl4aiClient()
    
    try:
        for url in test_urls:
            print(f"\n🔍 Extracting information from: {url}")
            print("-" * 60)
            
            try:
                # Fetch HTML content
                crawl_result = await crawl_client.crawl_url(url, include_raw_html=True)
                
                if not crawl_result["success"]:
                    print(f"❌ Failed to crawl {url}: {crawl_result['error']}")
                    continue
                
                # Get HTML content from cleaned_html or markdown
                html_content = crawl_result["result"]["cleaned_html"]
                if not html_content:
                    print(f"⚠️ No HTML content available for {url}")
                    continue
                
                # Extract company information
                company_info = parser.extract_company_information(
                    html_content=html_content,
                    url=url
                )
                
                # Display results
                basic = company_info.basic_info
                print(f"🏢 Company: {basic.name}")
                
                if basic.description:
                    desc = basic.description[:150] + "..." if len(basic.description) > 150 else basic.description
                    print(f"📝 Description: {desc}")
                
                if basic.website:
                    print(f"🌐 Website: {basic.website}")
                
                if basic.industry:
                    print(f"🏭 Industry: {basic.industry}")
                
                if basic.founded_year:
                    print(f"📅 Founded: {basic.founded_year}")
                
                if basic.headquarters:
                    print(f"🏠 Headquarters: {basic.headquarters}")
                
                # Contact information
                if company_info.contact:
                    contact = company_info.contact
                    print(f"\n📞 Contact Information:")
                    if contact.email:
                        print(f"  📧 Email: {contact.email}")
                    if contact.phone:
                        print(f"  📱 Phone: {contact.phone}")
                    if contact.address:
                        print(f"  🏠 Address: {contact.address}")
                
                # Social media
                if company_info.social_media:
                    print(f"\n🌐 Social Media ({len(company_info.social_media)} platforms):")
                    for social in company_info.social_media:
                        print(f"  {social.platform.value.title()}: {social.url}")
                
                # Quality scores
                print(f"\n📊 Data Quality Scores:")
                print(f"  Confidence: {company_info.confidence_score:.2f}")
                print(f"  Data Quality: {company_info.data_quality_score:.2f}")
                print(f"  Completeness: {company_info.completeness_score:.2f}")
                
                # Utility methods
                print(f"\n🔧 Utility Methods:")
                print(f"  Primary Email: {company_info.get_primary_email() or 'N/A'}")
                print(f"  Primary Phone: {company_info.get_primary_phone() or 'N/A'}")
                
                linkedin = company_info.get_social_by_platform('linkedin')
                print(f"  LinkedIn: {linkedin.url if linkedin else 'N/A'}")
                
            except Exception as e:
                print(f"❌ Error processing {url}: {str(e)}")
                import traceback
                traceback.print_exc()
    
    finally:
        # The Crawl4aiClient doesn't have a close method - it manages resources internally
        pass


def example_html_parsing():
    """Example of parsing HTML content directly."""
    
    print("\n\n📄 HTML Parsing Example")
    print("=" * 50)
    
    # Sample company HTML (could be from any source)
    sample_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Acme Corporation - Innovation in Technology</title>
        <meta name="description" content="Acme Corporation is a leading technology company specializing in innovative solutions for modern businesses.">
    </head>
    <body>
        <header>
            <h1>Acme Corporation</h1>
            <p>Innovation in Technology Since 1995</p>
        </header>
        
        <main>
            <section class="about">
                <h2>About Us</h2>
                <p>Acme Corporation has been at the forefront of technological innovation for over 25 years. Founded in 1995 in Silicon Valley, we now serve clients worldwide with our cutting-edge solutions.</p>
                <p>Our team of 150+ engineers and consultants work from our headquarters in Palo Alto, CA and satellite offices in New York and London.</p>
            </section>
            
            <section class="contact">
                <h2>Get in Touch</h2>
                <p>Email: info@acmecorp.com</p>
                <p>Phone: +1-650-555-0199</p>
                <p>Address: 1234 Innovation Drive, Palo Alto, CA 94301</p>
            </section>
        </main>
        
        <footer>
            <p>Follow us:</p>
            <a href="https://linkedin.com/company/acme-corp">LinkedIn</a>
            <a href="https://twitter.com/acmecorp">Twitter</a>
            <a href="https://github.com/acmecorp">GitHub</a>
        </footer>
    </body>
    </html>
    """
    
    # Create parser and extract information
    parser = create_company_parser()
    
    company_info = parser.extract_company_information(
        html_content=sample_html,
        url="https://acmecorp.com",
        company_name="Acme Corporation"
    )
    
    print("🏢 Extracted Company Information:")
    print(f"  Name: {company_info.basic_info.name}")
    print(f"  Founded: {company_info.basic_info.founded_year}")
    print(f"  Description: {company_info.basic_info.description}")
    print(f"  Email: {company_info.get_primary_email()}")
    print(f"  Phone: {company_info.get_primary_phone()}")
    
    if company_info.social_media:
        print(f"  Social Media: {len(company_info.social_media)} platforms found")
    
    print(f"  Confidence Score: {company_info.confidence_score:.2f}")


def example_custom_selectors():
    """Example using custom CSS selectors for specialized parsing."""
    
    print("\n\n🎯 Custom Selectors Example")
    print("=" * 50)
    
    # Custom selectors for specific website layouts
    custom_selectors = {
        'company_info': [
            '.company-overview',
            '.about-section',
            '#company-details'
        ],
        'contact_info': [
            '.contact-details',
            '.footer-contact',
            '#contact-section'
        ],
        'social_links': [
            '.social-icons a',
            '.footer-social a',
            '[class*="social"] a'
        ]
    }
    
    # Create parser with custom selectors
    parser = create_company_parser(custom_selectors=custom_selectors)
    
    print("✅ Parser created with custom selectors")
    print("🔧 Custom selectors can be used for:")
    print("  - Specialized website layouts")
    print("  - Industry-specific designs")
    print("  - Sites with unique CSS structures")


if __name__ == "__main__":
    # Run HTML parsing example (synchronous)
    example_html_parsing()
    
    # Run custom selectors example
    example_custom_selectors()
    
    # Run web crawling example (asynchronous)
    print("\n🚀 Starting web crawling examples...")
    print("Note: This will make actual HTTP requests to public websites")
    
    try:
        asyncio.run(example_company_extraction())
    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        print("This may be due to network issues or website changes")
    
    print("\n🎉 Examples completed!")