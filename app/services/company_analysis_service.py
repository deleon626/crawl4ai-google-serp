"""
Company Analysis Service
Handles company website discovery, content analysis, and employee extraction.
"""

import re
import asyncio
from typing import List, Optional, Dict, Tuple, Set
from urllib.parse import urljoin, urlparse
import time
from datetime import datetime

from app.models.company import (
    CompanyAnalysisRequest, CompanyAnalysisResponse, CompanyInfo, 
    CompanyWebsite, EmployeeProfile, EmployeeRole, ContactMethod,
    WebsiteDiscovery, EmployeeDiscoveryStats, CompanySize
)
from app.models.serp import SearchRequest, SearchResponse
from app.models.crawl import CrawlRequest
from app.services.serp_service import SERPService
from app.services.crawl_service import CrawlService
from app.utils.logging_decorators import log_operation
from app.utils.exceptions import CompanyAnalysisError


class CompanyWebsiteDiscovery:
    """Handles company website discovery via SERP"""
    
    def __init__(self):
        self.website_indicators = [
            r'(www\.)?([a-zA-Z0-9-]+\.com)',
            r'(www\.)?([a-zA-Z0-9-]+\.org)',
            r'(www\.)?([a-zA-Z0-9-]+\.net)',
        ]
        
    def generate_search_queries(self, company_name: str, context: Optional[str] = None) -> List[str]:
        """Generate SERP queries for website discovery"""
        base_queries = [
            f'"{company_name}" official website',
            f'"{company_name}" company website',
            f'{company_name} site:linkedin.com/company',
            f'{company_name} headquarters contact',
        ]
        
        if context:
            base_queries.extend([
                f'"{company_name}" {context} website',
                f'{company_name} {context} company'
            ])
            
        return base_queries
    
    def extract_company_urls(self, serp_results: List[Dict]) -> Tuple[Optional[str], List[str], Dict[str, str]]:
        """Extract company URLs from SERP results"""
        primary_website = None
        alternative_sites = []
        social_profiles = {}
        
        for result in serp_results:
            url = result.get('link', '')
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            
            # Check for social profiles
            if 'linkedin.com/company' in url:
                social_profiles['linkedin'] = url
            elif 'facebook.com' in url:
                social_profiles['facebook'] = url
            elif 'twitter.com' in url or 'x.com' in url:
                social_profiles['twitter'] = url
            elif 'instagram.com' in url:
                social_profiles['instagram'] = url
            
            # Check for primary website
            elif self._is_likely_company_website(url, title, snippet):
                if not primary_website:
                    primary_website = url
                else:
                    alternative_sites.append(url)
                    
        return primary_website, alternative_sites, social_profiles
    
    def _is_likely_company_website(self, url: str, title: str, snippet: str) -> bool:
        """Determine if URL is likely the company's official website"""
        # Skip social media and directory sites
        skip_domains = [
            'linkedin.com', 'facebook.com', 'twitter.com', 'x.com',
            'instagram.com', 'youtube.com', 'crunchbase.com',
            'glassdoor.com', 'indeed.com', 'yelp.com'
        ]
        
        for domain in skip_domains:
            if domain in url:
                return False
                
        # Look for indicators in title and snippet
        indicators = ['official', 'company', 'corporation', 'inc', 'llc', 'ltd']
        text = f"{title} {snippet}".lower()
        
        return any(indicator in text for indicator in indicators)


class EmployeeExtractor:
    """Extracts employee information from website content"""
    
    def __init__(self):
        self.name_patterns = [
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b',  # First Last
            r'\b([A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+)\b',  # First M. Last
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+)\b'  # First Middle Last
        ]
        
        self.title_patterns = [
            r'(CEO|CTO|CFO|COO|CRO)',
            r'(President|Vice President|VP)',
            r'(Director|Senior Director)',
            r'(Manager|Senior Manager)',
            r'(Engineer|Senior Engineer|Principal Engineer)',
            r'(Developer|Senior Developer|Lead Developer)',
            r'(Designer|Senior Designer|Lead Designer)',
            r'(Analyst|Senior Analyst)',
            r'(Consultant|Senior Consultant)',
            r'(Specialist|Expert)',
            r'(Coordinator|Administrator)'
        ]
        
        self.role_mapping = {
            'ceo': EmployeeRole.EXECUTIVE,
            'cto': EmployeeRole.EXECUTIVE,
            'cfo': EmployeeRole.EXECUTIVE,
            'coo': EmployeeRole.EXECUTIVE,
            'president': EmployeeRole.EXECUTIVE,
            'vice president': EmployeeRole.EXECUTIVE,
            'vp': EmployeeRole.EXECUTIVE,
            'director': EmployeeRole.MANAGEMENT,
            'manager': EmployeeRole.MANAGEMENT,
            'engineer': EmployeeRole.ENGINEERING,
            'developer': EmployeeRole.ENGINEERING,
            'designer': EmployeeRole.ENGINEERING,
            'analyst': EmployeeRole.FINANCE,
            'sales': EmployeeRole.SALES,
            'marketing': EmployeeRole.MARKETING,
            'hr': EmployeeRole.HR,
            'human resources': EmployeeRole.HR,
            'operations': EmployeeRole.OPERATIONS,
            'finance': EmployeeRole.FINANCE
        }
    
    def extract_employees(self, content: str, source_url: str) -> List[EmployeeProfile]:
        """Extract employee profiles from content"""
        employees = []
        
        # Look for structured employee sections
        employees.extend(self._extract_from_team_sections(content, source_url))
        
        # Look for individual mentions
        employees.extend(self._extract_individual_mentions(content, source_url))
        
        # Deduplicate and score
        return self._deduplicate_and_score(employees)
    
    def _extract_from_team_sections(self, content: str, source_url: str) -> List[EmployeeProfile]:
        """Extract from structured team/about sections"""
        employees = []
        
        # Look for team section patterns
        team_patterns = [
            r'<div[^>]*team[^>]*>(.*?)</div>',
            r'<section[^>]*team[^>]*>(.*?)</section>',
            r'(?i)our team(.*?)(?=<h|$)',
            r'(?i)meet the team(.*?)(?=<h|$)',
            r'(?i)leadership team(.*?)(?=<h|$)'
        ]
        
        for pattern in team_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                employees.extend(self._parse_team_section(match, source_url))
                
        return employees
    
    def _extract_individual_mentions(self, content: str, source_url: str) -> List[EmployeeProfile]:
        """Extract individual employee mentions"""
        employees = []
        
        # Look for name + title patterns
        combined_patterns = [
            r'([A-Z][a-z]+\s+[A-Z][a-z]+),?\s+(CEO|CTO|CFO|COO|President|Director|Manager|Engineer)',
            r'(CEO|CTO|CFO|COO|President|Director|Manager|Engineer):?\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        ]
        
        for pattern in combined_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match) == 2:
                    name, title = match if match[0].split()[0].isupper() else (match[1], match[0])
                    employee = self._create_employee_profile(name, title, source_url)
                    if employee:
                        employees.append(employee)
                        
        return employees
    
    def _parse_team_section(self, section: str, source_url: str) -> List[EmployeeProfile]:
        """Parse a team section for employee information"""
        employees = []
        
        # Remove HTML tags for cleaner text processing
        clean_text = re.sub(r'<[^>]+>', ' ', section)
        
        # Look for name-title pairs in the section
        for name_pattern in self.name_patterns:
            names = re.findall(name_pattern, clean_text)
            for name in names:
                # Look for title near the name
                name_pos = clean_text.find(name)
                context = clean_text[max(0, name_pos-100):name_pos+200]
                
                for title_pattern in self.title_patterns:
                    title_matches = re.findall(title_pattern, context, re.IGNORECASE)
                    if title_matches:
                        employee = self._create_employee_profile(name, title_matches[0], source_url)
                        if employee:
                            employees.append(employee)
                            break
                            
        return employees
    
    def _create_employee_profile(self, name: str, title: str, source_url: str) -> Optional[EmployeeProfile]:
        """Create employee profile from name and title"""
        if not name or not title or len(name.split()) < 2:
            return None
            
        # Determine role category
        role_category = self._categorize_role(title)
        
        # Calculate confidence based on title specificity and context
        confidence = self._calculate_confidence(name, title, source_url)
        
        if confidence < 0.3:  # Skip low confidence matches
            return None
            
        return EmployeeProfile(
            name=name.strip(),
            title=title.strip(),
            role_category=role_category,
            confidence_score=confidence,
            source_url=source_url
        )
    
    def _categorize_role(self, title: str) -> EmployeeRole:
        """Categorize employee role based on title"""
        title_lower = title.lower()
        
        for keyword, role in self.role_mapping.items():
            if keyword in title_lower:
                return role
                
        return EmployeeRole.OTHER
    
    def _calculate_confidence(self, name: str, title: str, source_url: str) -> float:
        """Calculate confidence score for employee identification"""
        confidence = 0.5  # Base confidence
        
        # Title specificity
        if any(exec_title in title.lower() for exec_title in ['ceo', 'cto', 'cfo', 'president']):
            confidence += 0.3
        elif any(mgmt_title in title.lower() for mgmt_title in ['director', 'manager', 'vp']):
            confidence += 0.2
        elif any(role_title in title.lower() for role_title in ['engineer', 'developer', 'designer']):
            confidence += 0.1
            
        # Name quality
        name_parts = name.split()
        if len(name_parts) >= 2:
            confidence += 0.1
        if len(name_parts) >= 3:
            confidence += 0.05
            
        # Source page type
        if any(page_type in source_url.lower() for page_type in ['team', 'about', 'leadership']):
            confidence += 0.1
            
        return min(confidence, 1.0)
    
    def _deduplicate_and_score(self, employees: List[EmployeeProfile]) -> List[EmployeeProfile]:
        """Remove duplicates and improve scoring"""
        seen_names = set()
        unique_employees = []
        
        # Sort by confidence first
        employees.sort(key=lambda e: e.confidence_score, reverse=True)
        
        for employee in employees:
            name_key = employee.name.lower().replace(' ', '')
            if name_key not in seen_names:
                seen_names.add(name_key)
                unique_employees.append(employee)
                
        return unique_employees


class CompanyAnalysisService:
    """Main service for company analysis"""
    
    def __init__(self):
        self.website_discovery = CompanyWebsiteDiscovery()
        self.employee_extractor = EmployeeExtractor()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    @log_operation("company_analysis")
    async def analyze_company(self, request: CompanyAnalysisRequest) -> CompanyAnalysisResponse:
        """Perform comprehensive company analysis"""
        start_time = time.time()
        
        try:
            # Phase 1: Website Discovery
            website_discovery = await self._discover_company_websites(request)
            
            if not website_discovery.primary_website:
                return CompanyAnalysisResponse(
                    success=False,
                    error_message="Could not discover company website",
                    processing_time_seconds=time.time() - start_time
                )
            
            # Phase 2: Website Analysis
            company_info = await self._analyze_company_website(
                website_discovery.primary_website, 
                request.company_name or "Unknown Company"
            )
            
            # Phase 3: Employee Extraction (if requested)
            employee_stats = None
            if request.extract_employees:
                employees, employee_stats = await self._extract_company_employees(
                    website_discovery.primary_website,
                    request.max_employees
                )
                company_info.employees = employees
            
            # Combine social profiles
            company_info.social_profiles = website_discovery.social_profiles
            
            return CompanyAnalysisResponse(
                success=True,
                company=company_info,
                website_discovery=website_discovery,
                employee_stats=employee_stats,
                processing_time_seconds=time.time() - start_time
            )
            
        except Exception as e:
            return CompanyAnalysisResponse(
                success=False,
                error_message=f"Company analysis failed: {str(e)}",
                processing_time_seconds=time.time() - start_time
            )
    
    async def _discover_company_websites(self, request: CompanyAnalysisRequest) -> WebsiteDiscovery:
        """Discover company websites using SERP"""
        search_queries = []
        
        if request.company_name:
            search_queries = self.website_discovery.generate_search_queries(
                request.company_name,
                request.additional_context
            )
        
        # If direct URL provided, use it
        if request.company_url:
            return WebsiteDiscovery(
                primary_website=request.company_url,
                confidence=1.0,
                search_queries_used=[]
            )
        
        # Search for company websites
        async with SERPService() as serp_service:
            all_results = []
            for query in search_queries:
                search_request = SearchRequest(
                    query=query,
                    country="US",
                    language="en",
                    num_results=10
                )
                response = await serp_service.search(search_request)
                if response.success:
                    all_results.extend(response.results)
        
        # Extract URLs from results
        primary_website, alternatives, social_profiles = self.website_discovery.extract_company_urls(all_results)
        
        return WebsiteDiscovery(
            primary_website=primary_website,
            alternative_websites=alternatives,
            social_profiles=social_profiles,
            confidence=0.8 if primary_website else 0.0,
            search_queries_used=search_queries
        )
    
    async def _analyze_company_website(self, website_url: str, company_name: str) -> CompanyInfo:
        """Analyze company website content"""
        async with CrawlService() as crawl_service:
            crawl_request = CrawlRequest(url=website_url)
            crawl_response = await crawl_service.crawl(crawl_request)
            
            if not crawl_response.success:
                raise CompanyAnalysisError(f"Failed to crawl website: {crawl_response.error}")
            
            content = crawl_response.content
            
            # Extract website information
            website_info = CompanyWebsite(
                url=website_url,
                title=content.get('title', ''),
                description=self._extract_description(content),
                about_content=self._extract_about_content(content),
                contact_page_url=self._find_contact_page(content, website_url),
                team_page_url=self._find_team_page(content, website_url),
                careers_page_url=self._find_careers_page(content, website_url),
                technologies=self._extract_technologies(content),
                keywords=self._extract_keywords(content)
            )
            
            # Create company info
            company_info = CompanyInfo(
                name=company_name,
                domain=urlparse(website_url).netloc,
                description=website_info.description,
                website=website_info,
                confidence_score=0.8
            )
            
            return company_info
    
    async def _extract_company_employees(self, website_url: str, max_employees: int) -> Tuple[List[EmployeeProfile], EmployeeDiscoveryStats]:
        """Extract employee information from company website"""
        stats = EmployeeDiscoveryStats()
        start_time = time.time()
        
        async with CrawlService() as crawl_service:
            # Crawl main page
            crawl_request = CrawlRequest(url=website_url)
            crawl_response = await crawl_service.crawl(crawl_request)
            
            employees = []
            stats.total_pages_crawled = 1
            
            if crawl_response.success:
                content = crawl_response.content
                main_employees = self.employee_extractor.extract_employees(
                    content.get('html', ''), website_url
                )
                employees.extend(main_employees)
                
                # Try team/about pages if found
                team_urls = self._find_additional_team_pages(content, website_url)
                for team_url in team_urls[:3]:  # Limit to 3 additional pages
                    team_request = CrawlRequest(url=team_url)
                    team_response = await crawl_service.crawl(team_request)
                    if team_response.success:
                        stats.total_pages_crawled += 1
                        team_employees = self.employee_extractor.extract_employees(
                            team_response.content.get('html', ''), team_url
                        )
                        employees.extend(team_employees)
            
            # Limit results
            employees = employees[:max_employees]
            
            # Calculate statistics
            stats.employees_found = len(employees)
            stats.high_confidence_employees = len([e for e in employees if e.confidence_score > 0.8])
            stats.roles_distribution = {}
            stats.departments_found = []
            
            for employee in employees:
                role = employee.role_category.value
                stats.roles_distribution[role] = stats.roles_distribution.get(role, 0) + 1
                
                if employee.department and employee.department not in stats.departments_found:
                    stats.departments_found.append(employee.department)
            
            stats.extraction_time_seconds = time.time() - start_time
            
            return employees, stats
    
    def _extract_description(self, content: Dict) -> Optional[str]:
        """Extract company description from content"""
        # Try meta description first
        html = content.get('html', '')
        meta_desc = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html, re.IGNORECASE)
        if meta_desc:
            return meta_desc.group(1)
        
        # Try first paragraph
        text = content.get('markdown', '')
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if paragraphs:
            return paragraphs[0][:500]  # Limit to 500 chars
            
        return None
    
    def _extract_about_content(self, content: Dict) -> Optional[str]:
        """Extract about section content"""
        html = content.get('html', '')
        
        # Look for about sections
        about_patterns = [
            r'<section[^>]*about[^>]*>(.*?)</section>',
            r'<div[^>]*about[^>]*>(.*?)</div>',
            r'(?i)about us(.*?)(?=<h|$)'
        ]
        
        for pattern in about_patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                # Clean HTML and return first 1000 chars
                clean_text = re.sub(r'<[^>]+>', ' ', match.group(1))
                return clean_text[:1000].strip()
        
        return None
    
    def _find_contact_page(self, content: Dict, base_url: str) -> Optional[str]:
        """Find contact page URL"""
        return self._find_page_url(content, base_url, ['contact', 'contact-us', 'get-in-touch'])
    
    def _find_team_page(self, content: Dict, base_url: str) -> Optional[str]:
        """Find team page URL"""
        return self._find_page_url(content, base_url, ['team', 'about', 'about-us', 'leadership'])
    
    def _find_careers_page(self, content: Dict, base_url: str) -> Optional[str]:
        """Find careers page URL"""
        return self._find_page_url(content, base_url, ['careers', 'jobs', 'join-us', 'hiring'])
    
    def _find_page_url(self, content: Dict, base_url: str, keywords: List[str]) -> Optional[str]:
        """Find specific page URL by keywords"""
        html = content.get('html', '')
        links = content.get('links', [])
        
        for link in links:
            url = link.get('url', '')
            text = link.get('text', '').lower()
            
            for keyword in keywords:
                if keyword in url.lower() or keyword in text:
                    return urljoin(base_url, url)
        
        return None
    
    def _find_additional_team_pages(self, content: Dict, base_url: str) -> List[str]:
        """Find additional team-related pages to crawl"""
        team_urls = []
        
        team_url = self._find_team_page(content, base_url)
        if team_url:
            team_urls.append(team_url)
            
        leadership_url = self._find_page_url(content, base_url, ['leadership', 'management'])
        if leadership_url and leadership_url not in team_urls:
            team_urls.append(leadership_url)
            
        return team_urls
    
    def _extract_technologies(self, content: Dict) -> List[str]:
        """Extract technologies mentioned on website"""
        text = content.get('markdown', '').lower()
        
        tech_keywords = [
            'python', 'javascript', 'typescript', 'react', 'vue', 'angular',
            'node.js', 'django', 'flask', 'fastapi', 'docker', 'kubernetes',
            'aws', 'azure', 'gcp', 'postgresql', 'mongodb', 'redis',
            'machine learning', 'ai', 'artificial intelligence'
        ]
        
        found_tech = []
        for tech in tech_keywords:
            if tech in text:
                found_tech.append(tech.title())
        
        return found_tech[:10]  # Limit to 10
    
    def _extract_keywords(self, content: Dict) -> List[str]:
        """Extract key business terms"""
        text = content.get('markdown', '').lower()
        
        business_keywords = [
            'saas', 'software', 'platform', 'service', 'solution',
            'technology', 'innovation', 'digital', 'cloud', 'mobile',
            'enterprise', 'startup', 'consulting', 'development'
        ]
        
        found_keywords = []
        for keyword in business_keywords:
            if keyword in text:
                found_keywords.append(keyword.title())
        
        return found_keywords[:10]  # Limit to 10