#!/usr/bin/env python3
"""
Complete Company Intelligence Workflow Example

This comprehensive example demonstrates a complete company intelligence workflow
using the Company Information Extraction API, including:

1. Market research and competitive analysis
2. Lead qualification and enrichment
3. Investment research and due diligence
4. Performance monitoring and optimization
5. Data export and CRM integration

Usage:
    python examples/example_complete_workflow.py
"""

import asyncio
import sys
import logging
import json
import csv
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
class CompanyIntelligence:
    """Comprehensive company intelligence data."""
    basic_info: Dict[str, Any]
    financial_metrics: Dict[str, Any]
    market_position: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    opportunity_score: float
    confidence_level: str
    extraction_timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return asdict(self)


class CompanyIntelligenceEngine:
    """Complete company intelligence analysis engine."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
    
    async def extract_company_data(
        self, 
        company_name: str, 
        extraction_mode: str = "comprehensive"
    ) -> Optional[Dict[str, Any]]:
        """Extract comprehensive company data."""
        async with httpx.AsyncClient(base_url=self.base_url, timeout=300) as client:
            try:
                response = await client.post(
                    "/api/v1/company/extract",
                    json={
                        "company_name": company_name,
                        "extraction_mode": extraction_mode,
                        "include_financial_data": True,
                        "include_contact_info": True
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success", False):
                        return result.get("data", {})
                
                logger.error(f"Failed to extract {company_name}: {response.status_code}")
                return None
                
            except Exception as e:
                logger.error(f"Error extracting {company_name}: {e}")
                return None
    
    async def batch_extract_companies(
        self, 
        company_names: List[str], 
        extraction_mode: str = "comprehensive"
    ) -> List[Dict[str, Any]]:
        """Extract data for multiple companies using batch processing."""
        async with httpx.AsyncClient(base_url=self.base_url, timeout=600) as client:
            try:
                # Submit batch
                logger.info(f"Submitting batch extraction for {len(company_names)} companies")
                response = await client.post(
                    "/api/v1/company/batch/submit",
                    json={
                        "company_names": company_names,
                        "extraction_mode": extraction_mode,
                        "priority": "high"
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Batch submission failed: {response.status_code}")
                    return []
                
                batch_id = response.json().get("batch_id")
                if not batch_id:
                    logger.error("No batch ID received")
                    return []
                
                logger.info(f"Batch submitted: {batch_id}")
                
                # Poll for completion
                while True:
                    status_response = await client.get(f"/api/v1/company/batch/{batch_id}/status")
                    
                    if status_response.status_code != 200:
                        logger.error(f"Status check failed: {status_response.status_code}")
                        return []
                    
                    status_data = status_response.json()
                    status = status_data.get("status", "unknown")
                    progress = status_data.get("progress", {})
                    
                    logger.info(f"Batch status: {status} - {progress.get('completed', 0)}/{progress.get('total', 0)} completed")
                    
                    if status == "completed":
                        break
                    elif status in ["failed", "cancelled"]:
                        logger.error(f"Batch processing failed: {status}")
                        return []
                    
                    await asyncio.sleep(15)  # Poll every 15 seconds
                
                # Get results
                results_response = await client.get(f"/api/v1/company/batch/{batch_id}/results")
                
                if results_response.status_code != 200:
                    logger.error(f"Results retrieval failed: {results_response.status_code}")
                    return []
                
                results_data = results_response.json()
                extracted_data = results_data.get("results", [])
                
                # Filter successful extractions
                successful_data = []
                for item in extracted_data:
                    if item.get("success", False):
                        successful_data.append(item.get("data", {}))
                
                logger.info(f"Successfully extracted data for {len(successful_data)} companies")
                return successful_data
                
            except Exception as e:
                logger.error(f"Batch extraction error: {e}")
                return []
    
    def analyze_company_intelligence(self, company_data: Dict[str, Any]) -> CompanyIntelligence:
        """Analyze company data and generate intelligence insights."""
        # Extract basic information
        basic_info = {
            "company_name": company_data.get("company_name", ""),
            "industry": company_data.get("industry", ""),
            "website": company_data.get("contact_info", {}).get("website", ""),
            "headquarters": company_data.get("contact_info", {}).get("headquarters", {}),
            "employee_count": company_data.get("employee_count", ""),
            "founded_year": company_data.get("founded_year", "")
        }
        
        # Extract financial metrics
        financial_data = company_data.get("financial_data", {})
        financial_metrics = {
            "revenue": financial_data.get("revenue", ""),
            "valuation": financial_data.get("valuation", ""),
            "funding_raised": financial_data.get("funding_raised", ""),
            "profitability_status": financial_data.get("profitability_status", ""),
            "growth_rate": financial_data.get("growth_rate", "")
        }
        
        # Assess market position
        market_position = {
            "market_cap_category": self._categorize_market_cap(financial_data.get("valuation", "")),
            "industry_leader_status": self._assess_leadership_position(company_data),
            "competitive_advantages": company_data.get("competitive_advantages", []),
            "market_share": financial_data.get("market_share", "")
        }
        
        # Risk assessment
        risk_assessment = {
            "financial_risk": self._assess_financial_risk(financial_data),
            "market_risk": self._assess_market_risk(company_data),
            "operational_risk": self._assess_operational_risk(company_data),
            "overall_risk_score": 0.0  # Will be calculated
        }
        
        # Calculate overall risk score
        risk_scores = [
            risk_assessment["financial_risk"],
            risk_assessment["market_risk"], 
            risk_assessment["operational_risk"]
        ]
        risk_assessment["overall_risk_score"] = sum(risk_scores) / len(risk_scores)
        
        # Calculate opportunity score
        opportunity_score = self._calculate_opportunity_score(
            financial_metrics, market_position, risk_assessment
        )
        
        # Determine confidence level
        confidence_score = company_data.get("confidence_score", 0.0)
        confidence_level = self._determine_confidence_level(confidence_score)
        
        return CompanyIntelligence(
            basic_info=basic_info,
            financial_metrics=financial_metrics,
            market_position=market_position,
            risk_assessment=risk_assessment,
            opportunity_score=opportunity_score,
            confidence_level=confidence_level,
            extraction_timestamp=datetime.now().isoformat()
        )
    
    def _categorize_market_cap(self, valuation_str: str) -> str:
        """Categorize company by market cap/valuation."""
        if not valuation_str:
            return "Unknown"
        
        val_lower = valuation_str.lower()
        if "trillion" in val_lower or "1000" in val_lower:
            return "Mega Cap (>$1T)"
        elif "billion" in val_lower:
            # Extract numeric value
            try:
                num = float(''.join(filter(str.isdigit, val_lower.split('billion')[0])))
                if num >= 200:
                    return "Large Cap ($200B+)"
                elif num >= 10:
                    return "Mid Cap ($10B-$200B)"
                else:
                    return "Small Cap ($2B-$10B)"
            except:
                return "Unknown"
        elif "million" in val_lower:
            return "Micro Cap (<$2B)"
        else:
            return "Unknown"
    
    def _assess_leadership_position(self, company_data: Dict[str, Any]) -> str:
        """Assess market leadership position."""
        industry = company_data.get("industry", "").lower()
        company_name = company_data.get("company_name", "").lower()
        
        # Simple heuristic based on well-known leaders
        tech_leaders = ["microsoft", "apple", "google", "amazon", "meta", "tesla", "nvidia"]
        finance_leaders = ["jpmorgan", "goldman sachs", "morgan stanley", "blackrock"]
        
        if any(leader in company_name for leader in tech_leaders + finance_leaders):
            return "Market Leader"
        elif "technology" in industry or "software" in industry:
            return "Technology Player"
        else:
            return "Industry Participant"
    
    def _assess_financial_risk(self, financial_data: Dict[str, Any]) -> float:
        """Assess financial risk (0-1 scale, lower is better)."""
        risk_score = 0.5  # Default moderate risk
        
        # Revenue assessment
        revenue = financial_data.get("revenue", "").lower()
        if "billion" in revenue:
            risk_score -= 0.2
        elif not revenue or "unknown" in revenue:
            risk_score += 0.2
        
        # Profitability assessment
        profitability = financial_data.get("profitability_status", "").lower()
        if "profitable" in profitability:
            risk_score -= 0.1
        elif "unprofitable" in profitability:
            risk_score += 0.1
        
        # Growth assessment
        growth = financial_data.get("growth_rate", "").lower()
        if "high" in growth or "rapid" in growth:
            risk_score -= 0.1
        elif "declining" in growth or "negative" in growth:
            risk_score += 0.2
        
        return max(0.0, min(1.0, risk_score))
    
    def _assess_market_risk(self, company_data: Dict[str, Any]) -> float:
        """Assess market risk (0-1 scale, lower is better)."""
        risk_score = 0.5
        
        industry = company_data.get("industry", "").lower()
        
        # Industry-specific risk adjustments
        low_risk_industries = ["healthcare", "utilities", "consumer staples"]
        high_risk_industries = ["cryptocurrency", "biotech", "energy"]
        
        if any(ind in industry for ind in low_risk_industries):
            risk_score -= 0.2
        elif any(ind in industry for ind in high_risk_industries):
            risk_score += 0.2
        
        return max(0.0, min(1.0, risk_score))
    
    def _assess_operational_risk(self, company_data: Dict[str, Any]) -> float:
        """Assess operational risk (0-1 scale, lower is better)."""
        risk_score = 0.5
        
        # Employee count as stability indicator
        emp_count = company_data.get("employee_count", "")
        if emp_count:
            try:
                count = int(emp_count.replace(",", "").replace("+", ""))
                if count > 10000:
                    risk_score -= 0.1
                elif count < 100:
                    risk_score += 0.1
            except:
                pass
        
        # Founded year as maturity indicator
        founded = company_data.get("founded_year", "")
        if founded:
            try:
                year = int(founded)
                age = 2024 - year
                if age > 20:
                    risk_score -= 0.1
                elif age < 5:
                    risk_score += 0.1
            except:
                pass
        
        return max(0.0, min(1.0, risk_score))
    
    def _calculate_opportunity_score(
        self, 
        financial_metrics: Dict[str, Any],
        market_position: Dict[str, Any], 
        risk_assessment: Dict[str, Any]
    ) -> float:
        """Calculate overall opportunity score (0-100)."""
        score = 50.0  # Base score
        
        # Financial metrics contribution (0-30 points)
        revenue = financial_metrics.get("revenue", "").lower()
        if "billion" in revenue:
            score += 15
        elif "million" in revenue:
            score += 10
        
        valuation = financial_metrics.get("valuation", "").lower()
        if "billion" in valuation:
            score += 15
        elif "million" in valuation:
            score += 8
        
        # Market position contribution (0-30 points)
        if market_position.get("market_cap_category") == "Large Cap ($200B+)":
            score += 20
        elif "Mid Cap" in market_position.get("market_cap_category", ""):
            score += 15
        
        if market_position.get("industry_leader_status") == "Market Leader":
            score += 10
        
        # Risk adjustment (-20 to +20 points)
        overall_risk = risk_assessment.get("overall_risk_score", 0.5)
        risk_adjustment = (0.5 - overall_risk) * 40  # Convert to -20 to +20 scale
        score += risk_adjustment
        
        return max(0.0, min(100.0, score))
    
    def _determine_confidence_level(self, confidence_score: float) -> str:
        """Determine confidence level from score."""
        if confidence_score >= 0.9:
            return "Very High"
        elif confidence_score >= 0.8:
            return "High"
        elif confidence_score >= 0.6:
            return "Medium"
        elif confidence_score >= 0.4:
            return "Low"
        else:
            return "Very Low"


class WorkflowExecutor:
    """Execute complete company intelligence workflows."""
    
    def __init__(self):
        self.engine = CompanyIntelligenceEngine()
    
    async def market_research_workflow(self, industry_companies: List[str]) -> List[CompanyIntelligence]:
        """Execute market research workflow."""
        logger.info(f"Starting market research for {len(industry_companies)} companies")
        
        # Extract company data
        company_data_list = await self.engine.batch_extract_companies(
            company_names=industry_companies,
            extraction_mode="comprehensive"
        )
        
        # Analyze each company
        intelligence_reports = []
        for company_data in company_data_list:
            intelligence = self.engine.analyze_company_intelligence(company_data)
            intelligence_reports.append(intelligence)
        
        # Sort by opportunity score
        intelligence_reports.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        logger.info(f"Market research completed for {len(intelligence_reports)} companies")
        return intelligence_reports
    
    async def lead_qualification_workflow(self, prospect_companies: List[str]) -> List[CompanyIntelligence]:
        """Execute lead qualification workflow."""
        logger.info(f"Starting lead qualification for {len(prospect_companies)} prospects")
        
        # Extract with contact focus
        company_data_list = await self.engine.batch_extract_companies(
            company_names=prospect_companies,
            extraction_mode="contact_focused"
        )
        
        # Analyze and qualify leads
        qualified_leads = []
        for company_data in company_data_list:
            intelligence = self.engine.analyze_company_intelligence(company_data)
            
            # Only include high-potential leads
            if intelligence.opportunity_score >= 60 and intelligence.confidence_level in ["High", "Very High"]:
                qualified_leads.append(intelligence)
        
        logger.info(f"Qualified {len(qualified_leads)} high-potential leads")
        return qualified_leads
    
    async def investment_research_workflow(self, investment_targets: List[str]) -> List[CompanyIntelligence]:
        """Execute investment research workflow."""
        logger.info(f"Starting investment research for {len(investment_targets)} targets")
        
        # Extract with financial focus
        company_data_list = await self.engine.batch_extract_companies(
            company_names=investment_targets,
            extraction_mode="financial_focused"
        )
        
        # Analyze investment potential
        investment_reports = []
        for company_data in company_data_list:
            intelligence = self.engine.analyze_company_intelligence(company_data)
            investment_reports.append(intelligence)
        
        # Sort by opportunity score and filter by confidence
        investment_reports = [
            report for report in investment_reports 
            if report.confidence_level in ["High", "Very High"]
        ]
        investment_reports.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        logger.info(f"Investment research completed for {len(investment_reports)} targets")
        return investment_reports
    
    def export_intelligence_reports(
        self, 
        reports: List[CompanyIntelligence], 
        filename_base: str
    ):
        """Export intelligence reports to multiple formats."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export to JSON
        json_filename = f"{filename_base}_{timestamp}.json"
        with open(json_filename, 'w') as f:
            json.dump([report.to_dict() for report in reports], f, indent=2)
        logger.info(f"Exported JSON report: {json_filename}")
        
        # Export to CSV
        csv_filename = f"{filename_base}_{timestamp}.csv"
        if reports:
            fieldnames = []
            for report in reports:
                report_dict = report.to_dict()
                for key, value in report_dict.items():
                    if isinstance(value, dict):
                        for subkey in value.keys():
                            fieldnames.append(f"{key}.{subkey}")
                    else:
                        fieldnames.append(key)
                break  # Just need fieldnames from first report
            
            fieldnames = list(set(fieldnames))  # Remove duplicates
            
            with open(csv_filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for report in reports:
                    row = {}
                    report_dict = report.to_dict()
                    for key, value in report_dict.items():
                        if isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                row[f"{key}.{subkey}"] = subvalue
                        else:
                            row[key] = value
                    writer.writerow(row)
            
            logger.info(f"Exported CSV report: {csv_filename}")
    
    def generate_executive_summary(self, reports: List[CompanyIntelligence]) -> str:
        """Generate executive summary of intelligence reports."""
        if not reports:
            return "No companies analyzed."
        
        # Calculate summary statistics
        avg_opportunity_score = sum(r.opportunity_score for r in reports) / len(reports)
        high_opportunity_count = len([r for r in reports if r.opportunity_score >= 70])
        high_confidence_count = len([r for r in reports if r.confidence_level in ["High", "Very High"]])
        
        # Top performing companies
        top_companies = sorted(reports, key=lambda x: x.opportunity_score, reverse=True)[:5]
        
        summary = f"""
EXECUTIVE SUMMARY - Company Intelligence Analysis
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

OVERVIEW:
- Total Companies Analyzed: {len(reports)}
- Average Opportunity Score: {avg_opportunity_score:.1f}/100
- High Opportunity Companies (70+ score): {high_opportunity_count}
- High Confidence Analyses: {high_confidence_count}

TOP PERFORMING COMPANIES:
"""
        
        for i, company in enumerate(top_companies, 1):
            name = company.basic_info.get("company_name", "Unknown")
            industry = company.basic_info.get("industry", "Unknown")
            score = company.opportunity_score
            confidence = company.confidence_level
            
            summary += f"{i}. {name} ({industry})\n"
            summary += f"   Opportunity Score: {score:.1f}/100\n"
            summary += f"   Confidence: {confidence}\n\n"
        
        return summary


async def example_market_research():
    """Example: Complete market research workflow."""
    logger.info("=" * 60)
    logger.info("MARKET RESEARCH WORKFLOW EXAMPLE")
    logger.info("=" * 60)
    
    # Define market segment companies
    fintech_companies = [
        "Stripe", "Square", "PayPal", "Klarna", "Affirm",
        "Robinhood", "Coinbase", "Plaid"
    ]
    
    executor = WorkflowExecutor()
    
    # Execute market research
    intelligence_reports = await executor.market_research_workflow(fintech_companies)
    
    # Generate and display summary
    summary = executor.generate_executive_summary(intelligence_reports)
    logger.info(summary)
    
    # Export reports
    executor.export_intelligence_reports(intelligence_reports, "market_research_fintech")
    
    return intelligence_reports


async def example_lead_qualification():
    """Example: Lead qualification workflow."""
    logger.info("=" * 60)
    logger.info("LEAD QUALIFICATION WORKFLOW EXAMPLE")
    logger.info("=" * 60)
    
    # Define prospect companies
    prospect_companies = [
        "Salesforce", "HubSpot", "Monday.com", "Asana",
        "Notion", "Airtable", "Figma", "Canva"
    ]
    
    executor = WorkflowExecutor()
    
    # Execute lead qualification
    qualified_leads = await executor.lead_qualification_workflow(prospect_companies)
    
    # Generate and display summary
    summary = executor.generate_executive_summary(qualified_leads)
    logger.info(summary)
    
    # Export qualified leads
    executor.export_intelligence_reports(qualified_leads, "qualified_leads")
    
    return qualified_leads


async def example_investment_research():
    """Example: Investment research workflow."""
    logger.info("=" * 60)
    logger.info("INVESTMENT RESEARCH WORKFLOW EXAMPLE")
    logger.info("=" * 60)
    
    # Define investment targets
    investment_targets = [
        "SpaceX", "Databricks", "Anthropic", "OpenAI",
        "Discord", "Epic Games", "Figma"
    ]
    
    executor = WorkflowExecutor()
    
    # Execute investment research
    investment_reports = await executor.investment_research_workflow(investment_targets)
    
    # Generate and display summary
    summary = executor.generate_executive_summary(investment_reports)
    logger.info(summary)
    
    # Export investment analysis
    executor.export_intelligence_reports(investment_reports, "investment_research")
    
    return investment_reports


async def main():
    """Execute complete workflow examples."""
    logger.info("Starting Complete Company Intelligence Workflow Examples")
    logger.info("This demonstrates end-to-end business intelligence workflows")
    
    try:
        # Run all workflow examples
        market_research_results = await example_market_research()
        await asyncio.sleep(2)
        
        lead_qualification_results = await example_lead_qualification()
        await asyncio.sleep(2)
        
        investment_research_results = await example_investment_research()
        
        # Combined summary
        logger.info("=" * 60)
        logger.info("OVERALL WORKFLOW SUMMARY")
        logger.info("=" * 60)
        
        total_companies = (
            len(market_research_results) + 
            len(lead_qualification_results) + 
            len(investment_research_results)
        )
        
        logger.info(f"Total Companies Analyzed: {total_companies}")
        logger.info(f"Market Research Companies: {len(market_research_results)}")
        logger.info(f"Qualified Leads: {len(lead_qualification_results)}")
        logger.info(f"Investment Targets: {len(investment_research_results)}")
        
        logger.info("All workflow examples completed successfully!")
        logger.info("Check the exported files for detailed analysis results.")
        
    except KeyboardInterrupt:
        logger.info("Workflow interrupted by user")
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())