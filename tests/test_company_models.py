"""Comprehensive unit tests for company data models."""

import pytest
from datetime import datetime, UTC
from pydantic import ValidationError
from typing import Optional

from app.models.company import (
    # Enums
    ExtractionMode, CompanySize, CompanySector, SocialPlatformType,
    
    # Request models
    CompanyInformationRequest,
    
    # Data models
    CompanyBasicInfo, CompanyContact, CompanySocial, CompanyFinancials,
    CompanyKeyPersonnel, CompanyInformation,
    
    # Response models
    ExtractionError, ExtractionMetadata, CompanyExtractionResponse
)


class TestExtractionMode:
    """Test ExtractionMode enum."""
    
    def test_extraction_mode_values(self):
        """Test all extraction mode values."""
        assert ExtractionMode.BASIC.value == "basic"
        assert ExtractionMode.COMPREHENSIVE.value == "comprehensive"
        assert ExtractionMode.CONTACT_FOCUSED.value == "contact_focused"
        assert ExtractionMode.FINANCIAL_FOCUSED.value == "financial_focused"
    
    def test_extraction_mode_count(self):
        """Test expected number of extraction modes."""
        assert len(ExtractionMode) == 4


class TestCompanySize:
    """Test CompanySize enum."""
    
    def test_company_size_values(self):
        """Test all company size values."""
        assert CompanySize.STARTUP.value == "startup"
        assert CompanySize.SMALL.value == "small"
        assert CompanySize.MEDIUM.value == "medium"
        assert CompanySize.LARGE.value == "large"
        assert CompanySize.ENTERPRISE.value == "enterprise"
        assert CompanySize.UNKNOWN.value == "unknown"


class TestCompanySector:
    """Test CompanySector enum."""
    
    def test_company_sector_values(self):
        """Test key company sector values."""
        assert CompanySector.TECHNOLOGY.value == "technology"
        assert CompanySector.FINANCE.value == "finance"
        assert CompanySector.HEALTHCARE.value == "healthcare"
        assert CompanySector.OTHER.value == "other"
    
    def test_sector_count(self):
        """Test expected number of sectors."""
        assert len(CompanySector) >= 10  # Should have at least 10 sectors


class TestSocialPlatformType:
    """Test SocialPlatformType enum."""
    
    def test_social_platform_values(self):
        """Test all social platform values."""
        assert SocialPlatformType.LINKEDIN.value == "linkedin"
        assert SocialPlatformType.TWITTER.value == "twitter"
        assert SocialPlatformType.FACEBOOK.value == "facebook"
        assert SocialPlatformType.GITHUB.value == "github"
        assert SocialPlatformType.CRUNCHBASE.value == "crunchbase"
        assert SocialPlatformType.OTHER.value == "other"


class TestCompanyInformationRequest:
    """Test CompanyInformationRequest model."""
    
    def test_valid_request_minimal(self):
        """Test valid request with minimal data."""
        request = CompanyInformationRequest(company_name="TestCorp")
        
        assert request.company_name == "TestCorp"
        assert request.domain is None
        assert request.extraction_mode == ExtractionMode.COMPREHENSIVE
        assert request.country == "US"
        assert request.language == "en"
        assert request.max_pages_to_crawl == 5
        assert request.timeout_seconds == 30
    
    def test_valid_request_full(self):
        """Test valid request with all data."""
        request = CompanyInformationRequest(
            company_name="OpenAI",
            domain="openai.com",
            extraction_mode=ExtractionMode.CONTACT_FOCUSED,
            country="GB",
            language="fr",
            include_subsidiaries=True,
            include_social_media=False,
            include_financial_data=False,
            include_contact_info=True,
            include_key_personnel=True,
            max_pages_to_crawl=10,
            timeout_seconds=60
        )
        
        assert request.company_name == "OpenAI"
        assert request.domain == "openai.com"
        assert request.extraction_mode == ExtractionMode.CONTACT_FOCUSED
        assert request.country == "GB"
        assert request.language == "fr"
        assert request.include_subsidiaries is True
        assert request.include_social_media is False
        assert request.max_pages_to_crawl == 10
        assert request.timeout_seconds == 60
    
    def test_invalid_company_name_empty(self):
        """Test validation error for empty company name."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyInformationRequest(company_name="")
        
        assert "string_too_short" in str(exc_info.value) or "min_length" in str(exc_info.value)
    
    def test_invalid_country_code_format(self):
        """Test validation error for invalid country code."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyInformationRequest(company_name="Test", country="usa")
        
        assert "Country code must be 2-letter uppercase" in str(exc_info.value)
    
    def test_invalid_language_code_format(self):
        """Test validation error for invalid language code."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyInformationRequest(company_name="Test", language="EN")
        
        assert "Language code must be 2-letter lowercase" in str(exc_info.value)
    
    def test_domain_validation_with_protocol(self):
        """Test domain validation strips protocol."""
        request = CompanyInformationRequest(
            company_name="Test",
            domain="https://example.com/"
        )
        
        assert request.domain == "example.com"
    
    def test_domain_validation_invalid_format(self):
        """Test domain validation rejects invalid formats."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyInformationRequest(
                company_name="Test",
                domain="not..a..valid..domain"
            )
        
        assert "Invalid domain format" in str(exc_info.value)
    
    def test_max_pages_constraints(self):
        """Test max pages validation constraints."""
        # Valid range
        request = CompanyInformationRequest(company_name="Test", max_pages_to_crawl=1)
        assert request.max_pages_to_crawl == 1
        
        request = CompanyInformationRequest(company_name="Test", max_pages_to_crawl=20)
        assert request.max_pages_to_crawl == 20
        
        # Invalid range - too low
        with pytest.raises(ValidationError):
            CompanyInformationRequest(company_name="Test", max_pages_to_crawl=0)
        
        # Invalid range - too high
        with pytest.raises(ValidationError):
            CompanyInformationRequest(company_name="Test", max_pages_to_crawl=21)
    
    def test_timeout_constraints(self):
        """Test timeout validation constraints."""
        # Valid range
        request = CompanyInformationRequest(company_name="Test", timeout_seconds=5)
        assert request.timeout_seconds == 5
        
        request = CompanyInformationRequest(company_name="Test", timeout_seconds=120)
        assert request.timeout_seconds == 120
        
        # Invalid range - too low
        with pytest.raises(ValidationError):
            CompanyInformationRequest(company_name="Test", timeout_seconds=4)
        
        # Invalid range - too high
        with pytest.raises(ValidationError):
            CompanyInformationRequest(company_name="Test", timeout_seconds=121)


class TestCompanyContact:
    """Test CompanyContact model."""
    
    def test_valid_contact_full(self):
        """Test valid contact with all fields."""
        contact = CompanyContact(
            email="contact@example.com",
            phone="+1-555-123-4567",
            fax="+1-555-123-4568",
            address="123 Main St, Suite 100",
            city="San Francisco",
            state="CA",
            country="United States",
            postal_code="94111",
            additional_emails=["support@example.com", "sales@example.com"],
            additional_phones=["+1-555-123-4569"]
        )
        
        assert contact.email == "contact@example.com"
        assert contact.phone == "+1-555-123-4567"
        assert contact.city == "San Francisco"
        assert len(contact.additional_emails) == 2
        assert len(contact.additional_phones) == 1
    
    def test_valid_contact_minimal(self):
        """Test valid contact with minimal fields."""
        contact = CompanyContact()
        
        assert contact.email is None
        assert contact.phone is None
        assert contact.additional_emails == []
        assert contact.additional_phones == []
    
    def test_invalid_email_format(self):
        """Test email validation."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyContact(email="not-an-email")
        
        assert "Invalid email format" in str(exc_info.value)
        
        # Valid email should work
        contact = CompanyContact(email="valid@example.com")
        assert contact.email == "valid@example.com"
    
    def test_invalid_phone_format(self):
        """Test phone validation."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyContact(phone="123")  # Too short
        
        assert "Phone number too short" in str(exc_info.value)
        
        # Valid phone should work
        contact = CompanyContact(phone="+1-555-123-4567")
        assert contact.phone == "+1-555-123-4567"
    
    def test_additional_emails_validation(self):
        """Test additional emails validation filters invalid ones."""
        contact = CompanyContact(
            additional_emails=["valid@example.com", "invalid-email", "another@valid.com"]
        )
        
        # Should filter out invalid email
        assert len(contact.additional_emails) == 2
        assert "valid@example.com" in contact.additional_emails
        assert "another@valid.com" in contact.additional_emails
        assert "invalid-email" not in contact.additional_emails
    
    def test_additional_phones_validation(self):
        """Test additional phones validation filters invalid ones."""
        contact = CompanyContact(
            additional_phones=["+1-555-123-4567", "123", "+1-555-987-6543"]  # Middle one too short
        )
        
        # Should filter out invalid phone
        assert len(contact.additional_phones) == 2
        assert "+1-555-123-4567" in contact.additional_phones
        assert "+1-555-987-6543" in contact.additional_phones
        assert "123" not in contact.additional_phones


class TestCompanySocial:
    """Test CompanySocial model."""
    
    def test_valid_social_linkedin(self):
        """Test valid LinkedIn social media."""
        social = CompanySocial(
            platform=SocialPlatformType.LINKEDIN,
            url="https://linkedin.com/company/openai",
            username="openai",
            followers_count=250000,
            verified=True
        )
        
        assert social.platform == SocialPlatformType.LINKEDIN
        assert str(social.url) == "https://linkedin.com/company/openai"
        assert social.username == "openai"
        assert social.followers_count == 250000
        assert social.verified is True
    
    def test_valid_social_twitter(self):
        """Test valid Twitter social media."""
        social = CompanySocial(
            platform=SocialPlatformType.TWITTER,
            url="https://twitter.com/openai",
            username="openai"
        )
        
        assert social.platform == SocialPlatformType.TWITTER
        assert "twitter.com" in str(social.url)
    
    def test_platform_url_mismatch(self):
        """Test validation error for platform-URL mismatch."""
        with pytest.raises(ValidationError) as exc_info:
            CompanySocial(
                platform=SocialPlatformType.LINKEDIN,
                url="https://twitter.com/openai"  # Wrong domain for LinkedIn
            )
        
        assert "URL does not match platform" in str(exc_info.value)
    
    def test_negative_followers_count(self):
        """Test validation error for negative followers."""
        with pytest.raises(ValidationError):
            CompanySocial(
                platform=SocialPlatformType.LINKEDIN,
                url="https://linkedin.com/company/test",
                followers_count=-100
            )
    
    def test_optional_fields(self):
        """Test social media with minimal required fields."""
        social = CompanySocial(
            platform=SocialPlatformType.GITHUB,
            url="https://github.com/openai"
        )
        
        assert social.username is None
        assert social.followers_count is None
        assert social.verified is None


class TestCompanyBasicInfo:
    """Test CompanyBasicInfo model."""
    
    def test_valid_basic_info_full(self):
        """Test valid basic info with all fields."""
        basic_info = CompanyBasicInfo(
            name="OpenAI",
            legal_name="OpenAI, L.L.C.",
            domain="openai.com",
            website="https://openai.com",
            description="AI research and deployment company",
            tagline="Creating safe AGI that benefits all of humanity",
            industry="Artificial Intelligence",
            sector=CompanySector.TECHNOLOGY,
            founded_year=2015,
            company_size=CompanySize.MEDIUM,
            employee_count=500,
            employee_count_range="201-500",
            headquarters="San Francisco, CA, USA",
            locations=["San Francisco, CA", "London, UK"],
            stock_symbol="OPENAI",
            is_public=False
        )
        
        assert basic_info.name == "OpenAI"
        assert basic_info.legal_name == "OpenAI, L.L.C."
        assert basic_info.sector == CompanySector.TECHNOLOGY
        assert basic_info.founded_year == 2015
        assert basic_info.employee_count == 500
        assert len(basic_info.locations) == 2
        assert basic_info.stock_symbol == "OPENAI"
    
    def test_valid_basic_info_minimal(self):
        """Test valid basic info with minimal fields."""
        basic_info = CompanyBasicInfo(name="TestCorp")
        
        assert basic_info.name == "TestCorp"
        assert basic_info.legal_name is None
        assert basic_info.domain is None
        assert basic_info.locations == []
    
    def test_invalid_name_empty(self):
        """Test validation error for empty name."""
        with pytest.raises(ValidationError):
            CompanyBasicInfo(name="")
    
    def test_founded_year_validation(self):
        """Test founded year validation."""
        # Valid year
        basic_info = CompanyBasicInfo(name="Test", founded_year=2000)
        assert basic_info.founded_year == 2000
        
        # Future year should raise error
        current_year = datetime.now().year
        with pytest.raises(ValidationError) as exc_info:
            CompanyBasicInfo(name="Test", founded_year=current_year + 1)
        
        assert "Founded year cannot be in the future" in str(exc_info.value)
        
        # Too old year should raise validation error from field constraints
        with pytest.raises(ValidationError):
            CompanyBasicInfo(name="Test", founded_year=1799)
        
        # Too new year should raise validation error from field constraints
        with pytest.raises(ValidationError):
            CompanyBasicInfo(name="Test", founded_year=2031)
    
    def test_stock_symbol_validation(self):
        """Test stock symbol validation."""
        # Valid stock symbols
        basic_info = CompanyBasicInfo(name="Test", stock_symbol="AAPL")
        assert basic_info.stock_symbol == "AAPL"
        
        basic_info = CompanyBasicInfo(name="Test", stock_symbol="brk.a")  # Should convert to uppercase
        assert basic_info.stock_symbol == "BRK.A"
        
        # Invalid stock symbol
        with pytest.raises(ValidationError) as exc_info:
            CompanyBasicInfo(name="Test", stock_symbol="INVALID_SYMBOL_TOO_LONG")
        
        assert "Invalid stock symbol format" in str(exc_info.value)
    
    def test_negative_employee_count(self):
        """Test validation error for negative employee count."""
        with pytest.raises(ValidationError):
            CompanyBasicInfo(name="Test", employee_count=-10)


class TestCompanyFinancials:
    """Test CompanyFinancials model."""
    
    def test_valid_financials_full(self):
        """Test valid financials with all fields."""
        financials = CompanyFinancials(
            revenue="100M+",
            revenue_currency="USD",
            funding_total="11.3B",
            funding_currency="USD",
            last_funding_round="Series C",
            last_funding_date="2023-04-28",
            valuation="29B",
            valuation_currency="USD",
            investors=["Microsoft", "Andreessen Horowitz", "Sequoia Capital"]
        )
        
        assert financials.revenue == "100M+"
        assert financials.revenue_currency == "USD"
        assert len(financials.investors) == 3
    
    def test_valid_financials_minimal(self):
        """Test valid financials with minimal fields."""
        financials = CompanyFinancials()
        
        assert financials.revenue is None
        assert financials.investors == []


class TestCompanyKeyPersonnel:
    """Test CompanyKeyPersonnel model."""
    
    def test_valid_personnel_full(self):
        """Test valid personnel with all fields."""
        personnel = CompanyKeyPersonnel(
            name="Sam Altman",
            title="CEO",
            linkedin_url="https://linkedin.com/in/sam-altman",
            email="sam@openai.com",
            bio="CEO of OpenAI, former president of Y Combinator"
        )
        
        assert personnel.name == "Sam Altman"
        assert personnel.title == "CEO"
        assert str(personnel.linkedin_url) == "https://linkedin.com/in/sam-altman"
        assert personnel.email == "sam@openai.com"
    
    def test_valid_personnel_minimal(self):
        """Test valid personnel with minimal fields."""
        personnel = CompanyKeyPersonnel(name="John Doe", title="CTO")
        
        assert personnel.name == "John Doe"
        assert personnel.title == "CTO"
        assert personnel.linkedin_url is None
        assert personnel.email is None
    
    def test_invalid_empty_name(self):
        """Test validation error for empty name."""
        with pytest.raises(ValidationError):
            CompanyKeyPersonnel(name="", title="CEO")
    
    def test_invalid_empty_title(self):
        """Test validation error for empty title."""
        with pytest.raises(ValidationError):
            CompanyKeyPersonnel(name="John Doe", title="")
    
    def test_invalid_email_format(self):
        """Test validation error for invalid email."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyKeyPersonnel(
                name="John Doe", 
                title="CEO", 
                email="not-an-email"
            )
        
        assert "Invalid email format" in str(exc_info.value)


class TestCompanyInformation:
    """Test CompanyInformation model."""
    
    @pytest.fixture
    def sample_basic_info(self):
        """Sample basic info fixture."""
        return CompanyBasicInfo(
            name="OpenAI",
            domain="openai.com",
            description="AI research company"
        )
    
    @pytest.fixture
    def sample_contact(self):
        """Sample contact fixture."""
        return CompanyContact(
            email="contact@openai.com",
            phone="+1-555-123-4567"
        )
    
    @pytest.fixture
    def sample_social(self):
        """Sample social media fixture."""
        return [
            CompanySocial(
                platform=SocialPlatformType.LINKEDIN,
                url="https://linkedin.com/company/openai",
                username="openai"
            )
        ]
    
    def test_valid_company_information_full(self, sample_basic_info, sample_contact, sample_social):
        """Test valid company information with all fields."""
        company_info = CompanyInformation(
            basic_info=sample_basic_info,
            contact=sample_contact,
            social_media=sample_social,
            data_quality_score=0.85,
            completeness_score=0.75,
            confidence_score=0.90
        )
        
        assert company_info.basic_info.name == "OpenAI"
        assert company_info.contact.email == "contact@openai.com"
        assert len(company_info.social_media) == 1
        assert company_info.data_quality_score == 0.85
        assert company_info.completeness_score == 0.75
        assert company_info.confidence_score == 0.90
    
    def test_valid_company_information_minimal(self, sample_basic_info):
        """Test valid company information with minimal fields."""
        company_info = CompanyInformation(basic_info=sample_basic_info)
        
        assert company_info.basic_info.name == "OpenAI"
        assert company_info.contact is None
        assert company_info.social_media == []
        assert company_info.financials is None
        assert company_info.key_personnel == []
    
    def test_score_validation_range(self, sample_basic_info):
        """Test score validation range (0-1)."""
        # Valid scores
        company_info = CompanyInformation(
            basic_info=sample_basic_info,
            data_quality_score=0.0,
            completeness_score=1.0,
            confidence_score=0.5
        )
        
        assert company_info.data_quality_score == 0.0
        assert company_info.completeness_score == 1.0
        assert company_info.confidence_score == 0.5
        
        # Invalid scores - too low
        with pytest.raises(ValidationError):
            CompanyInformation(
                basic_info=sample_basic_info,
                data_quality_score=-0.1
            )
        
        # Invalid scores - too high
        with pytest.raises(ValidationError):
            CompanyInformation(
                basic_info=sample_basic_info,
                completeness_score=1.1
            )
    
    def test_get_primary_email(self, sample_basic_info, sample_contact):
        """Test get_primary_email method."""
        # With contact
        company_info = CompanyInformation(
            basic_info=sample_basic_info,
            contact=sample_contact
        )
        assert company_info.get_primary_email() == "contact@openai.com"
        
        # Without contact
        company_info = CompanyInformation(basic_info=sample_basic_info)
        assert company_info.get_primary_email() is None
    
    def test_get_primary_phone(self, sample_basic_info, sample_contact):
        """Test get_primary_phone method."""
        # With contact
        company_info = CompanyInformation(
            basic_info=sample_basic_info,
            contact=sample_contact
        )
        assert company_info.get_primary_phone() == "+1-555-123-4567"
        
        # Without contact
        company_info = CompanyInformation(basic_info=sample_basic_info)
        assert company_info.get_primary_phone() is None
    
    def test_get_social_by_platform(self, sample_basic_info, sample_social):
        """Test get_social_by_platform method."""
        company_info = CompanyInformation(
            basic_info=sample_basic_info,
            social_media=sample_social
        )
        
        # Find existing platform
        linkedin = company_info.get_social_by_platform(SocialPlatformType.LINKEDIN)
        assert linkedin is not None
        assert linkedin.platform == SocialPlatformType.LINKEDIN
        
        # Find non-existing platform
        twitter = company_info.get_social_by_platform(SocialPlatformType.TWITTER)
        assert twitter is None


class TestExtractionError:
    """Test ExtractionError model."""
    
    def test_valid_extraction_error(self):
        """Test valid extraction error."""
        error = ExtractionError(
            error_type="TimeoutError",
            error_message="Request timed out after 30 seconds",
            url="https://example.com/about"
        )
        
        assert error.error_type == "TimeoutError"
        assert error.error_message == "Request timed out after 30 seconds"
        assert error.url == "https://example.com/about"
        assert isinstance(error.timestamp, datetime)
    
    def test_extraction_error_minimal(self):
        """Test extraction error with minimal fields."""
        error = ExtractionError(
            error_type="ValidationError",
            error_message="Invalid data format"
        )
        
        assert error.error_type == "ValidationError"
        assert error.error_message == "Invalid data format"
        assert error.url is None


class TestExtractionMetadata:
    """Test ExtractionMetadata model."""
    
    def test_valid_extraction_metadata(self):
        """Test valid extraction metadata."""
        metadata = ExtractionMetadata(
            pages_crawled=5,
            pages_attempted=7,
            extraction_time=45.2,
            sources_found=[
                "https://openai.com/about",
                "https://openai.com/contact"
            ],
            search_queries_used=[
                "OpenAI company information",
                "OpenAI contact details"
            ],
            extraction_mode_used=ExtractionMode.COMPREHENSIVE
        )
        
        assert metadata.pages_crawled == 5
        assert metadata.pages_attempted == 7
        assert metadata.extraction_time == 45.2
        assert len(metadata.sources_found) == 2
        assert len(metadata.search_queries_used) == 2
        assert metadata.extraction_mode_used == ExtractionMode.COMPREHENSIVE
    
    def test_extraction_metadata_minimal(self):
        """Test extraction metadata with minimal fields."""
        metadata = ExtractionMetadata(
            pages_crawled=0,
            pages_attempted=1,
            extraction_time=5.0,
            extraction_mode_used=ExtractionMode.BASIC
        )
        
        assert metadata.pages_crawled == 0
        assert metadata.pages_attempted == 1
        assert metadata.sources_found == []
        assert metadata.search_queries_used == []
    
    def test_negative_values_validation(self):
        """Test validation for negative values."""
        # Negative pages_crawled
        with pytest.raises(ValidationError):
            ExtractionMetadata(
                pages_crawled=-1,
                pages_attempted=1,
                extraction_time=5.0,
                extraction_mode_used=ExtractionMode.BASIC
            )
        
        # Negative extraction_time
        with pytest.raises(ValidationError):
            ExtractionMetadata(
                pages_crawled=0,
                pages_attempted=1,
                extraction_time=-1.0,
                extraction_mode_used=ExtractionMode.BASIC
            )


class TestCompanyExtractionResponse:
    """Test CompanyExtractionResponse model."""
    
    @pytest.fixture
    def sample_company_info(self):
        """Sample company information."""
        return CompanyInformation(
            basic_info=CompanyBasicInfo(name="OpenAI", domain="openai.com")
        )
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample extraction metadata."""
        return ExtractionMetadata(
            pages_crawled=3,
            pages_attempted=5,
            extraction_time=30.5,
            extraction_mode_used=ExtractionMode.COMPREHENSIVE
        )
    
    def test_valid_successful_response(self, sample_company_info, sample_metadata):
        """Test valid successful extraction response."""
        response = CompanyExtractionResponse(
            request_id="req_123456789",
            company_name="OpenAI",
            success=True,
            company_information=sample_company_info,
            extraction_metadata=sample_metadata,
            processing_time=32.1
        )
        
        assert response.request_id == "req_123456789"
        assert response.company_name == "OpenAI"
        assert response.success is True
        assert response.company_information is not None
        assert response.company_information.basic_info.name == "OpenAI"
        assert response.processing_time == 32.1
        assert isinstance(response.timestamp, datetime)
    
    def test_valid_failed_response(self, sample_metadata):
        """Test valid failed extraction response."""
        errors = [
            ExtractionError(
                error_type="TimeoutError",
                error_message="Request timed out"
            )
        ]
        
        response = CompanyExtractionResponse(
            request_id="req_987654321",
            company_name="FailedCorp",
            success=False,
            extraction_metadata=sample_metadata,
            errors=errors,
            warnings=["Limited data availability"],
            processing_time=15.0
        )
        
        assert response.success is False
        assert response.company_information is None
        assert len(response.errors) == 1
        assert len(response.warnings) == 1
        assert response.warnings[0] == "Limited data availability"
    
    def test_has_errors_method(self, sample_metadata):
        """Test has_errors method."""
        # No errors
        response = CompanyExtractionResponse(
            request_id="req_1",
            company_name="Test",
            success=True,
            extraction_metadata=sample_metadata,
            processing_time=10.0
        )
        assert response.has_errors() is False
        
        # With errors
        response.errors = [
            ExtractionError(error_type="TestError", error_message="Test")
        ]
        assert response.has_errors() is True
    
    def test_has_warnings_method(self, sample_metadata):
        """Test has_warnings method."""
        # No warnings
        response = CompanyExtractionResponse(
            request_id="req_1",
            company_name="Test",
            success=True,
            extraction_metadata=sample_metadata,
            processing_time=10.0
        )
        assert response.has_warnings() is False
        
        # With warnings
        response.warnings = ["Test warning"]
        assert response.has_warnings() is True
    
    def test_get_error_summary_method(self, sample_metadata):
        """Test get_error_summary method."""
        # No errors
        response = CompanyExtractionResponse(
            request_id="req_1",
            company_name="Test",
            success=True,
            extraction_metadata=sample_metadata,
            processing_time=10.0
        )
        assert response.get_error_summary() == "No errors"
        
        # With errors
        errors = [
            ExtractionError(error_type="TimeoutError", error_message="Timeout 1"),
            ExtractionError(error_type="ValidationError", error_message="Validation 1"),
            ExtractionError(error_type="TimeoutError", error_message="Timeout 2")
        ]
        response.errors = errors
        
        summary = response.get_error_summary()
        assert "3 errors" in summary
        assert "TimeoutError" in summary
        assert "ValidationError" in summary
    
    def test_negative_processing_time(self, sample_metadata):
        """Test validation error for negative processing time."""
        with pytest.raises(ValidationError):
            CompanyExtractionResponse(
                request_id="req_1",
                company_name="Test",
                success=True,
                extraction_metadata=sample_metadata,
                processing_time=-1.0
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])