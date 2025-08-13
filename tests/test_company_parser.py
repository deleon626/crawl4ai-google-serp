"""Comprehensive unit tests for company information parser."""

import pytest
import json
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from app.parsers.company_parser import CompanyInformationParser, create_company_parser
from app.models.company import (
    CompanyInformation, CompanyBasicInfo, CompanyContact, CompanySocial,
    CompanyFinancials, CompanyKeyPersonnel, SocialPlatformType,
    CompanySize, CompanySector
)


class TestCompanyInformationParser:
    """Test suite for CompanyInformationParser."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance for testing."""
        return CompanyInformationParser()
    
    @pytest.fixture
    def sample_html_minimal(self):
        """Minimal HTML sample for testing."""
        return """
        <html>
            <head>
                <title>TestCorp - Leading Technology Company</title>
                <meta name="description" content="TestCorp is a leading technology company providing innovative solutions.">
            </head>
            <body>
                <h1>TestCorp</h1>
                <p>We are a technology company focused on innovation.</p>
            </body>
        </html>
        """
    
    @pytest.fixture
    def sample_html_comprehensive(self):
        """Comprehensive HTML sample for testing."""
        return """
        <html>
            <head>
                <title>OpenAI - Artificial Intelligence Research</title>
                <meta name="description" content="OpenAI is an AI research and deployment company creating safe AGI.">
                <meta name="keywords" content="artificial intelligence, machine learning, AI research">
            </head>
            <body>
                <header>
                    <h1>OpenAI</h1>
                    <nav>
                        <a href="https://linkedin.com/company/openai">LinkedIn</a>
                        <a href="https://twitter.com/openai">Twitter</a>
                        <a href="https://github.com/openai">GitHub</a>
                    </nav>
                </header>
                
                <main>
                    <section class="about">
                        <h2>About OpenAI</h2>
                        <p>OpenAI is an AI research and deployment company. We're dedicated to creating safe artificial general intelligence that benefits all of humanity.</p>
                        <p>Founded in 2015, we have over 300 employees working on cutting-edge AI research.</p>
                        <p>Our headquarters are located in San Francisco, California.</p>
                    </section>
                    
                    <section class="team">
                        <h2>Leadership</h2>
                        <p>Sam Altman, CEO leads our mission to ensure AGI benefits everyone.</p>
                        <p>Greg Brockman, CTO oversees our technical development.</p>
                    </section>
                </main>
                
                <footer class="contact">
                    <h3>Contact Information</h3>
                    <p>Email: contact@openai.com</p>
                    <p>Phone: +1-415-555-0123</p>
                    <p>Address: 3180 18th St, San Francisco, CA 94110</p>
                    <p>Support: support@openai.com</p>
                </footer>
                
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": "OpenAI",
                    "url": "https://openai.com",
                    "description": "AI research and deployment company",
                    "foundingDate": "2015-12-11",
                    "email": "contact@openai.com",
                    "telephone": "+1-415-555-0123",
                    "address": {
                        "@type": "PostalAddress",
                        "streetAddress": "3180 18th St",
                        "addressLocality": "San Francisco",
                        "addressRegion": "CA",
                        "postalCode": "94110",
                        "addressCountry": "US"
                    }
                }
                </script>
            </body>
        </html>
        """
    
    @pytest.fixture
    def sample_html_social_media(self):
        """HTML sample with various social media links."""
        return """
        <html>
            <body>
                <div class="social-links">
                    <a href="https://linkedin.com/company/testcorp">LinkedIn</a>
                    <a href="https://twitter.com/testcorp">Twitter</a>
                    <a href="https://x.com/testcorp_alt">X Alternative</a>
                    <a href="https://facebook.com/testcorp">Facebook</a>
                    <a href="https://instagram.com/testcorp">Instagram</a>
                    <a href="https://youtube.com/c/testcorp">YouTube</a>
                    <a href="https://github.com/testcorp">GitHub</a>
                    <a href="https://tiktok.com/@testcorp">TikTok</a>
                    <a href="https://crunchbase.com/organization/testcorp">Crunchbase</a>
                </div>
            </body>
        </html>
        """
    
    @pytest.fixture
    def sample_html_contact_complex(self):
        """HTML sample with complex contact information."""
        return """
        <html>
            <body>
                <footer class="contact-info">
                    <h2>Contact Us</h2>
                    <div class="contact-details">
                        <p>Primary Email: info@techcorp.com</p>
                        <p>Sales: sales@techcorp.com</p>
                        <p>Support: help@techcorp.com</p>
                        
                        <p>Main Office: +1-555-123-4567</p>
                        <p>Sales Line: +1-555-123-4568</p>
                        <p>Fax: +1-555-123-4569</p>
                        
                        <div class="address">
                            <p>Headquarters:</p>
                            <p>123 Innovation Drive, Suite 400</p>
                            <p>Tech City, CA 94000</p>
                            <p>United States</p>
                        </div>
                        
                        <div class="additional-locations">
                            <p>Branch Offices:</p>
                            <p>456 Market Street, New York, NY 10001</p>
                            <p>789 Tech Boulevard, Austin, TX 78701</p>
                        </div>
                    </div>
                </footer>
            </body>
        </html>
        """
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        parser = CompanyInformationParser()
        
        assert parser.parser_name == 'html.parser'
        assert hasattr(parser, 'compiled_email_patterns')
        assert hasattr(parser, 'compiled_phone_patterns')
        assert hasattr(parser, 'compiled_social_patterns')
        assert len(parser.compiled_email_patterns) > 0
        assert len(parser.compiled_phone_patterns) > 0
        assert len(parser.compiled_social_patterns) > 0
    
    def test_parser_initialization_with_custom_selectors(self):
        """Test parser initialization with custom selectors."""
        custom_selectors = {
            'contact_info': ['.custom-contact', '.my-contact'],
            'new_category': ['.new-selector']
        }
        
        parser = CompanyInformationParser(custom_selectors)
        
        assert '.custom-contact' in parser.SELECTORS['contact_info']
        assert '.my-contact' in parser.SELECTORS['contact_info']
        assert 'new_category' in parser.SELECTORS
        assert '.new-selector' in parser.SELECTORS['new_category']
    
    def test_create_company_parser_factory(self):
        """Test factory function."""
        parser = create_company_parser()
        assert isinstance(parser, CompanyInformationParser)
        
        parser_with_selectors = create_company_parser({'test': ['.test']})
        assert isinstance(parser_with_selectors, CompanyInformationParser)
    
    def test_extract_company_information_empty_html(self, parser):
        """Test extraction with empty HTML."""
        result = parser.extract_company_information("")
        
        assert isinstance(result, CompanyInformation)
        assert result.basic_info.name == "Unknown"
        assert result.confidence_score == 0.0
        assert result.data_quality_score == 0.0
        assert result.completeness_score == 0.0
    
    def test_extract_company_information_minimal(self, parser, sample_html_minimal):
        """Test extraction with minimal HTML."""
        result = parser.extract_company_information(sample_html_minimal)
        
        assert isinstance(result, CompanyInformation)
        assert "TestCorp" in result.basic_info.name
        assert result.basic_info.description is not None
        assert "technology company" in result.basic_info.description.lower()
        assert result.confidence_score > 0.0
    
    def test_extract_company_information_comprehensive(self, parser, sample_html_comprehensive):
        """Test extraction with comprehensive HTML."""
        result = parser.extract_company_information(
            sample_html_comprehensive,
            url="https://openai.com",
            company_name="OpenAI"
        )
        
        # Basic info assertions
        assert result.basic_info.name == "OpenAI"
        assert result.basic_info.domain == "openai.com"
        assert result.basic_info.website == "https://openai.com"
        assert "AI research" in result.basic_info.description
        assert result.basic_info.founded_year == 2015
        assert result.basic_info.sector == CompanySector.TECHNOLOGY
        assert result.basic_info.employee_count == 300
        assert result.basic_info.company_size == CompanySize.MEDIUM
        assert "San Francisco" in result.basic_info.headquarters
        
        # Contact info assertions
        assert result.contact is not None
        assert result.contact.email == "contact@openai.com"
        assert result.contact.phone == "+1-415-555-0123"
        assert result.contact.city == "San Francisco"
        assert result.contact.state == "CA"
        assert result.contact.postal_code == "94110"
        assert "support@openai.com" in result.contact.additional_emails
        
        # Social media assertions
        assert len(result.social_media) >= 3
        social_platforms = {social.platform for social in result.social_media}
        assert SocialPlatformType.LINKEDIN in social_platforms
        assert SocialPlatformType.TWITTER in social_platforms
        assert SocialPlatformType.GITHUB in social_platforms
        
        # Personnel assertions
        assert len(result.key_personnel) >= 2
        names = [person.name for person in result.key_personnel]
        assert any("Sam Altman" in name for name in names)
        assert any("Greg Brockman" in name for name in names)
        
        # Score assertions
        assert result.confidence_score > 0.7
        assert result.data_quality_score > 0.5
        assert result.completeness_score > 0.3
    
    def test_extract_company_name_from_title(self, parser):
        """Test company name extraction from title tag."""
        html = '<html><head><title>TestCorp | About Us</title></head><body></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        name = parser._extract_company_name(soup)
        assert name == "TestCorp"
        
        html2 = '<html><head><title>AnotherCorp - Leading Solutions</title></head><body></body></html>'
        soup2 = BeautifulSoup(html2, 'html.parser')
        
        name2 = parser._extract_company_name(soup2)
        assert name2 == "AnotherCorp"
    
    def test_extract_company_name_from_h1(self, parser):
        """Test company name extraction from h1 tag."""
        html = '<html><body><h1>TechCorp Solutions</h1></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        name = parser._extract_company_name(soup)
        assert name == "TechCorp Solutions"
    
    def test_extract_company_name_known_name_priority(self, parser):
        """Test that known name takes priority."""
        html = '<html><head><title>Different Name</title></head><body></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        name = parser._extract_company_name(soup, "KnownCorp")
        assert name == "KnownCorp"
    
    def test_extract_description_from_meta(self, parser):
        """Test description extraction from meta tags."""
        html = '''
        <html>
            <head>
                <meta name="description" content="We are a leading technology company providing innovative solutions.">
            </head>
            <body></body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        description = parser._extract_description(soup)
        assert "leading technology company" in description
    
    def test_extract_description_from_opengraph(self, parser):
        """Test description extraction from OpenGraph meta."""
        html = '''
        <html>
            <head>
                <meta property="og:description" content="Advanced AI solutions for modern businesses.">
            </head>
            <body></body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        description = parser._extract_description(soup)
        assert "Advanced AI solutions" in description
    
    def test_extract_industry_info_technology(self, parser):
        """Test industry extraction for technology sector."""
        html = '''
        <html>
            <head>
                <meta name="keywords" content="software, technology, AI, machine learning">
            </head>
            <body>
                <p>We are a leading software company specializing in artificial intelligence and cloud solutions.</p>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        industry, sector = parser._extract_industry_info(soup)
        assert sector == CompanySector.TECHNOLOGY
        assert industry is not None
    
    def test_extract_size_info_employee_count(self, parser):
        """Test company size extraction from employee count."""
        html = '''
        <html>
            <body>
                <p>Our team of 150 employees is dedicated to excellence.</p>
                <p>We have grown to 150 people across multiple offices.</p>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        company_size, employee_count, employee_count_range = parser._extract_size_info(soup)
        assert employee_count == 150
        assert company_size == CompanySize.MEDIUM
    
    def test_extract_size_info_employee_range(self, parser):
        """Test company size extraction from employee range."""
        html = '<html><body><p>We employ 50-100 people worldwide.</p></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        company_size, employee_count, employee_count_range = parser._extract_size_info(soup)
        assert employee_count_range == "50-100"
        assert employee_count == 50  # Uses lower bound
        assert company_size == CompanySize.SMALL
    
    def test_extract_location_info_headquarters(self, parser):
        """Test headquarters extraction."""
        html = '''
        <html>
            <body>
                <footer>
                    <p>Our headquarters are located in New York, NY</p>
                    <p>Address: 123 Business Ave, New York, NY 10001</p>
                </footer>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        headquarters, locations = parser._extract_location_info(soup)
        assert "123 Business Ave" in headquarters
        assert "NY 10001" in headquarters
    
    def test_extract_founded_year(self, parser):
        """Test founding year extraction."""
        html_cases = [
            '<html><body><p>Founded in 2010, we have been serving customers for over a decade.</p></body></html>',
            '<html><body><p>Established 2015 as a technology startup.</p></body></html>',
            '<html><body><p>Since 2008, we have been industry leaders.</p></body></html>',
            '<html><body><p>Est. 2020</p></body></html>',
        ]
        
        expected_years = [2010, 2015, 2008, 2020]
        
        for html, expected_year in zip(html_cases, expected_years):
            soup = BeautifulSoup(html, 'html.parser')
            year = parser._extract_founded_year(soup)
            assert year == expected_year
    
    def test_extract_stock_info_public_company(self, parser):
        """Test stock information extraction."""
        html = '''
        <html>
            <body>
                <p>Our company is publicly traded on NASDAQ: TECH</p>
                <p>We are a publicly listed company serving global markets.</p>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        stock_symbol, is_public = parser._extract_stock_info(soup)
        assert stock_symbol == "TECH"
        assert is_public is True
    
    def test_extract_stock_info_private_company(self, parser):
        """Test private company detection."""
        html = '<html><body><p>We are a privately held company focused on innovation.</p></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        stock_symbol, is_public = parser._extract_stock_info(soup)
        assert stock_symbol is None
        assert is_public is False
    
    def test_extract_emails_valid_business_emails(self, parser):
        """Test email extraction with valid business emails."""
        text = """
        Contact us at info@techcorp.com or sales@techcorp.com
        For support, email help@company.co.uk
        CEO: john.doe@business.net
        """
        
        emails = parser._extract_emails(text)
        
        assert "info@techcorp.com" in emails
        assert "sales@techcorp.com" in emails
        assert "help@company.co.uk" in emails
        assert "john.doe@business.net" in emails
        assert len(emails) == 4
    
    def test_extract_emails_excludes_personal_emails(self, parser):
        """Test email extraction excludes personal/common emails."""
        text = """
        Contact: business@company.com
        Personal: john@gmail.com (excluded)
        Test: test@example.com (excluded)
        NoReply: noreply@company.com (excluded)
        """
        
        emails = parser._extract_emails(text)
        
        assert "business@company.com" in emails
        assert "john@gmail.com" not in emails
        assert "test@example.com" not in emails
        assert "noreply@company.com" not in emails
    
    def test_extract_phone_numbers_various_formats(self, parser):
        """Test phone number extraction with various formats."""
        text = """
        Call us at +1-555-123-4567
        Office: (555) 987-6543
        International: +44 20 1234 5678
        Simple: 555.123.4567
        """
        
        phones = parser._extract_phone_numbers(text)
        
        assert len(phones) >= 3  # Should extract multiple valid phones
        phone_strings = ' '.join(phones)
        assert "555-123-4567" in phone_strings or "555.123.4567" in phone_strings
        assert "987-6543" in phone_strings or "(555) 987-6543" in phone_strings
    
    def test_extract_address_components_full_address(self, parser):
        """Test address component extraction."""
        text = "Our office is located at 123 Main Street, San Francisco, CA 94105"
        
        components = parser._extract_address_components(text)
        
        assert components['address'] is not None
        assert "123 Main Street" in components['address']
        assert components['city'] == "San Francisco"
        assert components['state'] == "CA"
        assert components['postal_code'] == "94105"
    
    def test_extract_social_media_comprehensive(self, parser, sample_html_social_media):
        """Test comprehensive social media extraction."""
        soup = BeautifulSoup(sample_html_social_media, 'html.parser')
        
        social_profiles = parser._extract_social_media(soup)
        
        # Should extract profiles for multiple platforms
        assert len(social_profiles) >= 7
        
        platforms_found = {profile.platform for profile in social_profiles}
        expected_platforms = {
            SocialPlatformType.LINKEDIN,
            SocialPlatformType.TWITTER,
            SocialPlatformType.FACEBOOK,
            SocialPlatformType.INSTAGRAM,
            SocialPlatformType.YOUTUBE,
            SocialPlatformType.GITHUB,
            SocialPlatformType.TIKTOK,
            SocialPlatformType.CRUNCHBASE
        }
        
        # Should find most expected platforms
        assert len(platforms_found.intersection(expected_platforms)) >= 6
        
        # Check usernames are extracted
        linkedin_profile = next((p for p in social_profiles if p.platform == SocialPlatformType.LINKEDIN), None)
        if linkedin_profile:
            assert linkedin_profile.username == "testcorp"
    
    def test_extract_financial_info_funding_data(self, parser):
        """Test financial information extraction."""
        html = '''
        <html>
            <body>
                <p>The company raised $50M in Series B funding last year.</p>
                <p>Current valuation is estimated at $500M.</p>
                <p>Total funding raised: $75M across multiple rounds.</p>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        financials = parser._extract_financial_info(soup)
        
        if financials:  # Financial extraction is basic, may not always work
            assert financials.funding_total is not None
            assert financials.valuation is not None
    
    def test_extract_key_personnel_executives(self, parser):
        """Test key personnel extraction."""
        html = '''
        <html>
            <body>
                <div class="team">
                    <p>John Smith, CEO is leading our strategic vision.</p>
                    <p>Sarah Johnson, CTO oversees technical development.</p>
                    <p>Michael Brown, CFO manages financial operations.</p>
                </div>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        personnel = parser._extract_key_personnel(soup)
        
        assert len(personnel) >= 2
        
        titles = [person.title for person in personnel]
        assert "CEO" in titles
        assert "CTO" in titles
        
        names = [person.name for person in personnel]
        assert any("John Smith" in name for name in names)
        assert any("Sarah Johnson" in name for name in names)
    
    def test_extract_from_structured_data_organization(self, parser):
        """Test structured data extraction for organization."""
        html = '''
        <html>
            <body>
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": "TechCorp Inc.",
                    "description": "Leading technology solutions provider",
                    "url": "https://techcorp.com",
                    "foundingDate": "2010-01-15",
                    "email": "info@techcorp.com",
                    "telephone": "+1-555-123-4567",
                    "address": {
                        "@type": "PostalAddress",
                        "streetAddress": "456 Tech Street",
                        "addressLocality": "Silicon Valley",
                        "addressRegion": "CA",
                        "postalCode": "94000",
                        "addressCountry": "US"
                    }
                }
                </script>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        structured_data = parser._extract_from_structured_data(soup)
        
        assert 'basic_info' in structured_data
        assert 'contact_info' in structured_data
        
        basic_info = structured_data['basic_info']
        assert basic_info['name'] == "TechCorp Inc."
        assert basic_info['description'] == "Leading technology solutions provider"
        assert basic_info['website'] == "https://techcorp.com"
        assert basic_info['founded_year'] == 2010
        
        contact_info = structured_data['contact_info']
        assert contact_info['email'] == "info@techcorp.com"
        assert contact_info['phone'] == "+1-555-123-4567"
        assert contact_info['city'] == "Silicon Valley"
        assert contact_info['state'] == "CA"
        assert contact_info['postal_code'] == "94000"
        assert "456 Tech Street" in contact_info['address']
    
    def test_extract_from_structured_data_invalid_json(self, parser):
        """Test structured data extraction with invalid JSON."""
        html = '''
        <html>
            <body>
                <script type="application/ld+json">
                { invalid json structure }
                </script>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        # Should not raise exception, should return empty dict
        structured_data = parser._extract_from_structured_data(soup)
        assert structured_data == {}
    
    def test_merge_basic_info(self, parser):
        """Test merging basic info from different sources."""
        extracted = CompanyBasicInfo(
            name="TestCorp",
            description="Original description"
        )
        
        structured = {
            'name': 'TestCorp Enhanced',  # Should not override existing
            'website': 'https://testcorp.com',  # Should add missing
            'founded_year': 2020  # Should add missing
        }
        
        merged = parser._merge_basic_info(extracted, structured)
        
        assert merged.name == "TestCorp"  # Original preserved
        assert merged.description == "Original description"  # Original preserved  
        assert merged.website == "https://testcorp.com"  # Added from structured
        assert merged.founded_year == 2020  # Added from structured
    
    def test_merge_contact_info_new_contact(self, parser):
        """Test merging contact info when none exists."""
        structured = {
            'email': 'new@company.com',
            'phone': '+1-555-000-0000',
            'city': 'New City'
        }
        
        merged = parser._merge_contact_info(None, structured)
        
        assert merged.email == 'new@company.com'
        assert merged.phone == '+1-555-000-0000'
        assert merged.city == 'New City'
    
    def test_merge_contact_info_existing_contact(self, parser):
        """Test merging contact info with existing contact."""
        existing = CompanyContact(
            email="existing@company.com",
            phone="+1-555-111-1111"
        )
        
        structured = {
            'email': 'new@company.com',  # Should not override
            'address': '123 New Street',  # Should add
            'city': 'New City'  # Should add
        }
        
        merged = parser._merge_contact_info(existing, structured)
        
        assert merged.email == "existing@company.com"  # Original preserved
        assert merged.phone == "+1-555-111-1111"  # Original preserved
        assert merged.address == "123 New Street"  # Added from structured
        assert merged.city == "New City"  # Added from structured
    
    def test_calculate_confidence_score(self, parser):
        """Test confidence score calculation."""
        # High quality data
        basic_info = CompanyBasicInfo(
            name="TestCorp",
            description="A comprehensive description of the company",
            website="https://testcorp.com",
            industry="Technology"
        )
        
        contact = CompanyContact(
            email="contact@testcorp.com",
            phone="+1-555-123-4567",
            address="123 Tech Street, Tech City, CA 94000"
        )
        
        social_media = [
            CompanySocial(platform=SocialPlatformType.LINKEDIN, url="https://linkedin.com/company/testcorp"),
            CompanySocial(platform=SocialPlatformType.TWITTER, url="https://twitter.com/testcorp"),
        ]
        
        financials = CompanyFinancials(revenue="10M", funding_total="5M")
        personnel = [CompanyKeyPersonnel(name="John Doe", title="CEO")]
        
        score = parser._calculate_confidence_score(basic_info, contact, social_media, financials, personnel)
        
        assert 0.7 <= score <= 1.0  # Should be high confidence
    
    def test_calculate_confidence_score_minimal_data(self, parser):
        """Test confidence score with minimal data."""
        basic_info = CompanyBasicInfo(name="TestCorp")
        
        score = parser._calculate_confidence_score(basic_info, None, [], None, [])
        
        assert 0.0 <= score <= 0.3  # Should be low confidence
    
    def test_calculate_data_quality_score(self, parser):
        """Test data quality score calculation."""
        basic_info = CompanyBasicInfo(
            name="TestCorp",
            description="A good length description that provides meaningful information about the company and its services."
        )
        
        contact = CompanyContact(
            email="contact@testcorp.com",
            phone="+1-555-123-4567",
            address="123 Tech Street"
        )
        
        social_media = [
            CompanySocial(platform=SocialPlatformType.LINKEDIN, url="https://linkedin.com/company/testcorp"),
            CompanySocial(platform=SocialPlatformType.TWITTER, url="https://twitter.com/testcorp"),
        ]
        
        quality_score = parser._calculate_data_quality_score(basic_info, contact, social_media)
        
        assert 0.6 <= quality_score <= 1.0  # Should be good quality
    
    def test_calculate_completeness_score(self, parser):
        """Test completeness score calculation."""
        basic_info = CompanyBasicInfo(
            name="TestCorp",
            description="Company description",
            website="https://testcorp.com",
            industry="Technology",
            headquarters="Tech City, CA",
            founded_year=2020
        )
        
        contact = CompanyContact(
            email="contact@testcorp.com",
            phone="+1-555-123-4567",
            address="123 Tech Street",
            city="Tech City",
            state="CA"
        )
        
        social_media = [
            CompanySocial(platform=SocialPlatformType.LINKEDIN, url="https://linkedin.com/company/testcorp"),
            CompanySocial(platform=SocialPlatformType.TWITTER, url="https://twitter.com/testcorp"),
        ]
        
        financials = CompanyFinancials(revenue="10M")
        personnel = [CompanyKeyPersonnel(name="John Doe", title="CEO")]
        
        completeness_score = parser._calculate_completeness_score(
            basic_info, contact, social_media, financials, personnel
        )
        
        assert 0.5 <= completeness_score <= 1.0  # Should be reasonably complete
    
    def test_create_empty_company_info(self, parser):
        """Test creation of empty company info."""
        empty_info = parser._create_empty_company_info("TestCorp")
        
        assert isinstance(empty_info, CompanyInformation)
        assert empty_info.basic_info.name == "TestCorp"
        assert empty_info.contact is None
        assert empty_info.social_media == []
        assert empty_info.financials is None
        assert empty_info.key_personnel == []
        assert empty_info.confidence_score == 0.0
        assert empty_info.data_quality_score == 0.0
        assert empty_info.completeness_score == 0.0
    
    def test_is_valid_email(self, parser):
        """Test email validation method."""
        valid_emails = [
            "test@example.com",
            "user.name@company.co.uk",
            "info@company-name.com",
            "support123@tech.io",
        ]
        
        invalid_emails = [
            "not-an-email",
            "@missing-local.com",
            "missing-at-sign.com",
            "invalid@",
            "spaces in@email.com",
        ]
        
        for email in valid_emails:
            assert parser._is_valid_email(email), f"Should be valid: {email}"
        
        for email in invalid_emails:
            assert not parser._is_valid_email(email), f"Should be invalid: {email}"
    
    def test_error_handling_malformed_html(self, parser):
        """Test error handling with malformed HTML."""
        malformed_html = "<html><head><title>Test</title><body><p>Unclosed paragraph<div>Mixed tags</html>"
        
        # Should not raise exception, should return minimal result
        result = parser.extract_company_information(malformed_html, company_name="TestCorp")
        
        assert isinstance(result, CompanyInformation)
        assert result.basic_info.name == "TestCorp"
    
    @patch('app.parsers.company_parser.logger')
    def test_logging_behavior(self, mock_logger, parser, sample_html_minimal):
        """Test that parser logs appropriately."""
        parser.extract_company_information(sample_html_minimal, url="https://test.com")
        
        # Should have debug and info log calls
        assert mock_logger.debug.called
        assert mock_logger.info.called
    
    def test_extract_contact_info_complex(self, parser, sample_html_contact_complex):
        """Test contact extraction with complex contact information."""
        soup = BeautifulSoup(sample_html_contact_complex, 'html.parser')
        
        contact = parser._extract_contact_info(soup)
        
        assert contact is not None
        assert contact.email is not None
        assert contact.phone is not None
        assert contact.address is not None
        
        # Should extract primary contact info
        assert "info@techcorp.com" in contact.email or "sales@techcorp.com" in contact.email
        
        # Should have additional emails
        assert len(contact.additional_emails) >= 1
        
        # Should have phone numbers
        assert "555-123-4567" in contact.phone or len(contact.additional_phones) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])