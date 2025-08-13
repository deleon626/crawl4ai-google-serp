# Integration Examples

This guide provides practical examples for integrating the Company Information Extraction API with popular tools, frameworks, and business systems.

## Business Intelligence Tools

### Power BI Integration

Connect the API to Microsoft Power BI for dynamic company data visualization:

```python
# powerbi_connector.py
import pandas as pd
import httpx
import asyncio
from typing import List, Dict, Any

class PowerBICompanyConnector:
    def __init__(self, api_base_url: str, api_key: str = None):
        self.api_base_url = api_base_url
        self.api_key = api_key
    
    async def get_companies_data(self, company_list: List[str]) -> pd.DataFrame:
        """Fetch company data and return as pandas DataFrame for Power BI."""
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        async with httpx.AsyncClient(headers=headers, timeout=300) as client:
            # Submit batch request
            batch_response = await client.post(
                f"{self.api_base_url}/api/v1/company/batch/submit",
                json={
                    "company_names": company_list,
                    "extraction_mode": "standard",
                    "export_format": "json"
                }
            )
            
            batch_id = batch_response.json()["data"]["batch_id"]
            
            # Wait for completion
            while True:
                status_response = await client.get(
                    f"{self.api_base_url}/api/v1/company/batch/{batch_id}/status"
                )
                status = status_response.json()["data"]["status"]
                
                if status == "completed":
                    break
                elif status == "failed":
                    raise Exception("Batch processing failed")
                
                await asyncio.sleep(10)
            
            # Get results
            results_response = await client.get(
                f"{self.api_base_url}/api/v1/company/batch/{batch_id}/results"
            )
            
            results = results_response.json()["data"]["results"]
            
            # Convert to DataFrame
            return self._create_powerbi_dataframe(results)
    
    def _create_powerbi_dataframe(self, results: List[Dict]) -> pd.DataFrame:
        """Convert API results to Power BI compatible DataFrame."""
        
        rows = []
        for result in results:
            if result["extraction_status"] == "success":
                data = result["data"]
                row = {
                    "Company Name": data.get("company_name"),
                    "Domain": data.get("domain"),
                    "Industry": data.get("industry"),
                    "Description": data.get("description", "")[:500],  # Truncate for Power BI
                    "Employee Count": self._clean_employee_count(data.get("employee_count")),
                    "Founded Year": data.get("founded_year"),
                    "Company Type": data.get("company_type"),
                    "Website": data.get("contact_info", {}).get("website"),
                    "Email": data.get("contact_info", {}).get("email"),
                    "Phone": data.get("contact_info", {}).get("phone"),
                    "City": data.get("headquarters", {}).get("city"),
                    "State": data.get("headquarters", {}).get("state"),
                    "Country": data.get("headquarters", {}).get("country"),
                    "Revenue": self._clean_financial_value(data.get("financial_data", {}).get("revenue")),
                    "Valuation": self._clean_financial_value(data.get("financial_data", {}).get("valuation")),
                    "Funding Raised": self._clean_financial_value(data.get("financial_data", {}).get("funding_raised")),
                    "Last Funding Round": data.get("financial_data", {}).get("last_funding_round"),
                    "Twitter": data.get("social_media", {}).get("twitter"),
                    "LinkedIn": data.get("social_media", {}).get("linkedin"),
                    "Key Personnel Count": len(data.get("key_personnel", [])),
                    "Products Count": len(data.get("products_services", [])),
                    "Last Updated": pd.Timestamp.now()
                }
                rows.append(row)
        
        return pd.DataFrame(rows)
    
    def _clean_employee_count(self, employee_count: str) -> int:
        """Convert employee count ranges to numeric values for charts."""
        if not employee_count:
            return 0
        
        # Handle ranges like "501-1000"
        if "-" in str(employee_count):
            parts = employee_count.split("-")
            try:
                return int(parts[1])  # Use upper bound
            except:
                return 0
        
        # Handle single numbers
        try:
            return int(employee_count.replace(",", ""))
        except:
            return 0
    
    def _clean_financial_value(self, value: str) -> float:
        """Convert financial strings to numeric values."""
        if not value:
            return 0.0
        
        # Remove currency symbols and convert to float
        clean_value = value.replace("$", "").replace(",", "")
        
        # Handle suffixes like "1.2B", "500M", "10K"
        multipliers = {"K": 1000, "M": 1000000, "B": 1000000000}
        
        for suffix, multiplier in multipliers.items():
            if clean_value.upper().endswith(suffix):
                try:
                    return float(clean_value[:-1]) * multiplier
                except:
                    return 0.0
        
        try:
            return float(clean_value)
        except:
            return 0.0

# Usage in Power BI Python script
connector = PowerBICompanyConnector("http://localhost:8000")
company_list = ["Microsoft", "Apple", "Google", "Amazon", "Tesla"]
df = asyncio.run(connector.get_companies_data(company_list))

# This DataFrame can now be used in Power BI visualizations
```

### Tableau Integration

Create a Tableau Web Data Connector:

```javascript
// tableau_wdc.js - Tableau Web Data Connector
(function() {
    var myConnector = tableau.makeConnector();
    
    myConnector.getSchema = function(schemaCallback) {
        var cols = [
            { id: "company_name", alias: "Company Name", dataType: tableau.dataTypeEnum.string },
            { id: "domain", alias: "Domain", dataType: tableau.dataTypeEnum.string },
            { id: "industry", alias: "Industry", dataType: tableau.dataTypeEnum.string },
            { id: "employee_count", alias: "Employee Count", dataType: tableau.dataTypeEnum.int },
            { id: "founded_year", alias: "Founded Year", dataType: tableau.dataTypeEnum.int },
            { id: "revenue", alias: "Revenue", dataType: tableau.dataTypeEnum.float },
            { id: "valuation", alias: "Valuation", dataType: tableau.dataTypeEnum.float },
            { id: "city", alias: "City", dataType: tableau.dataTypeEnum.string },
            { id: "country", alias: "Country", dataType: tableau.dataTypeEnum.string }
        ];
        
        var tableSchema = {
            id: "company_data",
            alias: "Company Information",
            columns: cols
        };
        
        schemaCallback([tableSchema]);
    };
    
    myConnector.getData = function(table, doneCallback) {
        var companies = tableau.connectionData.split(",");
        var apiUrl = "http://localhost:8000";
        
        // Submit batch request
        fetch(apiUrl + "/api/v1/company/batch/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                company_names: companies,
                extraction_mode: "standard"
            })
        })
        .then(response => response.json())
        .then(data => {
            var batchId = data.data.batch_id;
            return pollForResults(apiUrl, batchId);
        })
        .then(results => {
            var tableData = [];
            
            results.forEach(result => {
                if (result.extraction_status === "success") {
                    var data = result.data;
                    tableData.push({
                        "company_name": data.company_name || "",
                        "domain": data.domain || "",
                        "industry": data.industry || "",
                        "employee_count": cleanEmployeeCount(data.employee_count),
                        "founded_year": data.founded_year || null,
                        "revenue": cleanFinancialValue(data.financial_data?.revenue),
                        "valuation": cleanFinancialValue(data.financial_data?.valuation),
                        "city": data.headquarters?.city || "",
                        "country": data.headquarters?.country || ""
                    });
                }
            });
            
            table.appendRows(tableData);
            doneCallback();
        })
        .catch(error => {
            tableau.abortWithError("Error fetching company data: " + error.message);
        });
    };
    
    function pollForResults(apiUrl, batchId) {
        return new Promise((resolve, reject) => {
            function checkStatus() {
                fetch(apiUrl + "/api/v1/company/batch/" + batchId + "/status")
                .then(response => response.json())
                .then(data => {
                    if (data.data.status === "completed") {
                        // Get results
                        fetch(apiUrl + "/api/v1/company/batch/" + batchId + "/results")
                        .then(response => response.json())
                        .then(resultsData => resolve(resultsData.data.results))
                        .catch(reject);
                    } else if (data.data.status === "failed") {
                        reject(new Error("Batch processing failed"));
                    } else {
                        setTimeout(checkStatus, 5000); // Check again in 5 seconds
                    }
                })
                .catch(reject);
            }
            checkStatus();
        });
    }
    
    function cleanEmployeeCount(employeeCount) {
        if (!employeeCount) return 0;
        if (employeeCount.includes("-")) {
            return parseInt(employeeCount.split("-")[1]) || 0;
        }
        return parseInt(employeeCount.replace(/,/g, "")) || 0;
    }
    
    function cleanFinancialValue(value) {
        if (!value) return 0;
        var cleaned = value.replace(/[$,]/g, "");
        var multipliers = { "K": 1000, "M": 1000000, "B": 1000000000 };
        
        for (var suffix in multipliers) {
            if (cleaned.toUpperCase().endsWith(suffix)) {
                return parseFloat(cleaned.slice(0, -1)) * multipliers[suffix] || 0;
            }
        }
        
        return parseFloat(cleaned) || 0;
    }
    
    tableau.registerConnector(myConnector);
})();
```

## CRM Integration

### Salesforce Integration

Comprehensive Salesforce integration with custom objects:

```python
# salesforce_integration.py
from simple_salesforce import Salesforce
import httpx
import asyncio
from typing import List, Dict, Any, Optional
import logging

class SalesforceCompanySync:
    def __init__(self, sf_credentials: Dict[str, str], api_base_url: str):
        self.sf = Salesforce(**sf_credentials)
        self.api_base_url = api_base_url
        self.logger = logging.getLogger(__name__)
    
    async def sync_companies(self, company_names: List[str]) -> Dict[str, Any]:
        """Extract company data and sync to Salesforce."""
        
        # Extract company data
        company_data = await self._extract_companies(company_names)
        
        # Sync to Salesforce
        sync_results = {"successful": [], "failed": []}
        
        for company_name, data in company_data.items():
            try:
                if data["success"]:
                    account_id = await self._create_or_update_account(data["data"])
                    await self._create_contacts(account_id, data["data"])
                    await self._create_financial_records(account_id, data["data"])
                    
                    sync_results["successful"].append(company_name)
                    self.logger.info(f"Successfully synced {company_name}")
                else:
                    sync_results["failed"].append({
                        "company": company_name,
                        "error": "Data extraction failed"
                    })
            except Exception as e:
                sync_results["failed"].append({
                    "company": company_name,
                    "error": str(e)
                })
                self.logger.error(f"Failed to sync {company_name}: {e}")
        
        return sync_results
    
    async def _extract_companies(self, company_names: List[str]) -> Dict[str, Any]:
        """Extract company data from API."""
        
        async with httpx.AsyncClient(timeout=300) as client:
            # Submit batch request
            batch_response = await client.post(
                f"{self.api_base_url}/api/v1/company/batch/submit",
                json={
                    "company_names": company_names,
                    "extraction_mode": "comprehensive",
                    "include_key_personnel": True,
                    "include_financial_data": True
                }
            )
            
            batch_id = batch_response.json()["data"]["batch_id"]
            
            # Wait for completion
            while True:
                status_response = await client.get(
                    f"{self.api_base_url}/api/v1/company/batch/{batch_id}/status"
                )
                status_data = status_response.json()["data"]
                
                if status_data["status"] == "completed":
                    break
                elif status_data["status"] == "failed":
                    raise Exception("Batch processing failed")
                
                await asyncio.sleep(10)
            
            # Get results
            results_response = await client.get(
                f"{self.api_base_url}/api/v1/company/batch/{batch_id}/results"
            )
            
            results = results_response.json()["data"]["results"]
            
            # Format results
            formatted_results = {}
            for result in results:
                formatted_results[result["company_name"]] = {
                    "success": result["extraction_status"] == "success",
                    "data": result.get("data"),
                    "error": result.get("error")
                }
            
            return formatted_results
    
    def _create_or_update_account(self, company_data: Dict[str, Any]) -> str:
        """Create or update Salesforce Account record."""
        
        account_data = {
            "Name": company_data.get("company_name"),
            "Website": company_data.get("contact_info", {}).get("website"),
            "Industry": company_data.get("industry"),
            "Type": company_data.get("company_type"),
            "Description": company_data.get("description", "")[:32000],  # Salesforce limit
            "NumberOfEmployees": self._parse_employee_count(company_data.get("employee_count")),
            "YearStarted": str(company_data.get("founded_year")) if company_data.get("founded_year") else None,
            "Phone": company_data.get("contact_info", {}).get("phone"),
            "BillingStreet": company_data.get("headquarters", {}).get("address"),
            "BillingCity": company_data.get("headquarters", {}).get("city"),
            "BillingState": company_data.get("headquarters", {}).get("state"),
            "BillingPostalCode": company_data.get("headquarters", {}).get("postal_code"),
            "BillingCountry": company_data.get("headquarters", {}).get("country"),
            # Custom fields for social media
            "Twitter_URL__c": company_data.get("social_media", {}).get("twitter"),
            "LinkedIn_URL__c": company_data.get("social_media", {}).get("linkedin"),
            "GitHub_URL__c": company_data.get("social_media", {}).get("github")
        }
        
        # Remove None values
        account_data = {k: v for k, v in account_data.items() if v is not None}
        
        # Check if account exists
        existing_accounts = self.sf.query(
            f"SELECT Id FROM Account WHERE Name = '{company_data.get('company_name')}' OR Website = '{company_data.get('contact_info', {}).get('website')}'"
        )
        
        if existing_accounts["records"]:
            # Update existing account
            account_id = existing_accounts["records"][0]["Id"]
            self.sf.Account.update(account_id, account_data)
        else:
            # Create new account
            result = self.sf.Account.create(account_data)
            account_id = result["id"]
        
        return account_id
    
    def _create_contacts(self, account_id: str, company_data: Dict[str, Any]):
        """Create Contact records for key personnel."""
        
        key_personnel = company_data.get("key_personnel", [])
        
        for person in key_personnel[:5]:  # Limit to top 5 people
            contact_data = {
                "AccountId": account_id,
                "FirstName": self._parse_first_name(person.get("name", "")),
                "LastName": self._parse_last_name(person.get("name", "")),
                "Title": person.get("position"),
                "Description": person.get("bio", "")[:32000],
                "LinkedIn_URL__c": person.get("profile_url")
            }
            
            # Check if contact exists
            full_name = person.get("name", "")
            existing_contacts = self.sf.query(
                f"SELECT Id FROM Contact WHERE AccountId = '{account_id}' AND Name = '{full_name}'"
            )
            
            if not existing_contacts["records"]:
                self.sf.Contact.create(contact_data)
    
    def _create_financial_records(self, account_id: str, company_data: Dict[str, Any]):
        """Create custom financial records."""
        
        financial_data = company_data.get("financial_data", {})
        
        if financial_data:
            # Assuming you have a custom object "Company_Financial_Data__c"
            financial_record = {
                "Account__c": account_id,
                "Revenue__c": self._parse_financial_value(financial_data.get("revenue")),
                "Valuation__c": self._parse_financial_value(financial_data.get("valuation")),
                "Funding_Raised__c": self._parse_financial_value(financial_data.get("funding_raised")),
                "Last_Funding_Round__c": financial_data.get("last_funding_round"),
                "Investors__c": ", ".join(financial_data.get("investors", [])[:5])  # Top 5 investors
            }
            
            # Remove None values
            financial_record = {k: v for k, v in financial_record.items() if v is not None}
            
            if financial_record:
                try:
                    self.sf.Company_Financial_Data__c.create(financial_record)
                except AttributeError:
                    # Custom object doesn't exist, skip
                    self.logger.warning("Company_Financial_Data__c custom object not found")
    
    def _parse_employee_count(self, employee_count: str) -> Optional[int]:
        """Parse employee count string to integer."""
        if not employee_count:
            return None
        
        if "-" in str(employee_count):
            # Use upper bound of range
            return int(employee_count.split("-")[1])
        
        try:
            return int(employee_count.replace(",", ""))
        except:
            return None
    
    def _parse_financial_value(self, value: str) -> Optional[float]:
        """Parse financial string to numeric value."""
        if not value:
            return None
        
        # Remove currency symbols
        clean_value = value.replace("$", "").replace(",", "")
        
        # Handle suffixes
        multipliers = {"K": 1000, "M": 1000000, "B": 1000000000}
        
        for suffix, multiplier in multipliers.items():
            if clean_value.upper().endswith(suffix):
                try:
                    return float(clean_value[:-1]) * multiplier
                except:
                    return None
        
        try:
            return float(clean_value)
        except:
            return None
    
    def _parse_first_name(self, full_name: str) -> str:
        """Extract first name from full name."""
        return full_name.split()[0] if full_name else ""
    
    def _parse_last_name(self, full_name: str) -> str:
        """Extract last name from full name."""
        parts = full_name.split()
        return " ".join(parts[1:]) if len(parts) > 1 else ""

# Usage example
async def sync_to_salesforce():
    sf_credentials = {
        "username": "your_sf_username",
        "password": "your_sf_password",
        "security_token": "your_sf_security_token",
        "domain": "test"  # or "login" for production
    }
    
    syncer = SalesforceCompanySync(sf_credentials, "http://localhost:8000")
    
    companies = ["Salesforce", "HubSpot", "Pipedrive", "Zoho", "monday.com"]
    results = await syncer.sync_companies(companies)
    
    print(f"Successfully synced: {len(results['successful'])} companies")
    print(f"Failed to sync: {len(results['failed'])} companies")
    
    for failure in results["failed"]:
        print(f"Failed: {failure['company']} - {failure['error']}")

asyncio.run(sync_to_salesforce())
```

### HubSpot Integration

```python
# hubspot_integration.py
import httpx
import asyncio
from typing import List, Dict, Any
import json

class HubSpotCompanySync:
    def __init__(self, hubspot_api_key: str, api_base_url: str):
        self.hubspot_api_key = hubspot_api_key
        self.api_base_url = api_base_url
        self.hubspot_base_url = "https://api.hubapi.com"
    
    async def sync_companies(self, company_names: List[str]) -> Dict[str, Any]:
        """Extract and sync companies to HubSpot."""
        
        # Extract company data
        company_data = await self._extract_companies(company_names)
        
        # Sync to HubSpot
        sync_results = {"successful": [], "failed": []}
        
        async with httpx.AsyncClient() as client:
            for company_name, data in company_data.items():
                try:
                    if data["success"]:
                        company_id = await self._create_or_update_company(client, data["data"])
                        await self._create_contacts(client, company_id, data["data"])
                        
                        sync_results["successful"].append(company_name)
                    else:
                        sync_results["failed"].append({
                            "company": company_name,
                            "error": "Data extraction failed"
                        })
                except Exception as e:
                    sync_results["failed"].append({
                        "company": company_name,
                        "error": str(e)
                    })
        
        return sync_results
    
    async def _create_or_update_company(self, client: httpx.AsyncClient, company_data: Dict[str, Any]) -> str:
        """Create or update HubSpot Company record."""
        
        # Map data to HubSpot properties
        properties = {
            "name": company_data.get("company_name"),
            "domain": company_data.get("domain"),
            "industry": company_data.get("industry"),
            "description": company_data.get("description", "")[:65536],  # HubSpot limit
            "numberofemployees": self._parse_employee_count(company_data.get("employee_count")),
            "year_founded": str(company_data.get("founded_year")) if company_data.get("founded_year") else None,
            "website": company_data.get("contact_info", {}).get("website"),
            "phone": company_data.get("contact_info", {}).get("phone"),
            "city": company_data.get("headquarters", {}).get("city"),
            "state": company_data.get("headquarters", {}).get("state"),
            "country": company_data.get("headquarters", {}).get("country"),
            "zip": company_data.get("headquarters", {}).get("postal_code"),
            "twitterhandle": self._extract_twitter_handle(company_data.get("social_media", {}).get("twitter")),
            "linkedin_company_page": company_data.get("social_media", {}).get("linkedin"),
            # Custom properties for financial data
            "company_valuation": self._format_financial_value(company_data.get("financial_data", {}).get("valuation")),
            "total_funding": self._format_financial_value(company_data.get("financial_data", {}).get("funding_raised")),
            "last_funding_round": company_data.get("financial_data", {}).get("last_funding_round")
        }
        
        # Remove None values
        properties = {k: v for k, v in properties.items() if v is not None}
        
        # Check if company exists
        domain = company_data.get("domain")
        if domain:
            search_response = await client.get(
                f"{self.hubspot_base_url}/crm/v3/objects/companies/search",
                headers={"Authorization": f"Bearer {self.hubspot_api_key}"},
                params={
                    "q": domain,
                    "properties": "id,domain"
                }
            )
            
            search_results = search_response.json()
            
            if search_results.get("results"):
                # Update existing company
                company_id = search_results["results"][0]["id"]
                await client.patch(
                    f"{self.hubspot_base_url}/crm/v3/objects/companies/{company_id}",
                    headers={
                        "Authorization": f"Bearer {self.hubspot_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={"properties": properties}
                )
            else:
                # Create new company
                create_response = await client.post(
                    f"{self.hubspot_base_url}/crm/v3/objects/companies",
                    headers={
                        "Authorization": f"Bearer {self.hubspot_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={"properties": properties}
                )
                company_id = create_response.json()["id"]
        else:
            # Create new company without domain check
            create_response = await client.post(
                f"{self.hubspot_base_url}/crm/v3/objects/companies",
                headers={
                    "Authorization": f"Bearer {self.hubspot_api_key}",
                    "Content-Type": "application/json"
                },
                json={"properties": properties}
            )
            company_id = create_response.json()["id"]
        
        return company_id
    
    async def _create_contacts(self, client: httpx.AsyncClient, company_id: str, company_data: Dict[str, Any]):
        """Create HubSpot Contact records for key personnel."""
        
        key_personnel = company_data.get("key_personnel", [])
        
        for person in key_personnel[:3]:  # Limit to top 3 people
            contact_properties = {
                "firstname": self._parse_first_name(person.get("name", "")),
                "lastname": self._parse_last_name(person.get("name", "")),
                "jobtitle": person.get("position"),
                "hs_content_membership_notes": person.get("bio", "")[:65536],
                "linkedin_url": person.get("profile_url"),
                "company": company_data.get("company_name")
            }
            
            # Remove None values
            contact_properties = {k: v for k, v in contact_properties.items() if v is not None}
            
            # Create contact
            contact_response = await client.post(
                f"{self.hubspot_base_url}/crm/v3/objects/contacts",
                headers={
                    "Authorization": f"Bearer {self.hubspot_api_key}",
                    "Content-Type": "application/json"
                },
                json={"properties": contact_properties}
            )
            
            contact_id = contact_response.json()["id"]
            
            # Associate contact with company
            await client.put(
                f"{self.hubspot_base_url}/crm/v4/objects/contact/{contact_id}/associations/company/{company_id}",
                headers={"Authorization": f"Bearer {self.hubspot_api_key}"},
                json=[{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 1}]
            )

# Similar helper methods as in Salesforce integration...
```

## Data Analysis and Machine Learning

### Pandas and Jupyter Integration

```python
# jupyter_analysis.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import httpx
import asyncio
from typing import List, Dict, Any
import warnings
warnings.filterwarnings('ignore')

class CompanyDataAnalyzer:
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url
    
    async def analyze_industry(self, companies: List[str]) -> pd.DataFrame:
        """Analyze companies and create comprehensive DataFrame for analysis."""
        
        # Extract company data
        company_data = await self._extract_companies(companies)
        
        # Create analysis DataFrame
        df = self._create_analysis_dataframe(company_data)
        
        # Add calculated fields
        df = self._add_calculated_fields(df)
        
        return df
    
    def _create_analysis_dataframe(self, company_data: Dict[str, Any]) -> pd.DataFrame:
        """Create pandas DataFrame optimized for analysis."""
        
        rows = []
        for company_name, result in company_data.items():
            if result["success"] and result["data"]:
                data = result["data"]
                
                row = {
                    "company_name": data.get("company_name"),
                    "domain": data.get("domain"),
                    "industry": data.get("industry"),
                    "employee_count_raw": data.get("employee_count"),
                    "employee_count_numeric": self._parse_employee_count(data.get("employee_count")),
                    "founded_year": data.get("founded_year"),
                    "company_type": data.get("company_type"),
                    "country": data.get("headquarters", {}).get("country"),
                    "city": data.get("headquarters", {}).get("city"),
                    "state": data.get("headquarters", {}).get("state"),
                    "revenue_raw": data.get("financial_data", {}).get("revenue"),
                    "revenue_numeric": self._parse_financial_value(data.get("financial_data", {}).get("revenue")),
                    "valuation_raw": data.get("financial_data", {}).get("valuation"),
                    "valuation_numeric": self._parse_financial_value(data.get("financial_data", {}).get("valuation")),
                    "funding_raised_raw": data.get("financial_data", {}).get("funding_raised"),
                    "funding_raised_numeric": self._parse_financial_value(data.get("financial_data", {}).get("funding_raised")),
                    "last_funding_round": data.get("financial_data", {}).get("last_funding_round"),
                    "investor_count": len(data.get("financial_data", {}).get("investors", [])),
                    "has_twitter": bool(data.get("social_media", {}).get("twitter")),
                    "has_linkedin": bool(data.get("social_media", {}).get("linkedin")),
                    "has_github": bool(data.get("social_media", {}).get("github")),
                    "social_media_presence": sum([
                        bool(data.get("social_media", {}).get(platform)) 
                        for platform in ["twitter", "linkedin", "github", "youtube", "facebook", "instagram"]
                    ]),
                    "key_personnel_count": len(data.get("key_personnel", [])),
                    "products_count": len(data.get("products_services", [])),
                    "competitors_count": len(data.get("competitors", [])),
                    "company_age": (2024 - data.get("founded_year")) if data.get("founded_year") else None
                }
                
                rows.append(row)
        
        return pd.DataFrame(rows)
    
    def _add_calculated_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add calculated fields for analysis."""
        
        # Company size categories
        def categorize_company_size(employee_count):
            if pd.isna(employee_count):
                return "Unknown"
            elif employee_count < 50:
                return "Startup"
            elif employee_count < 200:
                return "Small"
            elif employee_count < 1000:
                return "Medium"
            elif employee_count < 5000:
                return "Large"
            else:
                return "Enterprise"
        
        df["company_size_category"] = df["employee_count_numeric"].apply(categorize_company_size)
        
        # Funding stage based on valuation
        def categorize_funding_stage(valuation):
            if pd.isna(valuation) or valuation == 0:
                return "Unknown"
            elif valuation < 10_000_000:  # $10M
                return "Early Stage"
            elif valuation < 100_000_000:  # $100M
                return "Growth Stage"
            elif valuation < 1_000_000_000:  # $1B
                return "Late Stage"
            else:
                return "Unicorn"
        
        df["funding_stage"] = df["valuation_numeric"].apply(categorize_funding_stage)
        
        # Revenue per employee (if both available)
        df["revenue_per_employee"] = np.where(
            (df["revenue_numeric"] > 0) & (df["employee_count_numeric"] > 0),
            df["revenue_numeric"] / df["employee_count_numeric"],
            np.nan
        )
        
        # Valuation to revenue ratio
        df["valuation_to_revenue_ratio"] = np.where(
            (df["valuation_numeric"] > 0) & (df["revenue_numeric"] > 0),
            df["valuation_numeric"] / df["revenue_numeric"],
            np.nan
        )
        
        return df
    
    def create_industry_analysis_report(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Create comprehensive industry analysis report."""
        
        report = {
            "summary": {
                "total_companies": len(df),
                "industries_covered": df["industry"].nunique(),
                "countries_covered": df["country"].nunique(),
                "avg_company_age": df["company_age"].mean(),
                "total_employees": df["employee_count_numeric"].sum(),
                "total_valuation": df["valuation_numeric"].sum(),
                "total_funding_raised": df["funding_raised_numeric"].sum()
            },
            "industry_breakdown": df.groupby("industry").agg({
                "company_name": "count",
                "employee_count_numeric": ["mean", "median", "sum"],
                "valuation_numeric": ["mean", "median", "sum"],
                "revenue_numeric": ["mean", "median"],
                "company_age": "mean"
            }).round(2).to_dict(),
            "company_size_distribution": df["company_size_category"].value_counts().to_dict(),
            "funding_stage_distribution": df["funding_stage"].value_counts().to_dict(),
            "geographic_distribution": df["country"].value_counts().head(10).to_dict(),
            "top_performers": {
                "highest_valuation": df.nlargest(5, "valuation_numeric")[["company_name", "valuation_raw", "industry"]].to_dict("records"),
                "highest_revenue": df.nlargest(5, "revenue_numeric")[["company_name", "revenue_raw", "industry"]].to_dict("records"),
                "most_employees": df.nlargest(5, "employee_count_numeric")[["company_name", "employee_count_raw", "industry"]].to_dict("records"),
                "highest_revenue_per_employee": df.nlargest(5, "revenue_per_employee")[["company_name", "revenue_per_employee", "industry"]].to_dict("records")
            }
        }
        
        return report
    
    def create_visualizations(self, df: pd.DataFrame, output_dir: str = "./plots"):
        """Create comprehensive visualization suite."""
        
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Set style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # 1. Industry distribution
        plt.figure(figsize=(12, 8))
        industry_counts = df["industry"].value_counts().head(10)
        plt.barh(range(len(industry_counts)), industry_counts.values)
        plt.yticks(range(len(industry_counts)), industry_counts.index)
        plt.title("Top 10 Industries by Company Count")
        plt.xlabel("Number of Companies")
        plt.tight_layout()
        plt.savefig(f"{output_dir}/industry_distribution.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Company size vs Valuation scatter plot
        plt.figure(figsize=(12, 8))
        scatter_df = df.dropna(subset=["employee_count_numeric", "valuation_numeric"])
        scatter_df = scatter_df[scatter_df["valuation_numeric"] > 0]
        
        plt.scatter(scatter_df["employee_count_numeric"], 
                   scatter_df["valuation_numeric"], 
                   alpha=0.6, s=100)
        
        plt.xlabel("Employee Count")
        plt.ylabel("Valuation ($)")
        plt.title("Company Size vs Valuation")
        plt.yscale('log')
        plt.xscale('log')
        
        # Add trend line
        from scipy import stats
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            np.log(scatter_df["employee_count_numeric"]), 
            np.log(scatter_df["valuation_numeric"])
        )
        
        x_trend = np.linspace(scatter_df["employee_count_numeric"].min(), 
                             scatter_df["employee_count_numeric"].max(), 100)
        y_trend = np.exp(intercept) * x_trend ** slope
        plt.plot(x_trend, y_trend, 'r--', alpha=0.8, 
                label=f'Trend (R² = {r_value**2:.3f})')
        plt.legend()
        plt.tight_layout()
        plt.savefig(f"{output_dir}/size_vs_valuation.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. Funding stage distribution
        plt.figure(figsize=(10, 6))
        funding_dist = df["funding_stage"].value_counts()
        plt.pie(funding_dist.values, labels=funding_dist.index, autopct='%1.1f%%', startangle=90)
        plt.title("Funding Stage Distribution")
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig(f"{output_dir}/funding_stage_distribution.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 4. Revenue per employee by industry
        plt.figure(figsize=(14, 8))
        rpe_by_industry = df.dropna(subset=["revenue_per_employee"]).groupby("industry")["revenue_per_employee"].mean().sort_values(ascending=False).head(10)
        plt.barh(range(len(rpe_by_industry)), rpe_by_industry.values)
        plt.yticks(range(len(rpe_by_industry)), rpe_by_industry.index)
        plt.xlabel("Revenue per Employee ($)")
        plt.title("Average Revenue per Employee by Industry (Top 10)")
        plt.tight_layout()
        plt.savefig(f"{output_dir}/revenue_per_employee_by_industry.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Visualizations saved to {output_dir}/")

# Usage example for Jupyter notebook
async def analyze_tech_companies():
    analyzer = CompanyDataAnalyzer("http://localhost:8000")
    
    # Define companies to analyze
    companies = [
        "Apple", "Microsoft", "Google", "Amazon", "Meta", "Tesla", "Netflix", 
        "Adobe", "Salesforce", "Zoom", "Slack", "Spotify", "Uber", "Airbnb",
        "Stripe", "SpaceX", "OpenAI", "Anthropic", "Databricks", "Snowflake"
    ]
    
    # Extract and analyze data
    df = await analyzer.analyze_industry(companies)
    
    # Create analysis report
    report = analyzer.create_industry_analysis_report(df)
    
    # Create visualizations
    analyzer.create_visualizations(df)
    
    # Display summary
    print("=== INDUSTRY ANALYSIS SUMMARY ===")
    print(f"Total Companies Analyzed: {report['summary']['total_companies']}")
    print(f"Industries Covered: {report['summary']['industries_covered']}")
    print(f"Countries Covered: {report['summary']['countries_covered']}")
    print(f"Average Company Age: {report['summary']['avg_company_age']:.1f} years")
    print(f"Total Market Valuation: ${report['summary']['total_valuation']:,.0f}")
    
    return df, report

# Run analysis
# df, report = await analyze_tech_companies()
```

## Webhook and Event-Driven Integration

### Flask Webhook Server

```python
# webhook_server.py
from flask import Flask, request, jsonify
import httpx
import asyncio
import json
from datetime import datetime
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebhookProcessor:
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url
        self.processing_queue = []
    
    async def process_company_webhook(self, webhook_data: dict):
        """Process incoming webhook data to extract company information."""
        
        company_name = webhook_data.get("company_name")
        if not company_name:
            return {"error": "No company name provided"}
        
        try:
            # Extract company information
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base_url}/api/v1/company/extract",
                    json={
                        "company_name": company_name,
                        "extraction_mode": webhook_data.get("extraction_mode", "standard"),
                        "include_financial_data": webhook_data.get("include_financial", True),
                        "include_key_personnel": webhook_data.get("include_personnel", True)
                    }
                )
                
                if response.status_code == 200:
                    company_data = response.json()["data"]
                    
                    # Process the extracted data based on webhook type
                    await self._route_webhook_data(webhook_data, company_data)
                    
                    return {"status": "success", "company_data": company_data}
                else:
                    return {"error": f"API error: {response.text}"}
        
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return {"error": str(e)}
    
    async def _route_webhook_data(self, webhook_data: dict, company_data: dict):
        """Route extracted data based on webhook source."""
        
        webhook_source = webhook_data.get("source", "unknown")
        
        if webhook_source == "crm_lead":
            await self._handle_crm_lead(webhook_data, company_data)
        elif webhook_source == "sales_prospecting":
            await self._handle_sales_prospect(webhook_data, company_data)
        elif webhook_source == "investment_research":
            await self._handle_investment_research(webhook_data, company_data)
        else:
            logger.info(f"Unhandled webhook source: {webhook_source}")
    
    async def _handle_crm_lead(self, webhook_data: dict, company_data: dict):
        """Handle CRM lead webhook."""
        
        # Enrich lead data with company information
        enriched_data = {
            "lead_id": webhook_data.get("lead_id"),
            "company_info": company_data,
            "enrichment_timestamp": datetime.utcnow().isoformat(),
            "confidence_score": company_data.get("metadata", {}).get("confidence_score", 0)
        }
        
        # Send back to CRM system
        crm_webhook_url = webhook_data.get("callback_url")
        if crm_webhook_url:
            async with httpx.AsyncClient() as client:
                await client.post(crm_webhook_url, json=enriched_data)
        
        logger.info(f"Processed CRM lead for {company_data.get('company_name')}")
    
    async def _handle_sales_prospect(self, webhook_data: dict, company_data: dict):
        """Handle sales prospecting webhook."""
        
        # Extract key information for sales team
        sales_data = {
            "prospect_id": webhook_data.get("prospect_id"),
            "company_name": company_data.get("company_name"),
            "industry": company_data.get("industry"),
            "employee_count": company_data.get("employee_count"),
            "contact_info": company_data.get("contact_info", {}),
            "key_personnel": company_data.get("key_personnel", [])[:3],  # Top 3 contacts
            "social_media": company_data.get("social_media", {}),
            "priority_score": self._calculate_sales_priority(company_data)
        }
        
        # Send to sales system
        sales_webhook_url = webhook_data.get("sales_system_url")
        if sales_webhook_url:
            async with httpx.AsyncClient() as client:
                await client.post(sales_webhook_url, json=sales_data)
        
        logger.info(f"Processed sales prospect for {company_data.get('company_name')}")
    
    def _calculate_sales_priority(self, company_data: dict) -> int:
        """Calculate sales priority score based on company data."""
        
        score = 0
        
        # Company size scoring
        employee_count = company_data.get("employee_count")
        if employee_count:
            if "1000+" in str(employee_count) or (isinstance(employee_count, int) and employee_count > 1000):
                score += 30
            elif "500-1000" in str(employee_count) or (isinstance(employee_count, int) and employee_count > 500):
                score += 20
            elif "200-500" in str(employee_count) or (isinstance(employee_count, int) and employee_count > 200):
                score += 10
        
        # Industry scoring (adjust based on your target industries)
        target_industries = ["Technology", "Software", "SaaS", "E-commerce", "FinTech"]
        if company_data.get("industry") in target_industries:
            score += 20
        
        # Financial health scoring
        financial_data = company_data.get("financial_data", {})
        if financial_data.get("revenue"):
            score += 15
        if financial_data.get("funding_raised"):
            score += 10
        
        # Contact availability scoring
        if company_data.get("contact_info", {}).get("email"):
            score += 10
        if company_data.get("key_personnel"):
            score += len(company_data["key_personnel"]) * 2
        
        return min(score, 100)  # Cap at 100

# Initialize processor
processor = WebhookProcessor("http://localhost:8000")

@app.route("/webhook/company-extract", methods=["POST"])
def company_extract_webhook():
    """Handle incoming company extraction webhooks."""
    
    try:
        webhook_data = request.get_json()
        
        # Validate required fields
        if not webhook_data.get("company_name"):
            return jsonify({"error": "company_name is required"}), 400
        
        # Process webhook asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            processor.process_company_webhook(webhook_data)
        )
        loop.close()
        
        if "error" in result:
            return jsonify(result), 500
        else:
            return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/webhook/batch-complete", methods=["POST"])
def batch_complete_webhook():
    """Handle batch processing completion webhooks."""
    
    try:
        webhook_data = request.get_json()
        batch_id = webhook_data.get("batch_id")
        status = webhook_data.get("status")
        
        logger.info(f"Batch {batch_id} completed with status: {status}")
        
        if status == "completed":
            # Process completed batch results
            # You could trigger downstream processing here
            pass
        
        return jsonify({"status": "received"}), 200
    
    except Exception as e:
        logger.error(f"Batch webhook error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
```

## Next Steps

1. **Choose Your Integration**: Select the integration examples most relevant to your use case
2. **Customize for Your Needs**: Adapt the code examples to match your specific requirements
3. **Test Integration**: Use the development API endpoint to test your integration
4. **Deploy**: Follow the [deployment guide](../deployment/) for production deployment
5. **Monitor**: Set up monitoring as described in [operations guide](../operations/)

## Additional Resources

- [API Documentation](../api/) - Complete API reference
- [User Guide](./README.md) - Getting started guide
- [Performance Guide](./performance-guide.md) - Optimization strategies
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions