"""
Configuration-based mapper for transforming summary data to PDF content.

This module provides functionality to map data from Elasticsearch/API responses
to PDF content structure using external JSON configuration files with path-based mappings.
"""

import json
import logging
import os
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)


class ConfigMapper:
    """
    Handles configuration-based mapping using JSON path notation.

    The mapper reads JSON configuration files that define how to transform
    data from a source structure (summary) to a target structure (pdf_content).
    """

    def __init__(self, config_path: str):
        """
        Initialize the mapper with a configuration file.

        Args:
            config_path: Path to the JSON configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load the JSON configuration file."""
        try:
            if not os.path.exists(self.config_path):
                logger.error(f"Configuration file not found: {self.config_path}")
                return {}

            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"Configuration loaded from: {self.config_path}")
                return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {}

    def get_value_by_path(self, data: Dict[str, Any], path: str, default: Any = "N/A") -> Any:
        """
        Retrieve a value from nested dictionary using dot notation path.

        Args:
            data: Source data dictionary (typically the summary object)
            path: Dot-separated path (e.g., "key_information.Entity Type")
            default: Default value if path not found

        Returns:
            The value at the specified path, or default if not found
        """
        try:
            keys = path.split('.')
            value = data

            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                    if value is None:
                        return default
                else:
                    return default

            return value if value is not None else default
        except Exception as e:
            logger.warning(f"Error getting value for path '{path}': {e}")
            return default

    def resolve_template(self, template: str, summary: Dict[str, Any]) -> str:
        """
        Resolve a template string with {{path}} placeholders.

        Args:
            template: Template string like "{{summary.company_name}}"
            summary: Source data dictionary

        Returns:
            Resolved string with values replaced
        """
        if not isinstance(template, str):
            return template

        # Find all {{...}} patterns
        import re
        pattern = r'\{\{(.+?)\}\}'

        def replace_match(match):
            path = match.group(1).strip()
            # Remove 'summary.' prefix if present
            if path.startswith('summary.'):
                path = path[8:]

            value = self.get_value_by_path(summary, path)
            return str(value)

        result = re.sub(pattern, replace_match, template)
        return result

    def apply_mapping(self, summary: Dict[str, Any], mapping_section: str = "pdf_content_mappings") -> Dict[str, Any]:
        """
        Apply the configuration mapping to transform summary to pdf_content.

        Args:
            summary: Source data (the summary object from Elasticsearch/API)
            mapping_section: Section in config to use for mapping

        Returns:
            Transformed data structure (pdf_content)
        """
        if not self.config or mapping_section not in self.config:
            logger.warning(f"No mapping configuration found for section: {mapping_section}")
            return {}

        mappings = self.config[mapping_section]
        return self._apply_mappings_recursive(mappings, summary)

    def _apply_mappings_recursive(self, mappings: Any, summary: Dict[str, Any]) -> Any:
        """
        Recursively apply mappings to nested structures.

        Args:
            mappings: Mapping configuration (can be dict, list, or template string)
            summary: Source data

        Returns:
            Transformed data
        """
        if isinstance(mappings, dict):
            result = {}
            for key, value in mappings.items():
                result[key] = self._apply_mappings_recursive(value, summary)
            return result

        elif isinstance(mappings, list):
            return [self._apply_mappings_recursive(item, summary) for item in mappings]

        elif isinstance(mappings, str):
            # Check if it's a template string
            if '{{' in mappings and '}}' in mappings:
                return self.resolve_template(mappings, summary)
            else:
                return mappings

        else:
            return mappings

    def get_list_mapping(self, summary: Dict[str, Any], config_key: str) -> List[Any]:
        """
        Get a list mapping from configuration.

        Args:
            summary: Source data
            config_key: Key in configuration for the list mapping

        Returns:
            List of mapped items
        """
        if not self.config or config_key not in self.config:
            return []

        list_config = self.config[config_key]
        source_path = list_config.get("source_path", "")
        item_mapping = list_config.get("item_mapping", {})

        # Get source list
        source_list = self.get_value_by_path(summary, source_path, [])

        if not isinstance(source_list, list):
            return []

        # Map each item
        result = []
        for item in source_list:
            if isinstance(item, dict):
                mapped_item = {}
                for target_key, source_key in item_mapping.items():
                    if isinstance(source_key, str) and source_key.startswith("item."):
                        # Extract from current item
                        item_path = source_key[5:]  # Remove "item."
                        mapped_item[target_key] = self.get_value_by_path(item, item_path, "N/A")
                    else:
                        mapped_item[target_key] = source_key
                result.append(mapped_item)
            else:
                result.append(item)

        return result


    def format_currency(self, value: Any) -> str:
        """
        Format a value as currency if it's a number.

        Args:
            value: Value to format (can be int, float, or string)

        Returns:
            Formatted currency string (e.g., "$1,234,567.89" or "USD 1,234,567")
        """
        if value is None or value == "N/A" or value == "":
            return "N/A"

        # Try to extract numeric value
        try:
            # If it's already a number
            if isinstance(value, (int, float)):
                num = float(value)
            # If it's a string, try to parse it
            elif isinstance(value, str):
                # Remove common currency symbols and separators
                cleaned = value.replace("$", "").replace("€", "").replace("£", "").replace(",", "").replace(" ", "").strip()
                if not cleaned or cleaned == "N/A":
                    return str(value)
                num = float(cleaned)
            else:
                return str(value)

            # Format with thousand separators
            if num >= 1_000_000_000:  # Billions
                formatted = f"${num:,.0f}"
            elif num >= 1_000_000:  # Millions
                formatted = f"${num:,.0f}"
            else:
                formatted = f"${num:,.2f}"

            return formatted

        except (ValueError, TypeError):
            # If conversion fails, return as-is
            return str(value)

    def build_table_entries(self, summary: Dict[str, Any], entries_config: List[Dict]) -> List[tuple]:
        """
        Build table entries as list of tuples (label, value).

        Args:
            summary: Source data
            entries_config: List of entry configurations with 'label' and 'path'

        Returns:
            List of tuples (label, value)
        """
        result = []
        for entry in entries_config:
            label = entry.get("label", "")
            path = entry.get("path", "")
            format_type = entry.get("format", None)  # Optional format type

            value = self.get_value_by_path(summary, path, "N/A")

            # Apply formatting if specified
            if format_type == "currency":
                value = self.format_currency(value)
            else:
                value = str(value)

            result.append((label, value))
        return result

    def build_list_items(self, summary: Dict[str, Any], config: Dict[str, Any]) -> List[Any]:
        """
        Build list items from configuration.

        Args:
            summary: Source data
            config: Configuration with 'source' and optional 'default'

        Returns:
            List of items
        """
        source_path = config.get("source", "")
        default = config.get("default", [])

        value = self.get_value_by_path(summary, source_path)

        # Handle special cases
        if value == "N/A" or value is None or value == "":
            return default if isinstance(default, list) else [default]

        if isinstance(value, list):
            return value if len(value) > 0 else default
        else:
            return [str(value)]

    def format_investment_strategy_bullets(self, summary: Dict[str, Any]) -> str:
        """
        Format investment strategy as bullet list.

        Args:
            summary: Source data

        Returns:
            Formatted bullet list string
        """
        investment_strategy = self.get_value_by_path(summary, "investment_strategy", {})

        if not isinstance(investment_strategy, dict):
            return "N/A"

        bullets = []
        for key, value in investment_strategy.items():
            if value and str(value) != "N/A":
                bullets.append(f"• {key}: {value}")

        return "\n".join(bullets) if bullets else "N/A"

    def build_news_items(self, summary: Dict[str, Any]) -> List[tuple]:
        """
        Build news items as list of tuples (headline, summary).

        Args:
            summary: Source data

        Returns:
            List of tuples (headline, summary)
        """
        news_data = self.get_value_by_path(summary, "news", [])

        if not isinstance(news_data, list) or len(news_data) == 0:
            return [("Reference", "News entries")]

        if isinstance(news_data[0], dict):
            return [
                (item.get("headline", "No headline"), item.get("summary", "No summary"))
                for item in news_data
            ]
        else:
            return [("Reference", "News entries")]

    def build_leadership_rows(self, summary: Dict[str, Any], max_bio_length: int = 1000) -> List[tuple]:
        """
        Build leadership team rows as list of tuples (name, (title, biography)).

        Args:
            summary: Source data
            max_bio_length: Maximum length for biographies

        Returns:
            List of tuples
        """
        leadership_data = self.get_value_by_path(summary, "leadership.board_members", [])

        if not isinstance(leadership_data, list) or len(leadership_data) == 0:
            return [("Reference", ("Leadership Team", "Members"))]

        rows = []
        for leader in leadership_data:
            if isinstance(leader, dict):
                name = leader.get("MemberName", "N/A")
                title = leader.get("BoardRole", "N/A")
                biography = leader.get("LinkedInURL", "")
                # Truncate long biographies
                if isinstance(biography, str) and len(biography) > max_bio_length:
                    biography = self.truncate_long_text(biography, max_bio_length)
                rows.append((name, (title, biography)))
            else:
                rows.append((str(leader), ("N/A", "")))

        return rows if rows else [("Reference", ("Leadership Team", "Members"))]

    def build_board_rows(self, summary: Dict[str, Any]) -> List[List[str]]:
        """
        Build board of directors rows as list of lists [name, title].
        Names and titles are formatted in bold using HTML tags.

        Args:
            summary: Source data

        Returns:
            List of lists with bold-formatted text
        """
        board_data = self.get_value_by_path(summary, "leadership.executives", [])

        if not isinstance(board_data, list) or len(board_data) == 0:
            return [["Reference", "Board Members"]]

        rows = []
        for member in board_data:
            if isinstance(member, dict):
                name = member.get("ExecutiveName", "N/A")
                title = member.get("ExecutiveRole", "N/A")
                # Wrap in bold tags for PDF rendering
                rows.append([f"<b>{name}</b>", f"<b>{title}</b>"])
            else:
                rows.append([f"<b>{str(member)}</b>", "<b>N/A</b>"])

        return rows if rows else [["Reference", "Board Members"]]

    def build_assignments_revenue_table(self, summary: Dict[str, Any]) -> List[List[str]]:
        """
        Build firm assignments/revenue table rows.

        Args:
            summary: Source data

        Returns:
            List of lists with [year, revenue]
        """
        table_data = self.get_value_by_path(summary, "RRA_#_of_assignments/revenue.assignments/revenue_table", [])

        if not isinstance(table_data, list) or len(table_data) == 0 or table_data == "N/A":
            return [["Year", "Revenue"]]

        rows = []
        for item in table_data:
            if isinstance(item, dict):
                rows.append([
                    str(item.get("year", "N/A")),
                    "$ " + str(item.get("amount", "N/A"))
                ])

        return rows if rows else [["Year", "Revenue"]]

    def build_firm_relationships_summary(self, summary: Dict[str, Any]) -> List[str]:
        """
        Build firm relationships summary lines.

        Args:
            summary: Source data

        Returns:
            List of formatted summary lines
        """
        rra_rel = self.get_value_by_path(summary, "RRA_relationships", {})

        if not isinstance(rra_rel, dict):
            return ["Reference to RRA relationships"]

        lines = []
        lines.append(f"Strongest Connection: {rra_rel.get('strongest_connection', 'N/A')}")
        lines.append(f"Relationship Managers: {rra_rel.get('relationship_managers', 'N/A')}")

        open_assignments = rra_rel.get('open_assignments_with_current_company', {})
        if isinstance(open_assignments, dict):
            lines.append(f"Open Search Assignments: {open_assignments.get('search', 0)}")
            lines.append(f"Open Consulting Assignments: {open_assignments.get('consulting', 0)}")

        return lines

    def build_lead_consultants_list(self, summary: Dict[str, Any]) -> List[str]:
        """
        Build list of lead consultants.

        Args:
            summary: Source data

        Returns:
            List of consultant names
        """
        consultants = self.get_value_by_path(summary, "RRA_relationships.lead_consultants_on_RRA_projects", [])

        if not isinstance(consultants, list) or len(consultants) == 0:
            return ["Reference to lead consultants"]

        return consultants

    def build_recent_assignments(self, summary: Dict[str, Any], assignment_type: str) -> List[str]:
        """
        Build list of recent assignments (search or consulting).

        Args:
            summary: Source data
            assignment_type: "search_assignments" or "pure_consulting"

        Returns:
            List of assignment descriptions
        """
        assignments = self.get_value_by_path(summary, f"recent/marquee_assignments_for_company.{assignment_type}", [])

        if not isinstance(assignments, list) or len(assignments) == 0:
            default_msg = f"Reference to completed {assignment_type.replace('_', ' ')}"
            return [default_msg]

        return assignments

    def build_open_assignments_dict(self, summary: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Build open assignments dictionary.

        Args:
            summary: Source data

        Returns:
            Dictionary with Search and Consulting lists
        """
        open_assignments = self.get_value_by_path(summary, "recent/marquee_assignments_for_company.open_assignments", {})

        if not isinstance(open_assignments, dict):
            return {
                "Search": ["0 open search assignments"],
                "Consulting": ["0 open consulting assignments"]
            }

        search_count = open_assignments.get('search', 0)
        consulting_count = open_assignments.get('pure_consulting', 0)

        return {
            "Search": [f"{search_count} open search assignments"],
            "Consulting": [f"{consulting_count} open consulting assignments"]
        }

    def build_most_recent_hires(self, summary: Dict[str, Any]) -> List[str]:
        """
        Build most recent executive hires list.

        Args:
            summary: Source data

        Returns:
            List with hire information
        """
        hire_data = self.get_value_by_path(summary, "most_recent_executive_hires.most_recent_executive_hires", "N/A")

        if hire_data == "N/A" or not hire_data:
            return ["Reference to recent hires"]

        return [str(hire_data)]

    def truncate_long_text(self, text: str, max_length: int = 2000) -> str:
        """
        Truncate long text to prevent PDF rendering issues.

        Args:
            summary: Source data
            max_length: Maximum character length (default 2000)

        Returns:
            Truncated text with ellipsis if needed
        """
        if not isinstance(text, str):
            text = str(text)

        if len(text) <= max_length:
            return text

        # Truncate and add ellipsis
        return text[:max_length] + "...\n\n[Content truncated due to length. See full data in source system.]"

    def format_date(self, date_str: str) -> str:
        """
        Format a date string to a readable format.

        Args:
            date_str: Date string (e.g., "2022-12-08T00:00:00-05:00")

        Returns:
            Formatted date string (e.g., "Dec 8, 2022")
        """
        if not date_str or date_str in ["null", "N/A", "", None]:
            return "N/A"

        try:
            from datetime import datetime
            # Parse ISO format date
            if "T" in str(date_str):
                # Remove timezone info for parsing
                date_part = str(date_str).split("T")[0]
                dt = datetime.strptime(date_part, "%Y-%m-%d")
            else:
                dt = datetime.strptime(str(date_str), "%Y-%m-%d")

            # Format as "Month Day, Year"
            return dt.strftime("%b %d, %Y")
        except Exception as e:
            logger.warning(f"Error formatting date '{date_str}': {e}")
            return str(date_str)

    def build_rra_assignments_list(self, summary: Dict[str, Any], max_items: int = 50) -> str:
        """
        Build a formatted list of firm assignments from array of objects.

        Args:
            summary: Source data
            max_items: Maximum number of assignments to include

        Returns:
            Formatted assignments text
        """
        rra_data = self.get_value_by_path(
            summary,
            "assignments_with_rra.RRA History – Assignments and PNBs in last 3 years",
            []
        )

        # Handle case where data is already a string
        if isinstance(rra_data, str):
            return self.truncate_long_text(rra_data, max_length=2000)

        # Handle case where data is not a list
        if not isinstance(rra_data, list):
            return "N/A"

        if len(rra_data) == 0:
            return "No assignments found"

        # Build formatted list
        lines = []
        for i, assignment in enumerate(rra_data[:max_items]):
            if not isinstance(assignment, dict):
                continue

            project_type = assignment.get("projectType", "N/A")
            project_id = assignment.get("projectID", assignment.get("projectLabel", "N/A"))
            position_title = assignment.get("positionTitle", "N/A")
            lead_consultant = assignment.get("leadConsultant", "N/A")
            start_date = self.format_date(assignment.get("startDate", ""))
            end_date = self.format_date(assignment.get("endDate", ""))

            # Format each assignment entry
            entry = (
                f"• {position_title}\n"
                f"  Type: {project_type} | ID: {project_id}\n"
                f"  Lead: {lead_consultant}\n"
                f"  Period: {start_date} - {end_date}\n"
            )
            lines.append(entry)

        result = "\n".join(lines)

        # Add note if truncated
        if len(rra_data) > max_items:
            result += f"\n\n[Showing {max_items} of {len(rra_data)} assignments]"

        return result

    def build_rra_history(self, summary: Dict[str, Any], max_length: int = 2000) -> str:
        """
        Build RRA History text with length limits to prevent PDF overflow.
        Now uses formatted assignment list instead of raw JSON.

        Args:
            summary: Source data
            max_length: Maximum character length (applied after formatting)

        Returns:
            Formatted RRA history text
        """
        # Use the new formatted list function
        formatted_text = self.build_rra_assignments_list(summary, max_items=50)

        # Truncate if still too long
        return self.truncate_long_text(formatted_text, max_length=max_length)

    def build_rra_assignments_table(self, summary: Dict[str, Any], max_items: int = 50) -> list:
        """
        Build RRA assignments as a list of tuples for table display.
        Each tuple contains (leadConsultant, assignment_details).

        Args:
            summary: Source data
            max_items: Maximum number of assignments to include

        Returns:
            List of tuples (leadConsultant, assignment_details)
        """
        rra_data = self.get_value_by_path(
            summary,
            "assignments_with_rra.RRA History – Assignments and PNBs in last 3 years",
            []
        )

        # Handle case where data is already a string or not a list
        if not isinstance(rra_data, list):
            return [("N/A", "No assignments data available")]

        if len(rra_data) == 0:
            return [("N/A", "No assignments found")]

        # Build list of tuples
        table_rows = []
        for assignment in rra_data[:max_items]:
            if not isinstance(assignment, dict):
                continue

            # Extract fields
            lead_consultant = assignment.get("leadConsultant", "N/A")
            position_title = assignment.get("positionTitle", "N/A")
            project_type = assignment.get("projectType", "N/A")
            project_id = assignment.get("projectID", assignment.get("projectLabel", "N/A"))
            start_date = self.format_date(assignment.get("startDate", ""))
            end_date = self.format_date(assignment.get("endDate", ""))

            # Build the right side content with positionTitle in bold
            right_content = (
                f"<b>{position_title}</b><br/>"
                f"Type: {project_type} | ID: {project_id}<br/>"
                f"Period: {start_date} - {end_date}"
            )

            # Add tuple (leadConsultant will be bolded automatically by the PDF generator)
            table_rows.append((lead_consultant, right_content))

        return table_rows

    def get_value_truncated(self, summary: Dict[str, Any], path: str, default: str = "N/A", max_length: int = 1500) -> str:
        """
        Get a value by path and truncate if too long.

        Args:
            summary: Source data
            path: Dot notation path
            default: Default value if not found
            max_length: Maximum character length

        Returns:
            Value as string, truncated if needed
        """
        value = self.get_value_by_path(summary, path, default)
        text = str(value)
        return self.truncate_long_text(text, max_length=max_length)


def load_mapper(entity_type: str) -> ConfigMapper:
    """
    Load a mapper for the specified entity type (company or person).

    Args:
        entity_type: Type of entity ("company" or "person")

    Returns:
        ConfigMapper instance
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(current_dir, "mapping_configs")
    config_path = os.path.join(config_dir, f"{entity_type}_mapping.json")

    return ConfigMapper(config_path)
