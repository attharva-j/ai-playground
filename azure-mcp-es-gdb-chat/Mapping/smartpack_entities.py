
# smartpack_all_in_one_english.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging
import json
import os
import sys

# Add parent directory to path to import smartpack_generator
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from smartpackPdfMapping.smartpack_generator import generate_pdf_person, generate_pdf_company
from utils import upload_pdf_to_storage
from datetime import datetime
from collections import Counter

from utils import _execute_connector, merge_dicts
from Mapping.config_mapper import load_mapper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_COMPANY_FIELD = "CompanyName"
DEFAULT_PERSON_FIELD = "Overview.FullName"
import os
from dotenv import load_dotenv


class ISmartpackEntity(ABC):
    """Interface enforcing the required methods for smartpack entities."""

    @abstractmethod
    def get_smartpack_config(self, name: str, INTENTS_CONFIG: Dict[str, Any]) -> Dict[str, Any]:
        """Return the smartpack configuration (ES query, indexes, etc.)."""
        raise NotImplementedError

    @abstractmethod
    def generate_summary(
        self,
        es_response: Dict[str, Any],
        name: str,
        openai_client=None,
        secrets: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a structured summary from the Elasticsearch response."""
        raise NotImplementedError


class CompanySmartpack(ISmartpackEntity):
    """Implements the logic originally found in company.py."""

    def get_smartpack_config(self, company_name: str, INTENTS_CONFIG: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get smartpack configuration for a company (adapted from company.py).
        """
        if not INTENTS_CONFIG:
            logger.warning("Intents configuration not loaded")
            return {}

        try:
            cfg = INTENTS_CONFIG.get("companySmartpack", {})
            indexes = cfg.get("indexes", cfg.get("index", []))
            search_field = cfg.get("search_field", DEFAULT_COMPANY_FIELD)
            size = cfg.get("size", 10)
            source_fields = cfg.get("source", ["CompanyOverview", "BusinessDescription", "Leadership"])

            # Basic query construction (default: match_phrase)
            query_body = {
                "query": {
                    "bool": {
                        "must": [
                            {"match_phrase": {search_field: company_name}}
                        ]
                    }
                },
                "size": size,
                "_source": source_fields
            }

            # Additional filters or boosts could be added here if present in INTENTS_CONFIG
            return {
                "indexes": indexes,
                "body": query_body,
                "search_field": search_field,
                "size": size,
                "source": source_fields
            }
        except Exception as e:
            logger.error(f"Error building smartpack config for company: {e}")
            return {}

    def _fetch_ntlm_overlay(self, company_id: int, secrets: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Pull additional fields from the NTLM REST source for a company.
        """
        if not secrets or not secrets.get("NTLM_COMPANY_PATH"):
            return {}
        request_spec = {
            "operation": "get",
            "path": secrets.get("NTLM_COMPANY_PATH"),
            "params": {"companyId": company_id},
        }
        try:
            resp = _execute_connector("ntlm_rest", request_spec)
            if isinstance(resp, dict) and resp.get("error"):
                logger.warning("NTLM overlay returned error: %s", resp["error"])
                return {}
            return resp if isinstance(resp, dict) else {}
        except Exception as e:
            logger.error(f"NTLM overlay fetch failed: {e}")
            return {}

    def generate_summary(self, es_response: Dict[str, Any], company_name: str, openai_client = None, secrets: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a company summary from the ES response (adapted from company.py).
        Returns a simple, structured dictionary or a formatted text report.
        """
        try:
            hits = es_response.get("hits", {}).get("hits", [])
            if not hits:
                return {
                    "company_name": company_name,
                    "found": False,
                    "message": "No company data found",
                    "result_count": 0
                }

            company_data = hits[0].get("_source", {})
            ntlm_overlay = self._fetch_ntlm_overlay(company_data.get("ID"), secrets)

            if ntlm_overlay:
                company_data = merge_dicts(ntlm_overlay, company_data)
            

            # ------------------------------------------------------------------
            # JSON Summary (DO NOT MODIFY STRUCTURE OR KEYS)
            # ------------------------------------------------------------------
            summary = {
                "company_name": company_name,  # from your context

                # ---------------------------
                # 1. Key Information
                # ---------------------------
                "key_information": {
                    "Entity Type": company_data["keyInformation"]["entityType"] if "keyInformation" in company_data and "entityType" in company_data["keyInformation"] else "Reference: Entity Type",
                    "AUM/Revenue": company_data["keyInformation"]["revenue"] if "keyInformation" in company_data and "revenue" in company_data["keyInformation"] else "Reference: AUM/Revenue",
                    "No. of Employees": (company_data["CompanyOverview"]["TotalEmployees"] if "CompanyOverview" in company_data and "TotalEmployees" in company_data["CompanyOverview"] else "Reference: No. of Employees"),
                    "Headquarter": (company_data["CompanyOverview"]["CompanyLocation"] if "CompanyOverview" in company_data and "CompanyLocation" in company_data["CompanyOverview"] else "Reference: Headquarter"),
                    "Industry": company_data["keyInformation"]["industry"] if "keyInformation" in company_data and "industry" in company_data["keyInformation"] else "Reference: Industry",
                    "Year Founded": company_data["keyInformation"]["yearFounded"] if "keyInformation" in company_data and "yearFounded" in company_data["keyInformation"] else "Reference: Year Founded",
                    "Dry Powder": (company_data["DryPowder"] if "DryPowder" in company_data else "Reference: Dry Powder"),
                    "Active Portfolio": (company_data["ActivePortfolio"] if "ActivePortfolio" in company_data else "Reference: Active Portfolio"),
                    "Website": (company_data["Website"] if "Website" in company_data else "Reference: Website"),
                },

                # ---------------------------
                # 2. About the Company
                # ---------------------------
                "about_company": {
                    "Company Overview": company_data["BusinessDescription"] if "BusinessDescription" in company_data else "Reference: Company description",
                    "Industries Invested In": (
                        company_data["InvestmentIndustries"]
                        if "InvestmentIndustries" in company_data and company_data["InvestmentIndustries"]
                        else company_data["TargetIndustries"]
                        if "TargetIndustries" in company_data and company_data["TargetIndustries"]
                        else ["Reference: Industries invested in"]
                    ),
                    "Firm Type (RIA)": (company_data["FirmType"] if "FirmType" in company_data else "Reference: Firm type (RIA)"),
                },

                # ---------------------------
                # 3. Investment Strategy
                # ---------------------------
                "investment_strategy": {
                    "Private Equity Focus": (
                        company_data["InvestmentStrategy"]["PrivateEquityFocus"]
                        if "InvestmentStrategy" in company_data
                        and "PrivateEquityFocus" in company_data["InvestmentStrategy"]
                        and company_data["InvestmentStrategy"]["PrivateEquityFocus"] is not None
                        else "Reference: Private Equity Focus"
                    ),
                    "Broad Asset Classes": (
                        company_data["InvestmentStrategy"]["BroadAssetClasses"]
                        if "InvestmentStrategy" in company_data
                        and "BroadAssetClasses" in company_data["InvestmentStrategy"]
                        and company_data["InvestmentStrategy"]["BroadAssetClasses"] is not None
                        else "Reference: Broad Asset Classes"
                    ),
                    "Global Reach, Local Expertise": (
                        company_data["InvestmentStrategy"]["GlobalLocal"]
                        if "InvestmentStrategy" in company_data
                        and "GlobalLocal" in company_data["InvestmentStrategy"]
                        and company_data["InvestmentStrategy"]["GlobalLocal"] is not None
                        else "Reference: Global Reach, Local Expertise"
                    ),
                    "Active Ownership Model": (
                        company_data["InvestmentStrategy"]["ActiveOwnership"]
                        if "InvestmentStrategy" in company_data
                        and "ActiveOwnership" in company_data["InvestmentStrategy"]
                        and company_data["InvestmentStrategy"]["ActiveOwnership"] is not None
                        else "Reference: Active Ownership Model"
                    ),
                    "Long-term Value Creation": (
                        company_data["InvestmentStrategy"]["LongTermValueCreation"]
                        if "InvestmentStrategy" in company_data
                        and "LongTermValueCreation" in company_data["InvestmentStrategy"]
                        and company_data["InvestmentStrategy"]["LongTermValueCreation"] is not None
                        else "Reference: Long-term Value Creation"
                    ),
                    "Flexible Capital": (
                        company_data["InvestmentStrategy"]["FlexibleCapital"]
                        if "InvestmentStrategy" in company_data
                        and "FlexibleCapital" in company_data["InvestmentStrategy"]
                        and company_data["InvestmentStrategy"]["FlexibleCapital"] is not None
                        else "Reference: Flexible Capital"
                    ),
                    "Thematic Investing": (
                        company_data["InvestmentStrategy"]["ThematicInvesting"]
                        if "InvestmentStrategy" in company_data
                        and "ThematicInvesting" in company_data["InvestmentStrategy"]
                        and company_data["InvestmentStrategy"]["ThematicInvesting"] is not None
                        else "Reference: Thematic Investing"
                    ),
                    "Co-Investment and Partnerships": (
                        company_data["InvestmentStrategy"]["CoInvestmentPartnerships"]
                        if "InvestmentStrategy" in company_data
                        and "CoInvestmentPartnerships" in company_data["InvestmentStrategy"]
                        and company_data["InvestmentStrategy"]["CoInvestmentPartnerships"] is not None
                        else "Reference: Co-Investment and Partnerships"
                    ),
                },

                # ---------------------------
                # 4. Indicative Portfolio (Current)
                # ---------------------------
                "indicative_portfolio_current": {
                    "title": "Indicative Portfolio (Current)",
                    "portfolio_list": company_data["IndicativePortfolio"] if "IndicativePortfolio" in company_data else "Reference: Indicative Portfolio list",
                },

                # ---------------------------
                # 5. Financials
                # ---------------------------
                "financials": {
                    "Financials (general)": {
                        "current_year_revenue_usd": company_data["keyInformation"]["lastTwelveMonthsRevenueUSD"] if "keyInformation" in company_data and "lastTwelveMonthsRevenueUSD" in company_data["keyInformation"] else "Reference: current year revenue",
                        "last_year_revenue_enddate": company_data["keyInformation"]["lastTwelveMonthsRevenuePeriodEndDate"] if "keyInformation" in company_data and "lastTwelveMonthsRevenuePeriodEndDate" in company_data["keyInformation"] else "Reference: current year revenue end date",
                        "current_year_market_cap_usd": company_data["MarketCapUSDCurrentYear"] if "MarketCapUSDCurrentYear" in company_data else "N/A",
                        "other_financials": company_data["Financials"] if "Financials" in company_data else "Reference: Financials (general)"
                    },
                    "Segmental Financials": company_data["SegmentalFinancials"] if "SegmentalFinancials" in company_data else "Reference: Segmental Financials",
                },

                # ---------------------------
                # 6. Competitors
                # ---------------------------
                            "competitors": {
                    "list": company_data["Competitors"] if "Competitors" in company_data else "Reference: Competitors list",
                },

                # ---------------------------
                # 7. Analyst Reports
                # ---------------------------
                "analyst_reports": {
                    "reports": company_data["AnalystReports"] if "AnalystReports" in company_data else "Reference: Analyst reports list",
                },

                # ---------------------------
                # 8. News (January 2025 till Date)
                # ---------------------------
                "news": [
                    # Expected structure: {"date": "...", "headline": "...", "summary": "..."}
                    # If company_data has news entries, we transform them; otherwise, we leave an English reference
                ] + ([
                    {
                        "date": n["Date"] if "Date" in n else n["Fecha"] if "Fecha" in n else "Unknown date",
                        "headline": n["Title"] if "Title" in n else n["Headline"] if "Headline" in n else "No headline provided",
                        "summary": n["Summary"] if "Summary" in n else n["Resumen"] if "Resumen" in n else "No summary provided"
                    }
                    for n in (company_data["News"] if "News" in company_data else [])
                ] if "News" in company_data and company_data["News"] else ["Reference: News entries from January 2025 to date"]),

                # ---------------------------
                # 9. Leadership Team
                # ---------------------------
                "leadership_team": {
                    "members": (
                        company_data["leadership"]["executiveLeadership"]
                        if "leadership" in company_data and "Executives" in company_data["leadership"]
                        else ["Reference: Leadership team member - Name / Title / Full biography"]
                    )
                },

                # ---------------------------
                # 10. Board of Directors
                # ---------------------------
                "board_of_directors": {
                    "members": (
                        company_data["board"]["members"]
                        if "leadership" in company_data and "leadership" in company_data["leadership"]
                        else ["Reference: Board member - Name / Title"]
                    )
                },

                # ---------------------------
                # 11. Sustainability
                # ---------------------------
                "sustainability": {
                    "Sustainability ranking": company_data["SustainabilityRanking"] if "SustainabilityRanking" in company_data else "Reference: Sustainability ranking",
                    "Sustainability Report": company_data["SustainabilityReport"] if "SustainabilityReport" in company_data else "Reference: Sustainability report (link or summary)",
                },

                # ---------------------------
                # 12. Firm Assignment History
                # ---------------------------
                "assignments_with_rra": {
                    "RRA History – Assignments and PNBs in last 3 years": company_data["assignmentsWithRra"]["assignmentHistory"]["assignments"] if "assignmentsWithRra" in company_data and "assignmentHistory" in company_data["assignmentsWithRra"] else "Reference: firm assignments and PNBs last 3 years"
                },

                # ---------------------------
                # Extra: Minimal summary compatibility fields
                # ---------------------------
                "basic_info": {
                    "legal_name": (
                        company_data["LegalName"]
                        if "LegalName" in company_data
                        else company_data["CompanyName"]
                        if "CompanyName" in company_data
                        else "N/A"
                    ),
                    "ticker": company_data["Ticker"] if "Ticker" in company_data else "N/A",
                    "year_founded": company_data["CompanyOverview"]["YearFounded"] if "CompanyOverview" in company_data and "YearFounded" in company_data["CompanyOverview"] else "N/A",
                    "location": company_data["CompanyOverview"]["CompanyLocation"] if "CompanyOverview" in company_data and "CompanyLocation" in company_data["CompanyOverview"] else "N/A",
                },
                "company_overview": {
                    "total_employees": company_data["CompanyOverview"]["TotalEmployees"] if "CompanyOverview" in company_data and "TotalEmployees" in company_data["CompanyOverview"] else "N/A",
                    "primary_industry": company_data["PrimaryIndustry"]["Description"] if "PrimaryIndustry" in company_data and "Description" in company_data["PrimaryIndustry"] else "N/A",
                    "business_description": company_data["BusinessDescription"] if "BusinessDescription" in company_data else "N/A",
                },
                "financial_info": {
                    "current_year_revenue_usd": company_data["RevenueUSDCurrentYear"] if "RevenueUSDCurrentYear" in company_data else "N/A",
                    "current_year_market_cap_usd": company_data["MarketCapUSDCurrentYear"] if "MarketCapUSDCurrentYear" in company_data else "N/A",
                },
                "leadership": {
                    "executives": company_data["Leadership"]["Executives"] if "Leadership" in company_data and "Executives" in company_data["Leadership"] else [],
                    "board_members": company_data["Leadership"]["BoardMembers"] if "Leadership" in company_data and "BoardMembers" in company_data["Leadership"] else [],
                },
            }
            
            # Generate PDF using generate_pdf_company from smartpack_generator
            try:
                # ------------------------------------------------------------------
                # Load mapper and transform summary to pdf_content using configuration
                # ------------------------------------------------------------------
                mapper = load_mapper("company")

                # Build pdf_content using configuration-based mapping
                pdf_content = {
                    "company": company_name,
                    "first_table": {
                        "headers": ["Key Information", "Financial snapshot (Source: CapIQ / Annual Report, etc.)"],
                        "left_entries": mapper.build_table_entries(
                            summary,
                            mapper.config.get("pdf_content_mappings", {}).get("first_table", {}).get("left_entries", [])
                        ),
                        "right_entries": mapper.build_table_entries(
                            summary,
                            mapper.config.get("pdf_content_mappings", {}).get("first_table", {}).get("right_entries", [])
                        )
                    },
                    "about_investment": [
                        ("About the company", mapper.get_value_truncated(summary, "about_company.Company Overview", "N/A", max_length=1500)),
                        ("Investment Strategy", mapper.format_investment_strategy_bullets(summary))
                    ],
                    "indicative_portfolio": [
                        ("Indicative Portfolio (Current)",
                         mapper.get_value_truncated(summary, "indicative_portfolio_current.portfolio_list", "Reference to Indicative Portfolio", max_length=1500)),
                        ("Financials",
                         mapper.get_value_truncated(summary, "financials.Financials (general).current_year_revenue_usd", "Reference to Financials", max_length=800)),
                        ("Segmental Financials",
                         mapper.get_value_truncated(summary, "financials.Segmental Financials", "Reference to Segmental Financials", max_length=1500)),
                        ("Competitors",
                         mapper.get_value_truncated(summary, "competitors.list", "Reference to Competitors", max_length=1000)),
                        ("Analyst Reports",
                         mapper.get_value_truncated(summary, "analyst_reports.reports", "Reference to Analyst Reports", max_length=1500))
                    ],
                    "news": {
                        "header": "News (Recent)",
                        "items": mapper.build_news_items(summary)
                    },
                    "leadership_team": {
                        "title": "Leadership Team",
                        "rows": mapper.build_leadership_rows(summary)
                    },
                    "board_directors": {
                        "title": "Board of Directors",
                        "headers": ["Name", "Title"],
                        "rows": mapper.build_board_rows(summary)
                    },
                    "sustainability": {
                        "title": "Sustainability",
                        "subsections": [
                            {
                                "subtitle": "Sustainability ranking",
                                "content": mapper.get_value_truncated(summary, "sustainability.Sustainability ranking", "N/A", max_length=800)
                            },
                            {
                                "subtitle": "Sustainability Report",
                                "content": mapper.get_value_truncated(summary, "sustainability.Sustainability Report", "N/A", max_length=1500)
                            }
                        ]
                    },
                    "assignments_rra": {
                        "title": "Firm Assignment History",
                        "data": mapper.build_rra_assignments_table(summary, max_items=50)
                    }
                }

                # Sanitize company name for filename
                safe_company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_company_name = safe_company_name.replace(' ', '_')

                # Generate PDF in the smartpackPdfMapping/generated_pdfs directory
                current_dir = os.path.dirname(os.path.abspath(__file__))
                parent_dir = os.path.dirname(current_dir)
                output_dir = os.path.join(parent_dir, "smartpackPdfMapping", "generated_pdfs")
                os.makedirs(output_dir, exist_ok=True)

                pdf_path = os.path.join(output_dir, f"{safe_company_name}_smartpack.pdf")

                # Call generate_pdf_company
                generate_pdf_company(pdf_content, pdf_path)

                logger.info(f"Company SmartPack PDF generated locally: {pdf_path}")

                # Upload PDF to Azure Storage
                upload_result = upload_pdf_to_storage(
                    pdf_path=pdf_path,
                    blob_name=f"company/{os.path.basename(pdf_path)}"
                )

                # Get server base URL for download endpoints
                from mcp_app import SECRETS
                server_base_url = SECRETS.get("SERVER_BASE_URL")

                if upload_result.get("success"):
                    logger.info(f"Company SmartPack PDF uploaded to Azure Storage: {upload_result['blob_url']}")
                    #summary["pdf_path"] = pdf_path
                    #summary["pdf_blob_url"] = upload_result["blob_url"]
                    #summary["pdf_blob_name"] = upload_result["blob_name"]
                    #summary["pdf_container"] = upload_result["container_name"]

                    # Add smartpack_url for downloading through the server (as proxy to Azure Storage)
                    summary["smartpack_url"] = f"{server_base_url}/api/download-pdf-storage/{upload_result['blob_name']}"
                    # Also provide local download URL as fallback
                    #summary["smartpack_url_local"] = f"{server_base_url}/api/download-pdf-local/{os.path.basename(pdf_path)}"
                else:
                    logger.warning(f"Failed to upload PDF to Azure Storage: {upload_result.get('error')}")
                    #summary["pdf_path"] = pdf_path
                    summary["pdf_upload_error"] = upload_result.get("error")

                    # If upload failed, provide only local download URL
                    summary["smartpack_url"] = f"{server_base_url}/api/download-pdf-local/{os.path.basename(pdf_path)}"

                return summary

            except Exception as pdf_error:
                logger.error(f"Error generating PDF for company {company_name}: {pdf_error}")
                # Return summary even if PDF generation fails
                logger.info(f"Company summary generated for: {company_name}")
                return summary

        except Exception as e:
            logger.error(f"Error generating company summary: {e}")
            return {
                "company_name": company_name,
                "found": False,
                "message": f"Error processing company data: {str(e)}",
                "result_count": 0
            }
 


class PersonSmartpack(ISmartpackEntity):
    """Implements the logic originally found in person.py."""

    @staticmethod
    def _safe_dict(val: Any) -> Dict[str, Any]:
        return val if isinstance(val, dict) else {}

    @staticmethod
    def _safe_list(val: Any) -> List[Any]:
        return val if isinstance(val, list) else []

    def _extract_person_id(self, person_data: Dict[str, Any]) -> Any:
        """
        Try several common locations to find the personId to send to NTLM.
        """
        candidates = [
            person_data.get("personId"),
            person_data.get("PersonId"),
            person_data.get("PersonID"),
            person_data.get("personID"),
            person_data.get("Id"),
        ]
        overview = person_data.get("Overview") or {}
        candidates.extend([
            overview.get("personId"),
            overview.get("PersonId"),
            overview.get("PersonID"),
        ])
        for cid in candidates:
            if cid:
                return cid
        return None

    def _fetch_ntlm_overlay(self, id: Any, secrets: Optional[Dict[str, Any]], dataType: str) -> Dict[str, Any]:
        """
        Pull additional fields from the NTLM REST source for a person using personId.
        """
        if not secrets or not secrets.get("NTLM_PERSON_PATH") or not id:
            return {}

        request_spec = {
            "operation": "get",
            "path": secrets.get("NTLM_PERSON_PATH") if dataType == "person" else secrets.get("NTLM_COMPANY_PATH"),
            "params": {"personId": id} if dataType == "person" else {"companyId": id},
        }
        try:
            resp = _execute_connector("ntlm_rest", request_spec)
            if isinstance(resp, dict) and resp.get("error"):
                logger.warning("NTLM person overlay returned error: %s", resp["error"])
                return {}
            return resp if isinstance(resp, dict) else {}
        except Exception as e:
            logger.error(f"NTLM person overlay fetch failed: {e}")
            return {}

    def _merge_overlay(self, person_data: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge overlay into the ES person data, giving precedence to overlay values when non-empty.
        """
        if not overlay:
            return person_data
        return merge_dicts(overlay, person_data)

    def _generate_profile_summary_with_openai(self, person_data: Dict[str, Any], openai_client, secrets: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate profile summary bio bullets and conversation topics using OpenAI based on ntlm_overlay data.
        Uses educationHistory, employments, currentEmployment, homeAddress, and language from ntlm_overlay.
        Returns a dictionary with 'bio_bullets' and 'conversation_topics' keys.
        """
        if not openai_client or not secrets or not secrets.get("GPT_MODEL_NAME"):
            logger.warning("OpenAI client or GPT model not configured, returning default values")
            return {
                "bio_bullets": "N/A",
                "conversation_topics": ["Reference to conversation topics"]
            }

        try:
            # Log available keys for debugging
            logger.info(f"person_data keys available: {list(person_data.keys())}")

            # Extract relevant fields from person_data (which already has ntlm_overlay merged)
            # Try multiple field name variations since the structure might differ
            education_history = (
                person_data.get("educationHistory") or
                person_data.get("EducationHistory") or
                person_data.get("education") or
                []
            )

            employment_history = (
                person_data.get("employments") or
                person_data.get("EmploymentHistory") or
                []
            )

            current_employment = (
                person_data.get("currentEmployment") or
                person_data.get("CurrentEmployingCompanyInfo") or
                person_data.get("currentEmployingCompanyInfo") or
                {}
            )

            home_address = (
                person_data.get("homeAddress") or
                person_data.get("HomeAddress") or
                person_data.get("address") or
                {}
            )

            languages = (
                person_data.get("language") or
                person_data.get("languages") or
                person_data.get("Language") or
                person_data.get("LanguageProficiency") or
                []
            )

            # Build context for the prompt with actual data
            context_parts = []

            # Education
            if education_history and isinstance(education_history, list):
                edu_items = []
                for edu in education_history:
                    if isinstance(edu, dict):
                        degree = edu.get('degree') or edu.get('Degree') or edu.get('degreeType') or ''
                        institution = edu.get('institution') or edu.get('Institution') or edu.get('schoolName') or edu.get('SchoolName') or ''
                        field = edu.get('fieldOfStudy') or edu.get('major') or edu.get('Major') or ''

                        if degree or institution or field:
                            edu_text = f"{degree} {field}".strip() if field else degree
                            if institution:
                                edu_text = f"{edu_text} from {institution}".strip()
                            if edu_text:
                                edu_items.append(edu_text)

                if edu_items:
                    context_parts.append("Education:\n- " + "\n- ".join(edu_items))

            # Current Position
            if current_employment and isinstance(current_employment, dict):
                title = current_employment.get('title') or current_employment.get('jobTitle') or current_employment.get('JobTitle') or ''
                company = current_employment.get('company') or current_employment.get('companyName') or current_employment.get('CompanyName') or ''

                if title or company:
                    current_job = f"Current Position: {title}".strip()
                    if company:
                        current_job += f" at {company}"
                    context_parts.append(current_job)

            # Employment History
            if employment_history and isinstance(employment_history, list):
                emp_items = []
                for emp in employment_history[:5]:  # Limit to 5 most recent
                    if isinstance(emp, dict):
                        title = emp.get('title') or emp.get('JobTitle') or emp.get('jobTitle') or ''
                        company = emp.get('company') or emp.get('CompanyName') or emp.get('companyName') or ''
                        is_current = emp.get('IsCurrentJob') or emp.get('isCurrent') or False

                        if not is_current and (title or company):  # Skip current job as it's already listed
                            emp_text = title
                            if company:
                                emp_text = f"{emp_text} at {company}".strip()
                            if emp_text:
                                emp_items.append(emp_text)

                if emp_items:
                    context_parts.append("Previous Experience:\n- " + "\n- ".join(emp_items))

            # Location
            if home_address and isinstance(home_address, dict):
                city = home_address.get('city') or home_address.get('City') or ''
                country = home_address.get('country') or home_address.get('Country') or ''

                if city or country:
                    location = f"Location: {city}".strip()
                    if country:
                        location += f", {country}"
                    context_parts.append(location)

            # Languages
            if languages:
                lang_list = []
                if isinstance(languages, list):
                    lang_list = [lang for lang in languages if isinstance(lang, str) and lang]
                elif isinstance(languages, str):
                    lang_list = [languages]

                if lang_list:
                    context_parts.append("Languages: " + ", ".join(lang_list))

            if not context_parts:
                logger.warning("No context available from person_data for profile summary generation")
                logger.info(f"Available person_data keys: {list(person_data.keys())}")
                return {
                    "bio_bullets": "N/A",
                    "conversation_topics": ["Reference to conversation topics"]
                }

            context = "\n\n".join(context_parts)
            logger.info(f"Generated context for OpenAI:\n{context}")

            # Create prompts for OpenAI
            system_prompt = """You are an expert at creating professional executive profile summaries and conversation starters.
You must respond ONLY with valid JSON format.
IMPORTANT: Use ONLY the specific information provided. Do NOT use placeholders like [Current Position], [Company], etc.
If specific information is provided, use it exactly as given."""

            user_prompt = f"""Based on the following information, generate:
1. Exactly 4-5 concise professional bio bullet points that highlight the person's key qualifications, experience, and background
2. Exactly 3-5 potential conversation topics or starters that would be relevant for engaging with this person

{context}

CRITICAL INSTRUCTIONS:
1. Use ONLY the specific information provided above
2. Do NOT use placeholders like [Current Position], [Company], [Company 1], etc.
3. Each bullet should be a complete, specific statement
4. Conversation topics should be relevant to the person's background, industry, interests, or recent activities
5. Return your response as valid JSON with this exact structure:
{{
  "bio_bullets": [
    "bullet point 1",
    "bullet point 2",
    "bullet point 3",
    "bullet point 4"
  ],
  "conversation_topics": [
    "topic 1",
    "topic 2",
    "topic 3"
  ]
}}
6. Do NOT add any text before or after the JSON
7. Ensure the JSON is properly formatted and valid"""

            # Call OpenAI
            response = openai_client.chat.completions.create(
                model=secrets.get("GPT_MODEL_NAME"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # Lower temperature for more consistent, factual output
                max_tokens=800,
                response_format={"type": "json_object"}
            )

            result_content = response.choices[0].message.content or "{}"
            logger.info(f"Generated profile summary and topics:\n{result_content}")

            # Parse JSON response
            result = json.loads(result_content)

            # Validate and extract data
            bio_bullets_list = result.get("bio_bullets", [])
            conversation_topics_list = result.get("conversation_topics", [])

            # Convert bio bullets list to string format with "- " prefix
            if bio_bullets_list and isinstance(bio_bullets_list, list):
                bio_bullets_str = "\n".join([f"- {bullet}" for bullet in bio_bullets_list])
            else:
                bio_bullets_str = "N/A"

            # Ensure conversation topics is a list
            if not conversation_topics_list or not isinstance(conversation_topics_list, list):
                conversation_topics_list = ["Reference to conversation topics"]

            return {
                "bio_bullets": bio_bullets_str,
                "conversation_topics": conversation_topics_list
            }

        except Exception as e:
            logger.error(f"Error generating profile summary with OpenAI: {e}", exc_info=True)
            return {
                "bio_bullets": "N/A",
                "conversation_topics": ["Reference to conversation topics"]
            }

    def _generate_firm_relationships_with_openai(self, rra_relationships: Dict[str, Any], openai_client, secrets: Optional[Dict[str, Any]]) -> List[str]:
        """
        Generate Firm Relationships bullets using OpenAI based on relationship data.
        Creates one bullet per property in the relationships data.
        """
        if not openai_client or not secrets or not secrets.get("GPT_MODEL_NAME"):
            logger.warning("OpenAI client or GPT model not configured, returning default for firm_relationships")
            return ["No firm relationships data available"]

        if not rra_relationships or not isinstance(rra_relationships, dict):
            logger.warning("No relationships data available")
            return ["No firm relationships data available"]

        try:
            # Log available keys for debugging
            logger.info(f"relationships keys available: {list(rra_relationships.keys())}")

            # Build context from relationships properties
            context_parts = []

            # Iterate through all properties in relationships
            for key, value in rra_relationships.items():
                if value and value not in ["N/A", None, "", []]:
                    # Format the key to be more readable (convert camelCase to Title Case)
                    readable_key = ''.join([' ' + c if c.isupper() else c for c in key]).strip().title()

                    # Format the value appropriately
                    if isinstance(value, dict):
                        # For dict values, show key-value pairs
                        dict_items = [f"{k}: {v}" for k, v in value.items() if v not in ["N/A", None, ""]]
                        if dict_items:
                            context_parts.append(f"{readable_key}: {', '.join(dict_items)}")
                    elif isinstance(value, list):
                        # For list values, show count or items
                        if value:
                            if len(value) <= 5:
                                context_parts.append(f"{readable_key}: {', '.join([str(v) for v in value if v])}")
                            else:
                                context_parts.append(f"{readable_key}: {len(value)} items")
                    else:
                        # For simple values, show directly
                        context_parts.append(f"{readable_key}: {value}")

            if not context_parts:
                logger.warning("No valid data in relationships for relationship summary generation")
                return ["No firm relationships data available"]

            context = "\n".join(context_parts)
            logger.info(f"Generated context for Firm Relationships OpenAI:\n{context}")

            # Create prompts for OpenAI
            system_prompt = """You are an expert at summarizing firm relationship information.
Generate concise, professional bullet points based on the provided relationship data.
IMPORTANT: Use ONLY the specific information provided. Create one meaningful bullet point for each significant relationship aspect."""

            user_prompt = f"""Based on the following firm relationship information, generate 3-6 concise professional bullet points that highlight the key relationships and engagement history:

{context}

CRITICAL INSTRUCTIONS:
1. Use ONLY the specific information provided above
2. Each bullet should describe a distinct relationship aspect or metric
3. Focus on meaningful insights like strongest connections, relationship managers, assignments, etc.
4. Keep bullets concise and professional
5. Return EXACTLY 3-6 bullet points
6. Format as a simple list with "- " at the start of each line
7. Do NOT add any additional formatting, numbering, or explanation"""

            # Call OpenAI
            response = openai_client.chat.completions.create(
                model=secrets.get("GPT_MODEL_NAME"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            summary = response.choices[0].message.content or ""
            logger.info(f"Generated firm relationships summary:\n{summary}")

            # Split into individual bullets
            bullets = [
                line.strip().lstrip('- ').lstrip('• ').strip()
                for line in summary.split('\n')
                if line.strip() and line.strip() not in ['', '-', '•']
            ]

            # Ensure we have at least some content
            if not bullets:
                return ["No firm relationships data available"]

            return bullets

        except Exception as e:
            logger.error(f"Error generating firm relationships with OpenAI: {e}", exc_info=True)
            return ["No firm relationships data available"]

    def _generate_recent_assignments_from_ntlm(self, person_data: Dict[str, Any]) -> List[str]:
        """
        Generate recent assignments bullets from ntlm_overlay data.
        Extracts from currentEmployingCompanyInfo.currentCompanyAssignmentWorkHistories.currentCompanyAssignments
        and formats: positionTitle, projectLabel, leadConsultant, startDate, endDate
        """
        try:
            # Navigate to the assignments array
            current_company_info = person_data.get("currentEmployingCompanyInfo") or person_data.get("CurrentEmployingCompanyInfo") or {}

            if not isinstance(current_company_info, dict):
                logger.warning("currentEmployingCompanyInfo is not a dict")
                return ["Reference to completed search assignments"]

            work_histories = current_company_info.get("currentCompanyAssignmentWorkHistories") or current_company_info.get("CurrentCompanyAssignmentWorkHistories") or {}

            if not isinstance(work_histories, dict):
                logger.warning("currentCompanyAssignmentWorkHistories is not a dict")
                return ["Reference to completed search assignments"]

            assignments = work_histories.get("currentCompanyAssignments") or work_histories.get("CurrentCompanyAssignments") or []
            if not isinstance(assignments, list) or len(assignments) == 0:
                logger.warning(f"No currentCompanyAssignments found. Available keys in work_histories: {list(work_histories.keys())}, len assignments: {len(assignments)}")
                return ["Reference to completed search assignments"]

            logger.info(f"Found {len(assignments)} assignments in currentCompanyAssignments")

            # Format each assignment
            formatted_assignments = []
            for assignment in assignments:
                if not isinstance(assignment, dict):
                    continue

                # Extract fields with multiple possible names
                position_title = (
                    assignment.get("positionTitle") or
                    assignment.get("PositionTitle") or
                    assignment.get("position") or
                    ""
                )

                project_label = (
                    assignment.get("projectLabel") or
                    assignment.get("ProjectLabel") or
                    assignment.get("projectName") or
                    assignment.get("ProjectName") or
                    ""
                )

                lead_consultant = (
                    assignment.get("leadConsultant") or
                    assignment.get("LeadConsultant") or
                    ""
                )

                # Handle lead consultant if it's a dict (extract name)
                if isinstance(lead_consultant, dict):
                    lead_consultant = lead_consultant.get("name") or lead_consultant.get("Name") or ""
                elif isinstance(lead_consultant, list) and len(lead_consultant) > 0:
                    # If it's a list, take the first one
                    first_consultant = lead_consultant[0]
                    if isinstance(first_consultant, dict):
                        lead_consultant = first_consultant.get("name") or first_consultant.get("Name") or ""
                    else:
                        lead_consultant = str(first_consultant)

                start_date = (
                    assignment.get("startDate") or
                    assignment.get("StartDate") or
                    ""
                )

                end_date = (
                    assignment.get("endDate") or
                    assignment.get("EndDate") or
                    ""
                )

                # Format dates (from ISO format to MM/YYYY)
                def format_date(date_str):
                    if not date_str or date_str in ["N/A", None]:
                        return ""
                    try:
                        # Try to parse ISO format date
                        if "T" in str(date_str):
                            date_obj = datetime.strptime(str(date_str).split("T")[0], "%Y-%m-%d")
                        else:
                            date_obj = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
                        return date_obj.strftime("%m/%Y")
                    except Exception:
                        # If parsing fails, return as is
                        return str(date_str)[:7] if len(str(date_str)) >= 7 else str(date_str)

                formatted_start = format_date(start_date)
                formatted_end = format_date(end_date)

                # Build the assignment string
                # Format: "Position Title - Project Label; Lead Consultant; MM/YYYY - MM/YYYY"
                parts = []

                if position_title:
                    parts.append(position_title)

                if project_label:
                    if parts:
                        parts[-1] += f" - {project_label}"
                    else:
                        parts.append(project_label)

                if lead_consultant:
                    parts.append(lead_consultant)

                # Add date range
                if formatted_start or formatted_end:
                    date_range = f"{formatted_start or 'N/A'} - {formatted_end or 'Present'}"
                    parts.append(date_range)

                if parts:
                    assignment_str = "; ".join(parts)
                    formatted_assignments.append(assignment_str)
                    logger.info(f"Formatted assignment: {assignment_str}")

            if not formatted_assignments:
                logger.warning("No assignments could be formatted")
                return ["Reference to completed search assignments"]

            return formatted_assignments

        except Exception as e:
            logger.error(f"Error generating recent assignments from ntlm: {e}", exc_info=True)
            return ["Reference to completed search assignments"]

    def _generate_business_developments_from_ntlm(self, person_data: Dict[str, Any]) -> List[str]:
        """
        Generate business development bullets from ntlm_overlay data.
        Extracts from currentEmployingCompanyInfo.currentCompanyBusinessDevelopmentWorkHistories.businessDevelopments
        and formats: meetingTitle, meetingLabel, meetingDate
        """
        try:
            # Navigate to the business developments array
            current_company_info = person_data.get("currentEmployingCompanyInfo") or person_data.get("CurrentEmployingCompanyInfo") or {}

            if not isinstance(current_company_info, dict):
                logger.warning("currentEmployingCompanyInfo is not a dict")
                return ["Reference to completed pure consulting"]

            work_histories = current_company_info.get("currentCompanyBusinessDevelopmentWorkHistories") or current_company_info.get("CurrentCompanyBusinessDevelopmentWorkHistories") or {}

            if not isinstance(work_histories, dict):
                logger.warning("currentCompanyBusinessDevelopmentWorkHistories is not a dict")
                return ["Reference to completed pure consulting"]

            business_developments = work_histories.get("businessDevelopments") or work_histories.get("BusinessDevelopments") or []

            if not isinstance(business_developments, list) or len(business_developments) == 0:
                logger.warning(f"No businessDevelopments found. Available keys in work_histories: {list(work_histories.keys())}")
                return ["Reference to completed pure consulting"]

            logger.info(f"Found {len(business_developments)} business developments in businessDevelopments")

            # Format each business development
            formatted_developments = []
            for dev in business_developments:
                if not isinstance(dev, dict):
                    continue

                # Extract fields with multiple possible names
                meeting_title = (
                    dev.get("meetingTitle") or
                    dev.get("MeetingTitle") or
                    dev.get("title") or
                    dev.get("Title") or
                    ""
                )

                meeting_label = (
                    dev.get("meetingLabel") or
                    dev.get("MeetingLabel") or
                    dev.get("label") or
                    dev.get("Label") or
                    ""
                )

                meeting_date = (
                    dev.get("meetingDate") or
                    dev.get("MeetingDate") or
                    dev.get("date") or
                    dev.get("Date") or
                    ""
                )

                # Format date (from ISO format to MM/YYYY)
                def format_date(date_str):
                    if not date_str or date_str in ["N/A", None]:
                        return ""
                    try:
                        # Try to parse ISO format date
                        if "T" in str(date_str):
                            date_obj = datetime.strptime(str(date_str).split("T")[0], "%Y-%m-%d")
                        else:
                            date_obj = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
                        return date_obj.strftime("%m/%Y")
                    except Exception:
                        # If parsing fails, return as is
                        return str(date_str)[:7] if len(str(date_str)) >= 7 else str(date_str)

                formatted_date = format_date(meeting_date)

                # Build the business development string
                # Format: "Meeting Title - Meeting Label; MM/YYYY"
                parts = []

                if meeting_title:
                    parts.append(meeting_title)

                if meeting_label:
                    if parts:
                        parts[-1] += f" - {meeting_label}"
                    else:
                        parts.append(meeting_label)

                if formatted_date:
                    parts.append(formatted_date)

                if parts:
                    development_str = "; ".join(parts)
                    formatted_developments.append(development_str)
                    logger.info(f"Formatted business development: {development_str}")

            if not formatted_developments:
                logger.warning("No business developments could be formatted")
                return ["Reference to completed pure consulting"]

            return formatted_developments

        except Exception as e:
            logger.error(f"Error generating business developments from ntlm: {e}", exc_info=True)
            return ["Reference to completed pure consulting"]

    def get_smartpack_config(self, person_name: str, INTENTS_CONFIG: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get smartpack configuration for a person (adapted from person.py).
        """
        if not INTENTS_CONFIG:
            logger.warning("Intents configuration not loaded")
            return {}

        try:
            cfg = INTENTS_CONFIG.get("personSmartpack", {})
            indexes = cfg.get("indexes", cfg.get("index", []))
            search_field = cfg.get("search_field", DEFAULT_PERSON_FIELD)
            size = cfg.get("size", 10)
            source_fields = cfg.get("source", [
                "Overview", "EmploymentHistory", "CurrentEmployingCompanyInfo", "RRAWorkAndFinancialHistoryAggregates"
            ])

            # Basic query (match_phrase)
            query_body = {
                "query": {
                    "bool": {
                        "must": [
                            {"match_phrase": {search_field: person_name}}
                        ]
                    }
                },
                "size": size,
                "_source": source_fields
            }

            return {
                "indexes": indexes,
                "body": query_body,
                "search_field": search_field,
                "size": size,
                "source": source_fields
            }
        except Exception as e:
            logger.error(f"Error building smartpack config for person: {e}")
            return {}

    def generate_summary(self, es_response: Dict[str, Any], person_name: str, openai_client = None, secrets: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a person summary from the ES response (adapted from person.py).
        Returns a formatted text report with tables, preserving all JSON summary sections.
        """
        try:
            hits = es_response.get("hits", {}).get("hits", [])

            if not hits:
                return {
                    "person_name": person_name,
                    "found": False,
                    "message": "No person data found",
                    "result_count": 0
                }

            person_data = hits[0].get("_source", {})
            person_id = self._extract_person_id(person_data)
            ntlm_overlay = self._fetch_ntlm_overlay(person_id, secrets, "person")
            person_data = self._merge_overlay(person_data, ntlm_overlay)
            
            current_company_info = self._safe_dict(person_data.get("currentEmployingCompanyInfo"))
            current_company_name = current_company_info.get("companyName", "N/A") if isinstance(current_company_info.get("companyName", "N/A"), str) else "N/A"
            current_company_id = current_company_info.get("companyID") if isinstance(current_company_info.get("companyID", "N/A"), str) else "N/A"

            ntlm_overlay = self._fetch_ntlm_overlay(current_company_id, secrets, "company")
            person_data = self._merge_overlay(person_data, ntlm_overlay)

            employment_history = self._safe_list(person_data.get("EmploymentHistory"))
            rra_relationships = self._safe_dict(person_data.get("rraRelationships"))

            # Safe extraction of assignment work histories
            assignment_work_histories = []
            if (
                "rraRelationships" in person_data
                and "personAssignmentWorkHistory" in person_data["rraRelationships"]
                and "assignmentWorkHistories" in person_data["rraRelationships"]["personAssignmentWorkHistory"]
            ):
                assignment_work_histories = person_data["rraRelationships"]["personAssignmentWorkHistory"]["assignmentWorkHistories"]

            roles = assignment_work_histories if isinstance(assignment_work_histories, list) else []
            counts = Counter(obj.get("updateDate", "")[:4] for obj in roles if isinstance(obj, dict) and obj.get("updateDate"))

            current_title = "N/A"
            for item in employment_history:
                if not isinstance(item, dict):
                    continue
                try:
                    if item.get("CompanyName") == current_company_name and item.get("IsCurrentJob"):
                        title_candidate = item.get("JobTitle")
                        if title_candidate:
                            current_title = title_candidate
                            break
                except Exception:
                    continue

            # ------------------------------------------------------------------
            # JSON Summary (DO NOT MODIFY STRUCTURE OR KEYS)
            # ------------------------------------------------------------------
            summary = {
                "person_name": (
                    person_data["Overview"]["FullName"]
                    if "Overview" in person_data and "FullName" in person_data["Overview"]
                    else person_name
                ),
                "basic_info": {
                    "title": current_title,
                    "company": current_company_name,
                    "profile_summary": ( person_data["bioSummary"] if "bioSummary" in person_data else "N/A"),
                    "profile_photo": "N/A"
                },
                "RRA_#_of_assignments/revenue": {
                    "assignments/revenue_table": person_data["rraRevenueHistoryAggregates"] if "rraRevenueHistoryAggregates" in person_data else "N/A"
                },
                "RRA_relationships": {
                    "strongest_connection":(
                        rra_relationships.get("strongestRelationPersonName", "N/A")
                        if "rraRelationships" in person_data
                        else "N/A"
                    ),
                    "relationship_managers": (
                       rra_relationships.get("currentEmployingCompanyRelationsManager", "N/A")
                        if "rraRelationships" in person_data
                        else "N/A"
                    ),
                    "open_assignments_with_current_company": {
                        "search": len(
                            [
                                item for item in assignment_work_histories
                                if isinstance(item, dict)
                                and item.get("ProjectStatus") == "Open"
                                and item.get("assignmentType") == "Full Search"
                            ]
                        ) if assignment_work_histories else 0,
                        "consulting": len(
                            [
                                item for item in assignment_work_histories
                                if isinstance(item, dict)
                                and item.get("ProjectStatus") == "Open"
                                and item.get("assignmentType") == "Consulting"
                            ]
                        ) if assignment_work_histories else 0
                    },
                    "role_history": [{"year": int(year), "count": count} for year, count in counts.items()] if counts else [],
                    "lead_consultants_on_RRA_projects": (
                        # Flatten list of lists and extract consultant names
                        [
                            consultant.get("name", "Unknown") if isinstance(consultant, dict) else str(consultant)
                            for item in assignment_work_histories
                            if isinstance(item, dict)
                            for consultant in (item.get("leadConsultants", []) if isinstance(item.get("leadConsultants"), list) else [])
                        ]
                        if assignment_work_histories
                        else []
                    ),
                },
                "recent/marquee_assignments_for_company": {
                    "search_assignments": [
                        item.get("atsStagingRole", "") + " - " + item.get("HiringJobTitle", "") + "; " + item.get("HiringCompany", "") + "; " + (item.get("leadConsultants", [])[0].get("name", "") if item.get("leadConsultants") and len(item.get("leadConsultants", [])) > 0 else "")
                        for item in assignment_work_histories
                        if isinstance(item, dict) and item.get("projectStatus") == "Completed" and item.get("assignmentType") == "Full Search"
                    ] if assignment_work_histories else [],
                    "pure_consulting": [
                        item.get("atsStagingRole", "") + " - " + item.get("HiringJobTitle", "") + "; " + item.get("HiringCompany", "") + "; " + (item.get("leadConsultants", [])[0].get("name", "") if item.get("leadConsultants") and len(item.get("leadConsultants", [])) > 0 else "")
                        for item in assignment_work_histories
                        if isinstance(item, dict) and item.get("projectStatus") == "Completed" and item.get("assignmentType") == "Consulting"
                    ] if assignment_work_histories else [],
                    "open_assignments": {
                        "search": len(
                            [item for item in assignment_work_histories
                            if isinstance(item, dict) and item.get("projectStatus") == "Open" and item.get("assignmentType") == "Full Search"]
                        ) if assignment_work_histories else 0,
                        "pure_consulting": len(
                            [item for item in assignment_work_histories
                            if isinstance(item, dict) and item.get("projectStatus") == "Open" and item.get("assignmentType") == "Consulting"]
                        ) if assignment_work_histories else 0,
                    }
                },
                "current_board": {
                    "board/leadershipt_team_analysis": person_data.get("board", "N/A")
                },
                "most_recent_executive_hires": {
                    "most_recent_executive_hires": (
                        max([x for x in person_data.get("leadership", {}).get("executiveLeadership", [])
                        if isinstance(x, dict) and "startDate" in x and x["startDate"] not in (None, "")],
                        key=lambda x:datetime.strptime(x["startDate"], "%Y-%m-%dT%H:%M:%S"))
                        if person_data.get("leadership", {}).get("executiveLeadership")
                        and any(isinstance(x, dict) and "startDate" in x and x["startDate"] not in (None, "")
                                for x in person_data.get("leadership", {}).get("executiveLeadership", []))
                        else "N/A"
                    )
                }
            }

            # Generate PDF using generate_pdf_person from smartpack_generator
            try:
                # ------------------------------------------------------------------
                # Load mapper and transform summary to pdf_content using configuration
                # ------------------------------------------------------------------
                mapper = load_mapper("person")

                # Build pdf_content using configuration-based mapping
                basic_info = summary.get("basic_info", {})
                # Generate profile_summary and conversation topics using OpenAI based on ntlm_overlay data
                openai_result = self._generate_profile_summary_with_openai(person_data, openai_client, secrets)

                # Extract bio bullets from OpenAI result
                profile_summary = openai_result.get("bio_bullets", "N/A")
                conversation_topics = openai_result.get("conversation_topics", ["Reference to conversation topics"])

                # Convert profile_summary string to list of individual bullets
                if profile_summary not in ["N/A", None, ""]:
                    # Split by newlines and clean up each bullet
                    bio_bullets = [
                        line.strip().lstrip('- ').lstrip('• ').strip()
                        for line in profile_summary.split('\n')
                        if line.strip() and line.strip() not in ['', '-', '•']
                    ]
                    # Fallback if no valid bullets found
                    if not bio_bullets:
                        bio_bullets = ["Reference to bio bullets"]
                else:
                    bio_bullets = ["Reference to bio bullets"]

                # Generate firm relationships bullets using OpenAI based on relationship data
                rra_relationships_data = person_data.get("rraRelationships", {})
                rra_bullets = self._generate_firm_relationships_with_openai(rra_relationships_data, openai_client, secrets)

                # Generate recent assignments bullets from ntlm_overlay data
                search_completed_bullets = self._generate_recent_assignments_from_ntlm(person_data)

                # Generate business developments bullets from ntlm_overlay data
                pure_consulting_bullets = self._generate_business_developments_from_ntlm(person_data)

                pdf_content = {
                    "title": summary.get("person_name", person_name),
                    "subtitle": basic_info.get("title", "N/A"),
                    "company": basic_info.get("company"),
                    "bio_bullets": bio_bullets,
                    "ra_assignments_revenue": {
                        "title": "Firm # of Assignments/Revenue",
                        "header": ["Year", "Revenue"],
                        "rows": mapper.build_assignments_revenue_table(summary)
                    },
                    "rra_relationships": {
                        "title": "Firm Relationships",
                        "summary_lines": rra_bullets
                    },
                    "recent_marquee_assignments": {
                        "title": "Recent / Marquee Assignments",
                        "search_completed": search_completed_bullets,
                        "pure_consulting_completed": pure_consulting_bullets,
                        "open_assignments": mapper.build_open_assignments_dict(summary)
                    },
                    "current_board_back": {
                        "title": "Current Board",
                        "board_leadership_team_analysis": {
                            "title": "Board / Leadership Team Analysis",
                            "headers": ["Category", "Value", "Notes", "Details", "Status"],
                            "rows": [
                                mapper.build_open_assignments_dict(summary)
                            ],
                            "footnote": "Note: Data to be populated from board analysis"
                        },
                        "most_recent_executive_hires": {
                            "title": "Most Recent Executive Hires",
                            "items": mapper.build_most_recent_hires(summary)
                        },
                        "recent_company_news": {
                            "title": "Recent Company News",
                            "items": [
                                "Reference to recent company news"
                            ]
                        },
                        "potential_conversation_topics": {
                            "title": "Potential Topics / Conversation Starters",
                            "items": conversation_topics
                        }
                    },
                    "executive_directors": {
                        "header": ["Name", "Position", "Tenure", "Background", "Notes"],
                        "rows": [
                            ["Reference", "Executive", "Directors", "Data", "Here"]
                        ]
                    },
                    "supervisory_directors": {
                        "header": ["Name", "Position", "Tenure", "Background", "Notes"],
                        "rows": [
                            ["Reference", "Supervisory", "Directors", "Data", "Here"]
                        ]
                    }
                }

                # Sanitize person name for filename
                safe_person_name = "".join(c for c in person_name if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_person_name = safe_person_name.replace(' ', '_')

                # Generate PDF in the smartpackPdfMapping/generated_pdfs directory
                current_dir = os.path.dirname(os.path.abspath(__file__))
                parent_dir = os.path.dirname(current_dir)
                output_dir = os.path.join(parent_dir, "smartpackPdfMapping", "generated_pdfs")
                os.makedirs(output_dir, exist_ok=True)

                pdf_path = os.path.join(output_dir, f"{safe_person_name}_smartpack.pdf")

                # Call generate_pdf_person
                generate_pdf_person(pdf_content, pdf_path)

                logger.info(f"Person SmartPack PDF generated locally: {pdf_path}")

                # Upload PDF to Azure Storage
                upload_result = upload_pdf_to_storage(
                    pdf_path=pdf_path,
                    blob_name=f"person/{os.path.basename(pdf_path)}"
                )

                # Get server base URL for download endpoints
                from mcp_app import SECRETS
                server_base_url = SECRETS.get("SERVER_BASE_URL")

                if upload_result.get("success"):
                    logger.info(f"Person SmartPack PDF uploaded to Azure Storage: {upload_result['blob_url']}")
                    #summary["pdf_path"] = pdf_path
                    #summary["pdf_blob_url"] = upload_result["blob_url"]
                    #summary["pdf_blob_name"] = upload_result["blob_name"]
                    #summary["pdf_container"] = upload_result["container_name"]

                    # Add smartpack_url for downloading through the server (as proxy to Azure Storage)
                    summary["smartpack_url"] = f"{server_base_url}/api/download-pdf-storage/{upload_result['blob_name']}"
                    # Also provide local download URL as fallback
                    #summary["smartpack_url_local"] = f"{server_base_url}/api/download-pdf-local/{os.path.basename(pdf_path)}"
                else:
                    logger.warning(f"Failed to upload PDF to Azure Storage: {upload_result.get('error')}")
                    #summary["pdf_path"] = pdf_path
                    summary["pdf_upload_error"] = upload_result.get("error")

                    # If upload failed, provide only local download URL
                    summary["smartpack_url"] = f"{server_base_url}/api/download-pdf-local/{os.path.basename(pdf_path)}"

                return summary

            except Exception as pdf_error:
                logger.error(f"Error generating PDF for person {person_name}: {pdf_error}")
                # Return summary even if PDF generation fails
                logger.info(f"Person summary generated for: {person_name}")
                return summary

        except Exception as e:
            logger.error(f"Error generating person summary: {e}")
            return {
                "person_name": person_name,
                "found": False,
                "message": f"Error processing person data: {str(e)}",
                "result_count": 0
            }
