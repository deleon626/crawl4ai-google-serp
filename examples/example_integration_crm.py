#!/usr/bin/env python3
"""
CRM Integration Examples

This example demonstrates how to integrate the Company Information Extraction API
with popular CRM systems including Salesforce, HubSpot, and custom CRM solutions.

Usage:
    python examples/example_integration_crm.py
"""

import asyncio
import sys
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8000"


@dataclass
class CompanyRecord:
    """Standardized company record for CRM integration."""
    name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    headquarters_address: Optional[str] = None
    headquarters_city: Optional[str] = None
    headquarters_country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    employee_count: Optional[str] = None
    revenue: Optional[str] = None
    valuation: Optional[str] = None
    founded_year: Optional[str] = None
    ceo_name: Optional[str] = None
    key_products: Optional[List[str]] = None
    confidence_score: Optional[float] = None
    extraction_date: str = ""
    
    def __post_init__(self):
        if not self.extraction_date:
            self.extraction_date = datetime.now().isoformat()


class CompanyExtractorClient:
    """Client for Company Information Extraction API."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
    
    async def extract_company(
        self, 
        company_name: str, 
        extraction_mode: str = "standard"
    ) -> Optional[CompanyRecord]:
        """Extract company information and return standardized record."""
        async with httpx.AsyncClient(base_url=self.base_url, timeout=300) as client:
            try:
                response = await client.post(
                    "/api/v1/company/extract",
                    json={
                        "company_name": company_name,
                        "extraction_mode": extraction_mode
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                if not data.get("success", False):
                    logger.error(f"Extraction failed for {company_name}: {data.get('error')}")
                    return None
                
                return self._convert_to_record(data.get("data", {}))
                
            except Exception as e:
                logger.error(f"Error extracting company {company_name}: {e}")
                return None
    
    async def extract_companies_batch(
        self, 
        company_names: List[str], 
        extraction_mode: str = "standard"
    ) -> List[CompanyRecord]:
        """Extract multiple companies using batch processing."""
        async with httpx.AsyncClient(base_url=self.base_url, timeout=600) as client:
            try:
                # Submit batch
                response = await client.post(
                    "/api/v1/company/batch/submit",
                    json={
                        "company_names": company_names,
                        "extraction_mode": extraction_mode,
                        "priority": "high"
                    }
                )
                response.raise_for_status()
                
                batch_id = response.json().get("batch_id")
                if not batch_id:
                    logger.error("No batch_id received")
                    return []
                
                # Wait for completion
                while True:
                    status_response = await client.get(f"/api/v1/company/batch/{batch_id}/status")
                    status_response.raise_for_status()
                    
                    status_data = status_response.json()
                    status = status_data.get("status", "unknown")
                    
                    if status == "completed":
                        break
                    elif status in ["failed", "cancelled"]:
                        logger.error(f"Batch processing failed with status: {status}")
                        return []
                    
                    await asyncio.sleep(10)
                
                # Get results
                results_response = await client.get(f"/api/v1/company/batch/{batch_id}/results")
                results_response.raise_for_status()
                
                results_data = results_response.json()
                extracted_data = results_data.get("results", [])
                
                # Convert to CompanyRecord objects
                records = []
                for item in extracted_data:
                    if item.get("success", False):
                        record = self._convert_to_record(item.get("data", {}))
                        if record:
                            records.append(record)
                
                return records
                
            except Exception as e:
                logger.error(f"Error in batch extraction: {e}")
                return []
    
    def _convert_to_record(self, data: Dict[str, Any]) -> Optional[CompanyRecord]:
        """Convert API response data to CompanyRecord."""
        try:
            # Extract contact information
            contact_info = data.get("contact_info", {})
            headquarters = contact_info.get("headquarters", {})
            social_media = contact_info.get("social_media", {})
            
            # Extract financial data
            financial_data = data.get("financial_data", {})
            
            # Extract leadership information
            leadership = data.get("leadership", {})
            key_personnel = leadership.get("key_personnel", [])
            ceo_name = None
            if key_personnel:
                ceo = next((person for person in key_personnel if "CEO" in person.get("title", "")), None)
                if ceo:
                    ceo_name = ceo.get("name")
            
            return CompanyRecord(
                name=data.get("company_name", ""),
                website=contact_info.get("website"),
                industry=data.get("industry"),
                description=data.get("description"),
                headquarters_address=headquarters.get("address"),
                headquarters_city=headquarters.get("city"),
                headquarters_country=headquarters.get("country"),
                phone=contact_info.get("phone"),
                email=contact_info.get("email"),
                linkedin_url=social_media.get("linkedin"),
                twitter_url=social_media.get("twitter"),
                employee_count=data.get("employee_count"),
                revenue=financial_data.get("revenue"),
                valuation=financial_data.get("valuation"),
                founded_year=data.get("founded_year"),
                ceo_name=ceo_name,
                key_products=data.get("products_services", []),
                confidence_score=data.get("confidence_score")
            )
            
        except Exception as e:
            logger.error(f"Error converting data to record: {e}")
            return None


class SalesforceCRMIntegration:
    """Integration with Salesforce CRM."""
    
    def __init__(self, instance_url: str, access_token: str):
        self.instance_url = instance_url.rstrip('/')
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def create_account(self, company_record: CompanyRecord) -> Optional[str]:
        """Create a new account in Salesforce."""
        account_data = {
            "Name": company_record.name,
            "Website": company_record.website,
            "Industry": company_record.industry,
            "Description": company_record.description,
            "Phone": company_record.phone,
            "BillingStreet": company_record.headquarters_address,
            "BillingCity": company_record.headquarters_city,
            "BillingCountry": company_record.headquarters_country,
            "NumberOfEmployees": self._parse_employee_count(company_record.employee_count),
            "AnnualRevenue": self._parse_revenue(company_record.revenue),
            "YearStarted": company_record.founded_year,
            # Custom fields (adjust based on your Salesforce setup)
            "LinkedIn_URL__c": company_record.linkedin_url,
            "Twitter_URL__c": company_record.twitter_url,
            "Valuation__c": company_record.valuation,
            "CEO_Name__c": company_record.ceo_name,
            "Extraction_Date__c": company_record.extraction_date,
            "Confidence_Score__c": company_record.confidence_score
        }
        
        # Remove None values
        account_data = {k: v for k, v in account_data.items() if v is not None}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.instance_url}/services/data/v58.0/sobjects/Account/",
                    json=account_data,
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                account_id = result.get("id")
                logger.info(f"Created Salesforce account for {company_record.name}: {account_id}")
                return account_id
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error creating Salesforce account: {e.response.status_code} - {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Error creating Salesforce account: {e}")
                return None
    
    async def update_account(self, account_id: str, company_record: CompanyRecord) -> bool:
        """Update existing account in Salesforce."""
        account_data = {
            "Website": company_record.website,
            "Industry": company_record.industry,
            "Description": company_record.description,
            "Phone": company_record.phone,
            "BillingStreet": company_record.headquarters_address,
            "BillingCity": company_record.headquarters_city,
            "BillingCountry": company_record.headquarters_country,
            "LinkedIn_URL__c": company_record.linkedin_url,
            "Twitter_URL__c": company_record.twitter_url,
            "Extraction_Date__c": company_record.extraction_date,
            "Confidence_Score__c": company_record.confidence_score
        }
        
        # Remove None values
        account_data = {k: v for k, v in account_data.items() if v is not None}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.patch(
                    f"{self.instance_url}/services/data/v58.0/sobjects/Account/{account_id}",
                    json=account_data,
                    headers=self.headers
                )
                response.raise_for_status()
                
                logger.info(f"Updated Salesforce account: {account_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error updating Salesforce account: {e}")
                return False
    
    def _parse_employee_count(self, employee_count_str: Optional[str]) -> Optional[int]:
        """Parse employee count string to integer."""
        if not employee_count_str:
            return None
        
        # Handle ranges like "100-500"
        if "-" in employee_count_str:
            try:
                lower = int(employee_count_str.split("-")[0].replace(",", ""))
                return lower
            except ValueError:
                pass
        
        # Handle "1000+" format
        if "+" in employee_count_str:
            try:
                return int(employee_count_str.replace("+", "").replace(",", ""))
            except ValueError:
                pass
        
        # Try direct conversion
        try:
            return int(employee_count_str.replace(",", ""))
        except (ValueError, AttributeError):
            return None
    
    def _parse_revenue(self, revenue_str: Optional[str]) -> Optional[float]:
        """Parse revenue string to float."""
        if not revenue_str:
            return None
        
        try:
            # Remove currency symbols and "billion", "million" etc.
            clean_str = revenue_str.replace("$", "").replace(",", "").lower()
            
            multiplier = 1
            if "billion" in clean_str or "b" in clean_str:
                multiplier = 1_000_000_000
                clean_str = clean_str.replace("billion", "").replace("b", "").strip()
            elif "million" in clean_str or "m" in clean_str:
                multiplier = 1_000_000
                clean_str = clean_str.replace("million", "").replace("m", "").strip()
            
            return float(clean_str) * multiplier
            
        except (ValueError, AttributeError):
            return None


class HubSpotCRMIntegration:
    """Integration with HubSpot CRM."""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def create_company(self, company_record: CompanyRecord) -> Optional[str]:
        """Create a new company in HubSpot."""
        properties = {
            "name": company_record.name,
            "domain": self._extract_domain(company_record.website),
            "industry": company_record.industry,
            "description": company_record.description,
            "phone": company_record.phone,
            "address": company_record.headquarters_address,
            "city": company_record.headquarters_city,
            "country": company_record.headquarters_country,
            "numberofemployees": company_record.employee_count,
            "annualrevenue": company_record.revenue,
            "founded_year": company_record.founded_year,
            "linkedin_company_page": company_record.linkedin_url,
            "twitterhandle": company_record.twitter_url
        }
        
        # Remove None values
        properties = {k: v for k, v in properties.items() if v is not None}
        
        company_data = {"properties": properties}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/crm/v3/objects/companies",
                    json=company_data,
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                company_id = result.get("id")
                logger.info(f"Created HubSpot company for {company_record.name}: {company_id}")
                return company_id
                
            except Exception as e:
                logger.error(f"Error creating HubSpot company: {e}")
                return None
    
    def _extract_domain(self, website: Optional[str]) -> Optional[str]:
        """Extract domain from website URL."""
        if not website:
            return None
        
        domain = website.replace("https://", "").replace("http://", "").replace("www.", "")
        if "/" in domain:
            domain = domain.split("/")[0]
        
        return domain


class GenericCRMExporter:
    """Generic CRM data exporter for CSV/JSON formats."""
    
    @staticmethod
    def export_to_csv(records: List[CompanyRecord], filename: str):
        """Export company records to CSV file."""
        import csv
        
        if not records:
            logger.warning("No records to export")
            return
        
        fieldnames = [field.name for field in records[0].__dataclass_fields__.values()]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for record in records:
                row = asdict(record)
                # Convert lists to comma-separated strings
                for key, value in row.items():
                    if isinstance(value, list):
                        row[key] = ", ".join(map(str, value)) if value else ""
                writer.writerow(row)
        
        logger.info(f"Exported {len(records)} records to {filename}")
    
    @staticmethod
    def export_to_json(records: List[CompanyRecord], filename: str):
        """Export company records to JSON file."""
        if not records:
            logger.warning("No records to export")
            return
        
        data = [asdict(record) for record in records]
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(records)} records to {filename}")


async def example_salesforce_integration():
    """Example: Salesforce CRM integration."""
    logger.info("Running Salesforce integration example...")
    
    # Initialize clients
    extractor = CompanyExtractorClient()
    
    # Note: Replace with your actual Salesforce credentials
    # salesforce = SalesforceCRMIntegration(
    #     instance_url="https://your-instance.salesforce.com",
    #     access_token="your_access_token"
    # )
    
    # Companies to extract and add to CRM
    companies = ["OpenAI", "Anthropic", "Hugging Face"]
    
    logger.info(f"Extracting company data for: {companies}")
    
    # Extract company data
    records = await extractor.extract_companies_batch(
        company_names=companies,
        extraction_mode="contact_focused"  # Focus on contact info for CRM
    )
    
    if not records:
        logger.error("No company data extracted")
        return
    
    logger.info(f"Successfully extracted data for {len(records)} companies")
    
    # In a real implementation, you would create Salesforce accounts:
    # for record in records:
    #     account_id = await salesforce.create_account(record)
    #     if account_id:
    #         logger.info(f"Created account for {record.name}")
    
    # For demo purposes, just show the data
    for record in records:
        logger.info(f"""
Company: {record.name}
Website: {record.website}
Industry: {record.industry}
Headquarters: {record.headquarters_city}, {record.headquarters_country}
Employees: {record.employee_count}
CEO: {record.ceo_name}
        """)


async def example_hubspot_integration():
    """Example: HubSpot CRM integration."""
    logger.info("Running HubSpot integration example...")
    
    # Initialize clients
    extractor = CompanyExtractorClient()
    
    # Note: Replace with your actual HubSpot access token
    # hubspot = HubSpotCRMIntegration(access_token="your_access_token")
    
    # Companies for lead qualification
    prospect_companies = ["Stripe", "Square", "PayPal"]
    
    logger.info(f"Extracting prospect data for: {prospect_companies}")
    
    # Extract with financial focus for lead scoring
    records = await extractor.extract_companies_batch(
        company_names=prospect_companies,
        extraction_mode="financial_focused"
    )
    
    if not records:
        logger.error("No prospect data extracted")
        return
    
    logger.info(f"Successfully extracted data for {len(records)} prospects")
    
    # In a real implementation:
    # for record in records:
    #     company_id = await hubspot.create_company(record)
    #     if company_id:
    #         logger.info(f"Created HubSpot company for {record.name}")
    
    # Demo: show prospect data
    for record in records:
        logger.info(f"""
Prospect: {record.name}
Revenue: {record.revenue}
Valuation: {record.valuation}
Industry: {record.industry}
Website: {record.website}
        """)


async def example_csv_export():
    """Example: Export company data to CSV for CRM import."""
    logger.info("Running CSV export example...")
    
    extractor = CompanyExtractorClient()
    
    # Companies for market research
    market_companies = [
        "Netflix", "Disney", "Warner Bros",
        "Spotify", "Apple Music", "YouTube"
    ]
    
    logger.info(f"Extracting market research data for: {market_companies}")
    
    records = await extractor.extract_companies_batch(
        company_names=market_companies,
        extraction_mode="comprehensive"
    )
    
    if not records:
        logger.error("No market research data extracted")
        return
    
    # Export to different formats
    exporter = GenericCRMExporter()
    
    # CSV export
    exporter.export_to_csv(records, "market_research_companies.csv")
    
    # JSON export  
    exporter.export_to_json(records, "market_research_companies.json")
    
    logger.info("Export completed successfully")


async def example_lead_enrichment_workflow():
    """Example: Complete lead enrichment workflow."""
    logger.info("Running lead enrichment workflow...")
    
    extractor = CompanyExtractorClient()
    
    # Simulate leads from your CRM (company names only)
    leads = ["Zoom", "Slack", "Microsoft Teams", "Discord"]
    
    logger.info(f"Enriching leads: {leads}")
    
    # Extract detailed information
    enriched_records = await extractor.extract_companies_batch(
        company_names=leads,
        extraction_mode="comprehensive"
    )
    
    if not enriched_records:
        logger.error("No leads enriched")
        return
    
    # Lead scoring based on extracted data
    scored_leads = []
    for record in enriched_records:
        score = calculate_lead_score(record)
        scored_leads.append((record, score))
    
    # Sort by score (highest first)
    scored_leads.sort(key=lambda x: x[1], reverse=True)
    
    logger.info("Lead Scoring Results:")
    for record, score in scored_leads:
        logger.info(f"""
Company: {record.name}
Lead Score: {score}/100
Revenue: {record.revenue}
Employees: {record.employee_count}
Industry: {record.industry}
Confidence: {record.confidence_score}
        """)
    
    # Export high-priority leads (score > 70)
    high_priority = [record for record, score in scored_leads if score > 70]
    
    if high_priority:
        exporter = GenericCRMExporter()
        exporter.export_to_csv(high_priority, "high_priority_leads.csv")
        logger.info(f"Exported {len(high_priority)} high-priority leads")


def calculate_lead_score(record: CompanyRecord) -> int:
    """Calculate lead score based on company data."""
    score = 0
    
    # Revenue scoring
    if record.revenue:
        revenue_str = record.revenue.lower()
        if "billion" in revenue_str:
            score += 40
        elif "million" in revenue_str:
            score += 25
        else:
            score += 10
    
    # Employee count scoring
    if record.employee_count:
        try:
            emp_count = int(record.employee_count.replace(",", "").replace("+", "").split("-")[0])
            if emp_count >= 10000:
                score += 30
            elif emp_count >= 1000:
                score += 20
            elif emp_count >= 100:
                score += 15
            else:
                score += 10
        except (ValueError, AttributeError):
            pass
    
    # Industry bonus
    high_value_industries = ["technology", "software", "fintech", "healthcare"]
    if record.industry and any(industry in record.industry.lower() for industry in high_value_industries):
        score += 15
    
    # Data quality scoring
    if record.confidence_score and record.confidence_score > 0.8:
        score += 15
    elif record.confidence_score and record.confidence_score > 0.6:
        score += 10
    
    return min(score, 100)  # Cap at 100


async def main():
    """Run CRM integration examples."""
    logger.info("Starting CRM integration examples...")
    
    try:
        await example_salesforce_integration()
        await asyncio.sleep(2)
        
        await example_hubspot_integration()
        await asyncio.sleep(2)
        
        await example_csv_export()
        await asyncio.sleep(2)
        
        await example_lead_enrichment_workflow()
        
        logger.info("All CRM integration examples completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Examples interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())