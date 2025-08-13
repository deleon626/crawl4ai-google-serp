"""
Company Information Parser

This module provides robust parsing of web content to extract structured company information.
It extracts contact details, social media profiles, and business data from various web sources
including company websites, about pages, and structured data.
"""

import logging
import re
import json
from typing import List, Dict, Any, Optional, Tuple, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag

from app.models.company import (
    CompanyInformation, CompanyBasicInfo, CompanyContact, CompanySocial,
    CompanyFinancials, CompanyKeyPersonnel, SocialPlatformType, 
    CompanySize, CompanySector
)

# Set up logging
logger = logging.getLogger(__name__)


class CompanyInformationParser:
    """
    Production-ready company information parser.
    
    Extracts structured company data from web content including contact information,
    social media profiles, business details, and structured data with confidence scoring.
    """
    
    # Email patterns with exclusion filters
    EMAIL_PATTERNS = [
        # Standard email pattern
        r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
    ]
    
    # Email patterns to exclude (common non-business emails)
    EMAIL_EXCLUSIONS = [
        r'.*@(gmail\.com|yahoo\.com|hotmail\.com|outlook\.com)$',
        r'.*@(example\.com|test\.com|domain\.com)$',
        r'.*(no-?reply|noreply|donotreply).*',
        r'.*(support|help|contact|info)@.*',  # Will be handled separately
    ]
    
    # Phone number patterns with international support
    PHONE_PATTERNS = [
        # International format: +1-234-567-8900
        r'\+\d{1,4}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
        # US format variations: (123) 456-7890, 123-456-7890, 123.456.7890
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        # General pattern: any sequence of 7-15 digits with separators
        r'(?:\+?\d{1,4}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{4,9}',
    ]
    
    # Social media platform patterns
    SOCIAL_PATTERNS = {
        SocialPlatformType.LINKEDIN: [
            r'(?:https?://)?(?:www\.)?linkedin\.com/(?:company|in)/([^/\s?]+)',
            r'(?:https?://)?(?:www\.)?linkedin\.com/company/([^/\s?]+)',
        ],
        SocialPlatformType.TWITTER: [
            r'(?:https?://)?(?:www\.)?(?:twitter|x)\.com/([^/\s?]+)',
        ],
        SocialPlatformType.FACEBOOK: [
            r'(?:https?://)?(?:www\.)?facebook\.com/([^/\s?]+)',
        ],
        SocialPlatformType.INSTAGRAM: [
            r'(?:https?://)?(?:www\.)?instagram\.com/([^/\s?]+)',
        ],
        SocialPlatformType.YOUTUBE: [
            r'(?:https?://)?(?:www\.)?youtube\.com/(?:c/|channel/|user/)?([^/\s?]+)',
        ],
        SocialPlatformType.GITHUB: [
            r'(?:https?://)?(?:www\.)?github\.com/([^/\s?]+)',
        ],
        SocialPlatformType.TIKTOK: [
            r'(?:https?://)?(?:www\.)?tiktok\.com/@?([^/\s?]+)',
        ],
        SocialPlatformType.CRUNCHBASE: [
            r'(?:https?://)?(?:www\.)?crunchbase\.com/organization/([^/\s?]+)',
        ],
    }
    
    # Address pattern keywords and indicators
    ADDRESS_PATTERNS = [
        # Street address patterns
        r'\d+\s+[A-Za-z0-9\s,.-]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Lane|Ln|Way|Plaza|Place|Pl|Court|Ct)',
        # P.O. Box patterns
        r'(?:P\.?O\.?\s+)?Box\s+\d+',
        # General address with city, state patterns
        r'\d+\s+[^,\n]+,\s*[A-Za-z\s]+,?\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?',
    ]
    
    # CSS selectors for different content types
    SELECTORS = {
        # Company information sections
        'company_info': [
            '.about', '.company-info', '.company-description',
            '[class*="about"]', '[class*="company"]',
            '#about', '#company-info', '#description',
        ],
        
        # Contact information sections
        'contact_info': [
            '.contact', '.contact-info', '.contact-us',
            '[class*="contact"]', '[class*="address"]',
            '#contact', '#contact-info', '#contact-us',
            'footer', '.footer', '#footer',
        ],
        
        # Social media links
        'social_links': [
            '.social', '.social-links', '.social-media',
            '[class*="social"]', '[href*="linkedin"]', '[href*="twitter"]',
            '[href*="facebook"]', '[href*="instagram"]', '[href*="youtube"]',
            'a[href*="linkedin.com"]', 'a[href*="twitter.com"]', 
            'a[href*="x.com"]', 'a[href*="facebook.com"]',
            'a[href*="instagram.com"]', 'a[href*="youtube.com"]',
            'a[href*="github.com"]', 'a[href*="tiktok.com"]',
            'a[href*="crunchbase.com"]',
        ],
        
        # Meta tags for descriptions and structured data
        'meta_tags': [
            'meta[name="description"]',
            'meta[property="og:description"]',
            'meta[name="keywords"]',
            'title',
        ],
        
        # Structured data
        'structured_data': [
            'script[type="application/ld+json"]',
            '[itemtype*="Organization"]',
            '[itemtype*="LocalBusiness"]',
        ],
        
        # Headers and branding
        'branding': [
            'h1', 'h2', '.logo', '.brand', '.company-name',
            '[class*="logo"]', '[class*="brand"]',
            '#logo', '#brand', 'header',
        ],
        
        # Footer and header info
        'page_structure': [
            'header', '.header', '#header',
            'footer', '.footer', '#footer',
            '.main', '#main', 'main',
        ]
    }
    
    def __init__(self, custom_selectors: Optional[Dict[str, List[str]]] = None):
        """
        Initialize the parser with configuration options.
        
        Args:
            custom_selectors: Additional CSS selectors to use for extraction
        """
        self.parser_name = 'html.parser'  # Use built-in parser to avoid lxml dependency
        
        # Merge custom selectors if provided
        if custom_selectors:
            for key, selectors in custom_selectors.items():
                if key in self.SELECTORS:
                    self.SELECTORS[key].extend(selectors)
                else:
                    self.SELECTORS[key] = selectors
        
        # Compile regex patterns for performance
        self._compile_patterns()
        
    def _compile_patterns(self):
        """Compile regex patterns for better performance."""
        self.compiled_email_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.EMAIL_PATTERNS]
        self.compiled_email_exclusions = [re.compile(pattern, re.IGNORECASE) for pattern in self.EMAIL_EXCLUSIONS]
        self.compiled_phone_patterns = [re.compile(pattern) for pattern in self.PHONE_PATTERNS]
        self.compiled_address_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.ADDRESS_PATTERNS]
        
        # Compile social media patterns
        self.compiled_social_patterns = {}
        for platform, patterns in self.SOCIAL_PATTERNS.items():
            self.compiled_social_patterns[platform] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def extract_company_information(
        self,
        html_content: str,
        url: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> CompanyInformation:
        """
        Main method to extract company information from HTML content.
        
        Args:
            html_content: Raw HTML content to parse
            url: Source URL for context
            company_name: Known company name for validation
            
        Returns:
            CompanyInformation object with extracted data and confidence scores
        """
        if not html_content or not html_content.strip():
            logger.warning("Empty HTML content provided")
            return self._create_empty_company_info(company_name or "Unknown")
            
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, self.parser_name)
            
            logger.debug(f"Parsing HTML content: {len(html_content)} chars from {url}")
            
            # Extract different types of information
            basic_info = self._extract_basic_info(soup, url, company_name)
            contact_info = self._extract_contact_info(soup)
            social_media = self._extract_social_media(soup)
            financials = self._extract_financial_info(soup)
            key_personnel = self._extract_key_personnel(soup)
            
            # Extract from structured data (JSON-LD)
            structured_data = self._extract_from_structured_data(soup)
            
            # Merge structured data with extracted data
            basic_info = self._merge_basic_info(basic_info, structured_data.get('basic_info'))
            if structured_data.get('contact_info'):
                contact_info = self._merge_contact_info(contact_info, structured_data.get('contact_info'))
            
            # Calculate confidence scores
            confidence_score = self._calculate_confidence_score(
                basic_info, contact_info, social_media, financials, key_personnel
            )
            data_quality_score = self._calculate_data_quality_score(basic_info, contact_info, social_media)
            completeness_score = self._calculate_completeness_score(
                basic_info, contact_info, social_media, financials, key_personnel
            )
            
            # Create company information object
            company_info = CompanyInformation(
                basic_info=basic_info,
                contact=contact_info,
                social_media=social_media,
                financials=financials,
                key_personnel=key_personnel,
                confidence_score=confidence_score,
                data_quality_score=data_quality_score,
                completeness_score=completeness_score
            )
            
            logger.info(f"Successfully extracted company information: {basic_info.name}, "
                       f"confidence: {confidence_score:.2f}")
            
            return company_info
            
        except Exception as e:
            logger.error(f"Error extracting company information from {url}: {str(e)}", exc_info=True)
            return self._create_empty_company_info(company_name or "Unknown")
    
    def _extract_basic_info(
        self, 
        soup: BeautifulSoup, 
        url: Optional[str] = None,
        known_name: Optional[str] = None
    ) -> CompanyBasicInfo:
        """Extract basic company information."""
        logger.debug("Extracting basic company information")
        
        # Extract company name
        name = self._extract_company_name(soup, known_name)
        
        # Extract domain from URL
        domain = None
        website = None
        if url:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace('www.', '')
            website = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Extract description
        description = self._extract_description(soup)
        
        # Extract industry and sector
        industry, sector = self._extract_industry_info(soup)
        
        # Extract size information
        company_size, employee_count, employee_count_range = self._extract_size_info(soup)
        
        # Extract location information
        headquarters, locations = self._extract_location_info(soup)
        
        # Extract founding information
        founded_year = self._extract_founded_year(soup)
        
        # Extract stock information
        stock_symbol, is_public = self._extract_stock_info(soup)
        
        return CompanyBasicInfo(
            name=name,
            domain=domain,
            website=website,
            description=description,
            industry=industry,
            sector=sector,
            founded_year=founded_year,
            company_size=company_size,
            employee_count=employee_count,
            employee_count_range=employee_count_range,
            headquarters=headquarters,
            locations=locations,
            stock_symbol=stock_symbol,
            is_public=is_public
        )
    
    def _extract_company_name(self, soup: BeautifulSoup, known_name: Optional[str] = None) -> str:
        """Extract company name from various sources."""
        if known_name:
            return known_name
            
        # Try title tag first
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            # Extract company name from title patterns
            patterns = [
                r'^([^|]+)\|',  # "Company Name | Page Title"
                r'^([^-]+)-',   # "Company Name - Page Title" 
                r'^(.+?)(?:\s*-\s*.+)?$',  # Extract first part before dash
            ]
            
            for pattern in patterns:
                match = re.match(pattern, title_text, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    if len(name) > 2 and 'home' not in name.lower():
                        return name
        
        # Try h1 tags
        for h1 in soup.find_all('h1', limit=3):
            text = h1.get_text(strip=True)
            if len(text) > 2 and len(text) < 100:
                return text
        
        # Try logo alt text
        logo_imgs = soup.find_all('img', {'alt': re.compile(r'.+logo.+', re.IGNORECASE)})
        for img in logo_imgs:
            alt_text = img.get('alt', '').strip()
            if alt_text and 'logo' not in alt_text.lower():
                return alt_text
        
        # Try meta tags
        og_title = soup.find('meta', property='og:title')
        if og_title:
            return og_title.get('content', '').strip()
        
        return "Unknown Company"
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract company description from meta tags and content."""
        # Try meta description first
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            desc = meta_desc.get('content', '').strip()
            if desc and len(desc) > 20:
                return desc
        
        # Try OpenGraph description
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            desc = og_desc.get('content', '').strip()
            if desc and len(desc) > 20:
                return desc
        
        # Try to find description in about sections
        for selector in self.SELECTORS['company_info']:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if len(text) > 50 and len(text) < 500:
                    # Clean up the text
                    text = re.sub(r'\s+', ' ', text)
                    return text
        
        return None
    
    def _extract_industry_info(self, soup: BeautifulSoup) -> Tuple[Optional[str], Optional[CompanySector]]:
        """Extract industry and sector information."""
        industry_keywords = {
            CompanySector.TECHNOLOGY: ['tech', 'software', 'ai', 'artificial intelligence', 'saas', 'cloud'],
            CompanySector.FINANCE: ['finance', 'financial', 'banking', 'investment', 'fintech'],
            CompanySector.HEALTHCARE: ['health', 'medical', 'pharma', 'biotech', 'healthcare'],
            CompanySector.RETAIL: ['retail', 'ecommerce', 'shopping', 'commerce'],
            CompanySector.MANUFACTURING: ['manufacturing', 'industrial', 'factory', 'production'],
            CompanySector.EDUCATION: ['education', 'learning', 'school', 'university', 'training'],
            CompanySector.CONSULTING: ['consulting', 'advisory', 'services', 'professional services'],
            CompanySector.REAL_ESTATE: ['real estate', 'property', 'realty'],
            CompanySector.MEDIA: ['media', 'publishing', 'entertainment', 'content'],
            CompanySector.ENERGY: ['energy', 'oil', 'gas', 'renewable', 'solar', 'wind'],
        }
        
        # Get page text for keyword analysis
        page_text = soup.get_text().lower()
        
        # Try meta keywords first
        keywords_meta = soup.find('meta', {'name': 'keywords'})
        if keywords_meta:
            keywords_text = keywords_meta.get('content', '').lower()
            page_text = keywords_text + ' ' + page_text
        
        # Score each sector based on keyword matches
        sector_scores = {}
        for sector, keywords in industry_keywords.items():
            score = 0
            for keyword in keywords:
                score += page_text.count(keyword.lower())
            if score > 0:
                sector_scores[sector] = score
        
        # Get the highest scoring sector
        if sector_scores:
            best_sector = max(sector_scores, key=sector_scores.get)
            # Extract more specific industry from the text around keywords
            for keyword in industry_keywords[best_sector]:
                if keyword in page_text:
                    return keyword.title(), best_sector
            return None, best_sector
        
        return None, None
    
    def _extract_size_info(self, soup: BeautifulSoup) -> Tuple[Optional[CompanySize], Optional[int], Optional[str]]:
        """Extract company size information."""
        page_text = soup.get_text().lower()
        
        # Look for employee count patterns
        employee_patterns = [
            r'(\d+[\-–]?\d*)\s*employees?',
            r'team\s+of\s+(\d+)',
            r'staff\s+of\s+(\d+)',
            r'(\d+)\+?\s*people',
        ]
        
        employee_count = None
        employee_count_range = None
        
        for pattern in employee_patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                try:
                    if '-' in match or '–' in match:
                        employee_count_range = match
                        # Extract approximate count from range
                        numbers = re.findall(r'\d+', match)
                        if numbers:
                            employee_count = int(numbers[0])  # Use lower bound
                    else:
                        employee_count = int(match.replace('+', ''))
                        break
                except ValueError:
                    continue
        
        # Determine company size category
        company_size = None
        if employee_count:
            if employee_count <= 10:
                company_size = CompanySize.STARTUP
            elif employee_count <= 50:
                company_size = CompanySize.SMALL
            elif employee_count <= 250:
                company_size = CompanySize.MEDIUM
            elif employee_count <= 1000:
                company_size = CompanySize.LARGE
            else:
                company_size = CompanySize.ENTERPRISE
        
        return company_size, employee_count, employee_count_range
    
    def _extract_location_info(self, soup: BeautifulSoup) -> Tuple[Optional[str], List[str]]:
        """Extract headquarters and office locations."""
        headquarters = None
        locations = []
        
        # Look for address patterns in contact sections and footer
        for selector in self.SELECTORS['contact_info'] + self.SELECTORS['page_structure']:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text()
                
                # Find addresses using compiled patterns
                for pattern in self.compiled_address_patterns:
                    matches = pattern.findall(text)
                    for match in matches:
                        clean_address = match.strip()
                        if len(clean_address) > 10:
                            if not headquarters:
                                headquarters = clean_address
                            elif clean_address not in locations:
                                locations.append(clean_address)
        
        # Try to extract city/state from structured text
        if not headquarters:
            location_patterns = [
                r'(?:headquarters?|located|based)\s+(?:in|at)?\s*([^,\n]+(?:,\s*[A-Z]{2})?)',
                r'([A-Za-z\s]+,\s*[A-Z]{2})',  # City, State format
            ]
            
            page_text = soup.get_text()
            for pattern in location_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    clean_location = match.strip()
                    if len(clean_location) > 5 and len(clean_location) < 100:
                        headquarters = clean_location
                        break
                if headquarters:
                    break
        
        return headquarters, locations
    
    def _extract_founded_year(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract company founding year."""
        page_text = soup.get_text()
        
        # Look for founding year patterns
        patterns = [
            r'(?:founded|established|since)\s+(?:in\s+)?(\d{4})',
            r'(?:est\.?|since)\s+(\d{4})',
            r'(\d{4})\s*[-–]\s*present',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for match in matches:
                try:
                    year = int(match)
                    if 1800 <= year <= 2030:  # Reasonable year range
                        return year
                except ValueError:
                    continue
        
        return None
    
    def _extract_stock_info(self, soup: BeautifulSoup) -> Tuple[Optional[str], Optional[bool]]:
        """Extract stock symbol and public status."""
        page_text = soup.get_text()
        
        # Look for stock symbol patterns
        stock_patterns = [
            r'(?:nasdaq|nyse|stock):\s*([A-Z]{1,5})',
            r'ticker:\s*([A-Z]{1,5})',
            r'\(([A-Z]{2,5})\)',  # Symbol in parentheses
        ]
        
        stock_symbol = None
        for pattern in stock_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for match in matches:
                if len(match) <= 5 and match.isupper():
                    stock_symbol = match
                    break
            if stock_symbol:
                break
        
        # Determine if public
        is_public = None
        if stock_symbol:
            is_public = True
        else:
            # Look for private/public indicators
            if re.search(r'\b(?:private|privately held)\b', page_text, re.IGNORECASE):
                is_public = False
            elif re.search(r'\b(?:public|publicly traded|listed)\b', page_text, re.IGNORECASE):
                is_public = True
        
        return stock_symbol, is_public
    
    def _extract_contact_info(self, soup: BeautifulSoup) -> Optional[CompanyContact]:
        """Extract contact information including email, phone, and address."""
        logger.debug("Extracting contact information")
        
        # Get text from contact-related sections
        contact_text = ""
        for selector in self.SELECTORS['contact_info']:
            elements = soup.select(selector)
            for element in elements:
                contact_text += element.get_text() + "\n"
        
        if not contact_text.strip():
            contact_text = soup.get_text()
        
        # Extract emails
        emails = self._extract_emails(contact_text)
        primary_email = emails[0] if emails else None
        additional_emails = emails[1:] if len(emails) > 1 else []
        
        # Extract phone numbers
        phones = self._extract_phone_numbers(contact_text)
        primary_phone = phones[0] if phones else None
        additional_phones = phones[1:] if len(phones) > 1 else []
        
        # Extract address components
        address_info = self._extract_address_components(contact_text)
        
        # Create contact object if we have any contact information
        if any([primary_email, primary_phone, address_info.get('address')]):
            return CompanyContact(
                email=primary_email,
                phone=primary_phone,
                address=address_info.get('address'),
                city=address_info.get('city'),
                state=address_info.get('state'),
                country=address_info.get('country'),
                postal_code=address_info.get('postal_code'),
                additional_emails=additional_emails,
                additional_phones=additional_phones
            )
        
        return None
    
    def _extract_emails(self, text: str) -> List[str]:
        """Extract and validate email addresses from text."""
        emails = set()
        
        for pattern in self.compiled_email_patterns:
            matches = pattern.findall(text)
            for match in matches:
                email = match.lower().strip()
                
                # Check exclusion patterns
                excluded = False
                for exclusion in self.compiled_email_exclusions:
                    if exclusion.match(email):
                        excluded = True
                        break
                
                if not excluded:
                    # Basic email format validation
                    if self._is_valid_email(email):
                        emails.add(email)
        
        return list(emails)
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation using regex."""
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        return bool(email_pattern.match(email))
    
    def _extract_phone_numbers(self, text: str) -> List[str]:
        """Extract and validate phone numbers from text."""
        phones = set()
        
        for pattern in self.compiled_phone_patterns:
            matches = pattern.findall(text)
            for match in matches:
                phone = match.strip()
                
                # Basic validation
                clean_phone = re.sub(r'[^\d+]', '', phone)
                if len(clean_phone) >= 7:  # Minimum reasonable length
                    phones.add(phone)
        
        return list(phones)
    
    def _extract_address_components(self, text: str) -> Dict[str, Optional[str]]:
        """Extract address components from text."""
        address_info = {
            'address': None,
            'city': None,
            'state': None,
            'country': None,
            'postal_code': None
        }
        
        # Extract full addresses
        for pattern in self.compiled_address_patterns:
            matches = pattern.findall(text)
            for match in matches:
                clean_match = match.strip()
                # Ensure it's actually an address, not just a phone number
                if len(clean_match) > 10 and not re.match(r'^\+?[\d\s\-\(\)\.]+$', clean_match):
                    address_info['address'] = clean_match
                    
                    # Try to extract components from the address
                    # Look for ZIP/postal codes
                    zip_match = re.search(r'\b\d{5}(?:-\d{4})?\b', clean_match)
                    if zip_match:
                        address_info['postal_code'] = zip_match.group()
                    
                    # Look for state codes (2 letters before ZIP)
                    state_match = re.search(r'\b([A-Z]{2})\s*\d{5}', clean_match)
                    if state_match:
                        address_info['state'] = state_match.group(1)
                    
                    # Extract city (text before state and ZIP)
                    city_match = re.search(r',\s*([^,]+),\s*[A-Z]{2}\s*\d{5}', clean_match)
                    if city_match:
                        address_info['city'] = city_match.group(1).strip()
                    
                    break
        
        return address_info
    
    def _extract_social_media(self, soup: BeautifulSoup) -> List[CompanySocial]:
        """Extract social media profiles."""
        logger.debug("Extracting social media information")
        
        social_profiles = []
        found_urls = set()
        
        # Find all links
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '').strip()
            if not href or href.startswith('#'):
                continue
            
            # Check each platform pattern
            for platform, patterns in self.compiled_social_patterns.items():
                for pattern in patterns:
                    match = pattern.search(href)
                    if match and href not in found_urls:
                        try:
                            # Extract username if available
                            username = match.group(1) if match.groups() else None
                            
                            # Create social profile
                            social_profile = CompanySocial(
                                platform=platform,
                                url=href,
                                username=username
                            )
                            
                            social_profiles.append(social_profile)
                            found_urls.add(href)
                            break
                        except Exception as e:
                            logger.debug(f"Error creating social profile for {href}: {e}")
                            continue
                
                if href in found_urls:
                    break
        
        logger.debug(f"Found {len(social_profiles)} social media profiles")
        return social_profiles
    
    def _extract_financial_info(self, soup: BeautifulSoup) -> Optional[CompanyFinancials]:
        """Extract financial information from content."""
        # This is a basic implementation - would need more sophisticated parsing
        # for actual financial data extraction
        page_text = soup.get_text()
        
        # Look for funding/revenue patterns
        funding_patterns = [
            r'raised\s+\$?([\d.]+[MBK]?)\s*(?:million|billion|thousand)?',
            r'funding[:\s]+\$?([\d.]+[MBK]?)',
            r'valuation[:\s]+\$?([\d.]+[MBK]?)',
        ]
        
        financials_data = {}
        
        for pattern in funding_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                amount = matches[0]
                if 'raised' in pattern or 'funding' in pattern:
                    financials_data['funding_total'] = amount
                elif 'valuation' in pattern:
                    financials_data['valuation'] = amount
        
        # Return financials object only if we found some data
        if financials_data:
            return CompanyFinancials(**financials_data)
        
        return None
    
    def _extract_key_personnel(self, soup: BeautifulSoup) -> List[CompanyKeyPersonnel]:
        """Extract key personnel information."""
        # This is a basic implementation - would need more sophisticated parsing
        # for actual personnel extraction
        personnel = []
        
        # Look for common executive titles
        page_text = soup.get_text()
        executive_patterns = [
            r'([\w\s]+),?\s+(CEO|CTO|CFO|COO|President|Founder)',
        ]
        
        for pattern in executive_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for name, title in matches[:5]:  # Limit to 5 personnel
                name = name.strip()
                if len(name) > 2 and len(name) < 50:
                    personnel.append(CompanyKeyPersonnel(
                        name=name,
                        title=title.upper()
                    ))
        
        return personnel
    
    def _extract_from_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract information from structured data (JSON-LD)."""
        logger.debug("Extracting structured data")
        
        structured_info = {}
        
        # Find JSON-LD scripts
        json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
        
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string or '{}')
                
                # Handle arrays of structured data
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            structured_info.update(self._parse_structured_data_item(item))
                elif isinstance(data, dict):
                    structured_info.update(self._parse_structured_data_item(data))
                    
            except (json.JSONDecodeError, TypeError) as e:
                logger.debug(f"Error parsing JSON-LD: {e}")
                continue
        
        return structured_info
    
    def _parse_structured_data_item(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse individual structured data item."""
        parsed = {}
        
        data_type = data.get('@type', '').lower()
        
        if data_type in ['organization', 'localbusiness', 'corporation']:
            basic_info = {}
            contact_info = {}
            
            # Extract basic information
            if 'name' in data:
                basic_info['name'] = data['name']
            if 'description' in data:
                basic_info['description'] = data['description']
            if 'url' in data:
                basic_info['website'] = data['url']
            if 'foundingDate' in data:
                try:
                    year = int(data['foundingDate'][:4])
                    basic_info['founded_year'] = year
                except (ValueError, TypeError):
                    pass
            
            # Extract contact information
            if 'email' in data:
                contact_info['email'] = data['email']
            if 'telephone' in data:
                contact_info['phone'] = data['telephone']
            
            # Extract address
            if 'address' in data:
                address_data = data['address']
                if isinstance(address_data, dict):
                    address_parts = []
                    if 'streetAddress' in address_data:
                        address_parts.append(address_data['streetAddress'])
                    if 'addressLocality' in address_data:
                        contact_info['city'] = address_data['addressLocality']
                        address_parts.append(address_data['addressLocality'])
                    if 'addressRegion' in address_data:
                        contact_info['state'] = address_data['addressRegion']
                        address_parts.append(address_data['addressRegion'])
                    if 'postalCode' in address_data:
                        contact_info['postal_code'] = address_data['postalCode']
                        address_parts.append(address_data['postalCode'])
                    if 'addressCountry' in address_data:
                        contact_info['country'] = address_data['addressCountry']
                    
                    if address_parts:
                        contact_info['address'] = ', '.join(address_parts)
            
            if basic_info:
                parsed['basic_info'] = basic_info
            if contact_info:
                parsed['contact_info'] = contact_info
        
        return parsed
    
    def _merge_basic_info(self, extracted: CompanyBasicInfo, structured: Optional[Dict]) -> CompanyBasicInfo:
        """Merge basic info from different sources."""
        if not structured:
            return extracted
        
        # Update fields with structured data if extracted data is missing
        updates = {}
        if not extracted.name and structured.get('name'):
            updates['name'] = structured['name']
        if not extracted.description and structured.get('description'):
            updates['description'] = structured['description']
        if not extracted.website and structured.get('website'):
            updates['website'] = structured['website']
        if not extracted.founded_year and structured.get('founded_year'):
            updates['founded_year'] = structured['founded_year']
        
        if updates:
            # Create new instance with updates
            return extracted.model_copy(update=updates)
        
        return extracted
    
    def _merge_contact_info(self, extracted: Optional[CompanyContact], structured: Dict) -> CompanyContact:
        """Merge contact info from different sources."""
        if not extracted:
            # Create new contact info from structured data
            return CompanyContact(**structured)
        
        # Update missing fields
        updates = {}
        if not extracted.email and structured.get('email'):
            updates['email'] = structured['email']
        if not extracted.phone and structured.get('phone'):
            updates['phone'] = structured['phone']
        if not extracted.address and structured.get('address'):
            updates['address'] = structured['address']
        if not extracted.city and structured.get('city'):
            updates['city'] = structured['city']
        if not extracted.state and structured.get('state'):
            updates['state'] = structured['state']
        if not extracted.country and structured.get('country'):
            updates['country'] = structured['country']
        if not extracted.postal_code and structured.get('postal_code'):
            updates['postal_code'] = structured['postal_code']
        
        if updates:
            return extracted.model_copy(update=updates)
        
        return extracted
    
    def _calculate_confidence_score(
        self,
        basic_info: CompanyBasicInfo,
        contact: Optional[CompanyContact],
        social_media: List[CompanySocial],
        financials: Optional[CompanyFinancials],
        personnel: List[CompanyKeyPersonnel]
    ) -> float:
        """Calculate confidence score based on data quality and completeness."""
        score = 0.0
        max_score = 100.0
        
        # Basic info scoring (40 points)
        if basic_info.name and basic_info.name != "Unknown Company":
            score += 15
        if basic_info.description and len(basic_info.description) > 20:
            score += 10
        if basic_info.website:
            score += 10
        if basic_info.industry or basic_info.sector:
            score += 5
        
        # Contact info scoring (30 points)
        if contact:
            if contact.email:
                score += 15
            if contact.phone:
                score += 10
            if contact.address:
                score += 5
        
        # Social media scoring (20 points)
        social_score = min(len(social_media) * 4, 20)
        score += social_score
        
        # Additional data scoring (10 points)
        if financials:
            score += 5
        if personnel:
            score += 5
        
        return round(score / max_score, 2)
    
    def _calculate_data_quality_score(
        self,
        basic_info: CompanyBasicInfo,
        contact: Optional[CompanyContact],
        social_media: List[CompanySocial]
    ) -> float:
        """Calculate data quality score based on validation and completeness."""
        quality_factors = []
        
        # Name quality
        if basic_info.name and len(basic_info.name) > 2:
            quality_factors.append(1.0)
        else:
            quality_factors.append(0.0)
        
        # Description quality
        if basic_info.description:
            desc_quality = min(len(basic_info.description) / 100, 1.0)
            quality_factors.append(desc_quality)
        else:
            quality_factors.append(0.0)
        
        # Contact quality
        contact_quality = 0.0
        if contact:
            if contact.email:
                contact_quality += 0.4
            if contact.phone:
                contact_quality += 0.3
            if contact.address:
                contact_quality += 0.3
        quality_factors.append(contact_quality)
        
        # Social media quality
        social_quality = min(len(social_media) / 3, 1.0)  # Up to 3 platforms for max score
        quality_factors.append(social_quality)
        
        return round(sum(quality_factors) / len(quality_factors), 2)
    
    def _calculate_completeness_score(
        self,
        basic_info: CompanyBasicInfo,
        contact: Optional[CompanyContact],
        social_media: List[CompanySocial],
        financials: Optional[CompanyFinancials],
        personnel: List[CompanyKeyPersonnel]
    ) -> float:
        """Calculate completeness score based on available information."""
        total_fields = 20  # Total expected fields
        filled_fields = 0
        
        # Count filled basic info fields
        basic_fields = [
            basic_info.name, basic_info.description, basic_info.website,
            basic_info.industry, basic_info.headquarters, basic_info.founded_year
        ]
        filled_fields += sum(1 for field in basic_fields if field)
        
        # Count contact fields
        if contact:
            contact_fields = [
                contact.email, contact.phone, contact.address,
                contact.city, contact.state
            ]
            filled_fields += sum(1 for field in contact_fields if field)
        
        # Count social media (up to 5 platforms)
        filled_fields += min(len(social_media), 5)
        
        # Count financials
        if financials:
            filled_fields += 2
        
        # Count personnel (up to 2)
        filled_fields += min(len(personnel), 2)
        
        return round(filled_fields / total_fields, 2)
    
    def _create_empty_company_info(self, company_name: str) -> CompanyInformation:
        """Create empty company information object."""
        basic_info = CompanyBasicInfo(name=company_name)
        
        return CompanyInformation(
            basic_info=basic_info,
            contact=None,
            social_media=[],
            financials=None,
            key_personnel=[],
            confidence_score=0.0,
            data_quality_score=0.0,
            completeness_score=0.0
        )


class CompanyParsingError(Exception):
    """Custom exception for company parsing errors."""
    pass


# Factory function for easy instantiation
def create_company_parser(custom_selectors: Optional[Dict[str, List[str]]] = None) -> CompanyInformationParser:
    """Create and return a new CompanyInformationParser instance."""
    return CompanyInformationParser(custom_selectors)