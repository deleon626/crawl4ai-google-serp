"""
Company analysis data models using Pydantic v2.
Handles company analysis requests/responses, employee profiles, and website data.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, validator
from enum import Enum


class CompanySize(str, Enum):
    """Company size categories"""
    STARTUP = "startup"
    SMALL = "small"
    MEDIUM = "medium" 
    LARGE = "large"
    ENTERPRISE = "enterprise"


class EmployeeRole(str, Enum):
    """Employee role categories"""
    EXECUTIVE = "executive"
    MANAGEMENT = "management"
    ENGINEERING = "engineering"
    SALES = "sales"
    MARKETING = "marketing"
    HR = "hr"
    FINANCE = "finance"
    OPERATIONS = "operations"
    OTHER = "other"


class ContactMethod(BaseModel):
    """Contact information structure"""
    type: str = Field(..., description="Contact type (email, phone, linkedin)")
    value: str = Field(..., description="Contact value")
    verified: bool = Field(default=False, description="Whether contact is verified")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")


class EmployeeProfile(BaseModel):
    """Employee profile information"""
    name: str = Field(..., description="Employee full name")
    title: str = Field(..., description="Job title or position")
    role_category: EmployeeRole = Field(..., description="Role category")
    department: Optional[str] = Field(None, description="Department or team")
    contact_methods: List[ContactMethod] = Field(default_factory=list, description="Contact information")
    bio: Optional[str] = Field(None, description="Employee bio or description")
    experience_years: Optional[int] = Field(None, description="Years of experience")
    linkedin_url: Optional[HttpUrl] = Field(None, description="LinkedIn profile URL")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Employee identification confidence")
    source_url: Optional[HttpUrl] = Field(None, description="Source page where found")
    
    class Config:
        json_encoders = {
            HttpUrl: str
        }


class CompanyWebsite(BaseModel):
    """Company website analysis results"""
    url: HttpUrl = Field(..., description="Website URL")
    title: Optional[str] = Field(None, description="Website title")
    description: Optional[str] = Field(None, description="Website description")
    about_content: Optional[str] = Field(None, description="About section content")
    contact_page_url: Optional[HttpUrl] = Field(None, description="Contact page URL")
    team_page_url: Optional[HttpUrl] = Field(None, description="Team/About page URL")
    careers_page_url: Optional[HttpUrl] = Field(None, description="Careers page URL")
    employee_count_estimate: Optional[int] = Field(None, description="Estimated employee count")
    technologies: List[str] = Field(default_factory=list, description="Technologies mentioned")
    keywords: List[str] = Field(default_factory=list, description="Key business terms")
    
    class Config:
        json_encoders = {
            HttpUrl: str
        }


class CompanyInfo(BaseModel):
    """Company information and analysis"""
    name: str = Field(..., description="Company name")
    domain: Optional[str] = Field(None, description="Primary domain")
    industry: Optional[str] = Field(None, description="Industry classification")
    size_category: Optional[CompanySize] = Field(None, description="Company size category")
    founded_year: Optional[int] = Field(None, description="Year founded")
    headquarters: Optional[str] = Field(None, description="Headquarters location")
    description: Optional[str] = Field(None, description="Company description")
    website: Optional[CompanyWebsite] = Field(None, description="Website analysis")
    employees: List[EmployeeProfile] = Field(default_factory=list, description="Discovered employees")
    social_profiles: Dict[str, HttpUrl] = Field(default_factory=dict, description="Social media profiles")
    contact_methods: List[ContactMethod] = Field(default_factory=list, description="Company contact information")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Overall analysis confidence")
    
    class Config:
        json_encoders = {
            HttpUrl: str
        }


class CompanyAnalysisRequest(BaseModel):
    """Request model for company analysis"""
    company_name: Optional[str] = Field(None, description="Company name to analyze")
    company_url: Optional[HttpUrl] = Field(None, description="Company website URL")
    linkedin_url: Optional[HttpUrl] = Field(None, description="Company LinkedIn profile URL")
    additional_context: Optional[str] = Field(None, description="Additional context or keywords")
    deep_analysis: bool = Field(default=True, description="Whether to perform deep website analysis")
    extract_employees: bool = Field(default=True, description="Whether to extract employee information")
    max_employees: int = Field(default=50, ge=1, le=200, description="Maximum employees to extract")
    
    @validator('company_name', 'company_url', 'linkedin_url')
    def at_least_one_input(cls, v, values):
        """Ensure at least one input is provided"""
        if not any([v, values.get('company_name'), values.get('company_url'), values.get('linkedin_url')]):
            raise ValueError('At least one of company_name, company_url, or linkedin_url must be provided')
        return v
    
    class Config:
        json_encoders = {
            HttpUrl: str
        }


class WebsiteDiscovery(BaseModel):
    """Website discovery results from SERP"""
    primary_website: Optional[HttpUrl] = Field(None, description="Primary company website")
    alternative_websites: List[HttpUrl] = Field(default_factory=list, description="Alternative websites found")
    social_profiles: Dict[str, HttpUrl] = Field(default_factory=dict, description="Social media profiles found")
    confidence: float = Field(ge=0.0, le=1.0, description="Discovery confidence")
    search_queries_used: List[str] = Field(default_factory=list, description="SERP queries used")
    
    class Config:
        json_encoders = {
            HttpUrl: str
        }


class EmployeeDiscoveryStats(BaseModel):
    """Statistics for employee discovery process"""
    total_pages_crawled: int = Field(default=0, description="Total pages analyzed")
    employees_found: int = Field(default=0, description="Total employees identified")
    high_confidence_employees: int = Field(default=0, description="High confidence employees (>0.8)")
    roles_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution by role")
    departments_found: List[str] = Field(default_factory=list, description="Departments identified")
    extraction_time_seconds: float = Field(default=0.0, description="Time taken for extraction")


class CompanyAnalysisResponse(BaseModel):
    """Response model for company analysis"""
    success: bool = Field(..., description="Whether analysis was successful")
    company: Optional[CompanyInfo] = Field(None, description="Company information and analysis")
    website_discovery: Optional[WebsiteDiscovery] = Field(None, description="Website discovery results")
    employee_stats: Optional[EmployeeDiscoveryStats] = Field(None, description="Employee discovery statistics")
    error_message: Optional[str] = Field(None, description="Error message if analysis failed")
    processing_time_seconds: float = Field(default=0.0, description="Total processing time")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str
        }


class CompanySearchRequest(BaseModel):
    """Request model for company search queries"""
    company_name: str = Field(..., description="Company name to search for")
    industry: Optional[str] = Field(None, description="Industry context")
    location: Optional[str] = Field(None, description="Geographic location")
    additional_keywords: List[str] = Field(default_factory=list, description="Additional search keywords")
    search_type: str = Field(default="comprehensive", description="Type of search (website, employees, contact)")


class CompanySearchResponse(BaseModel):
    """Response model for company search queries"""
    search_queries: List[str] = Field(..., description="Generated search queries")
    query_explanations: Dict[str, str] = Field(default_factory=dict, description="Explanation for each query")
    estimated_results: int = Field(default=0, description="Estimated number of results")
    search_strategy: str = Field(..., description="Search strategy used")