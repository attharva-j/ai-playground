"""Chart generation using Plotly."""
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, List, Optional
import pandas as pd


class ChartGenerator:
    """Generate interactive charts using Plotly."""
    
    @staticmethod
    def generate_chart(
        data: Dict[str, Any],
        viz_config: Dict[str, Any],
    ) -> Optional[go.Figure]:
        """
        Generate a chart based on the data and visualization configuration.
        
        Args:
            data: The data to visualize
            viz_config: Configuration including chart_type, x_field, y_field, title
            
        Returns:
            A Plotly figure object or None if table view
        """
        chart_type = viz_config.get("chart_type", "table")
        
        if chart_type == "table":
            return None
        
        # Extract the actual data list from the nested structure
        data_list = ChartGenerator._extract_data_list(data)
        
        if not data_list:
            print("⚠️  No data to visualize")
            return None
        
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(data_list)
        
        x_field = viz_config.get("x_field")
        y_field = viz_config.get("y_field")
        title = viz_config.get("title", "Data Visualization")
        
        try:
            if chart_type == "bar":
                return ChartGenerator._create_bar_chart(df, x_field, y_field, title)
            elif chart_type == "line":
                return ChartGenerator._create_line_chart(df, x_field, y_field, title)
            elif chart_type == "pie":
                return ChartGenerator._create_pie_chart(df, x_field, y_field, title)
            elif chart_type == "scatter":
                return ChartGenerator._create_scatter_chart(df, x_field, y_field, title)
            elif chart_type == "histogram":
                return ChartGenerator._create_histogram(df, x_field, title)
            else:
                print(f"⚠️  Unknown chart type: {chart_type}")
                return None
        except Exception as e:
            print(f"⚠️  Error creating chart: {e}")
            return None
    
    @staticmethod
    def _extract_data_list(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract the list of data items from the nested GraphQL response."""
        if not data:
            return []
        
        # GraphQL responses are typically nested: {queryName: [items]}
        for key, value in data.items():
            if isinstance(value, list) and value:
                return value
        
        return []
    
    @staticmethod
    def _create_bar_chart(
        df: pd.DataFrame,
        x_field: str,
        y_field: str,
        title: str,
    ) -> go.Figure:
        """Create a bar chart."""
        fig = px.bar(
            df,
            x=x_field,
            y=y_field,
            title=title,
            labels={x_field: x_field.replace("_", " ").title(), 
                   y_field: y_field.replace("_", " ").title()},
        )
        
        fig.update_layout(
            xaxis_tickangle=-45,
            hovermode="x unified",
            template="plotly_white",
        )
        
        return fig
    
    @staticmethod
    def _create_line_chart(
        df: pd.DataFrame,
        x_field: str,
        y_field: str,
        title: str,
    ) -> go.Figure:
        """Create a line chart."""
        fig = px.line(
            df,
            x=x_field,
            y=y_field,
            title=title,
            labels={x_field: x_field.replace("_", " ").title(), 
                   y_field: y_field.replace("_", " ").title()},
            markers=True,
        )
        
        fig.update_layout(
            hovermode="x unified",
            template="plotly_white",
        )
        
        return fig
    
    @staticmethod
    def _create_pie_chart(
        df: pd.DataFrame,
        x_field: str,
        y_field: str,
        title: str,
    ) -> go.Figure:
        """Create a pie chart."""
        fig = px.pie(
            df,
            names=x_field,
            values=y_field,
            title=title,
        )
        
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(template="plotly_white")
        
        return fig
    
    @staticmethod
    def _create_scatter_chart(
        df: pd.DataFrame,
        x_field: str,
        y_field: str,
        title: str,
    ) -> go.Figure:
        """Create a scatter plot."""
        fig = px.scatter(
            df,
            x=x_field,
            y=y_field,
            title=title,
            labels={x_field: x_field.replace("_", " ").title(), 
                   y_field: y_field.replace("_", " ").title()},
        )
        
        fig.update_layout(
            hovermode="closest",
            template="plotly_white",
        )
        
        return fig
    
    @staticmethod
    def _create_histogram(
        df: pd.DataFrame,
        x_field: str,
        title: str,
    ) -> go.Figure:
        """Create a histogram."""
        fig = px.histogram(
            df,
            x=x_field,
            title=title,
            labels={x_field: x_field.replace("_", " ").title()},
        )
        
        fig.update_layout(
            bargap=0.1,
            template="plotly_white",
        )
        
        return fig
    
    @staticmethod
    def display_as_table(data: Dict[str, Any]) -> None:
        """Display data as a formatted table."""
        data_list = ChartGenerator._extract_data_list(data)
        
        if not data_list:
            print("No data to display")
            return
        
        df = pd.DataFrame(data_list)
        print("\n" + "="*80)
        print(df.to_string(index=False))
        print("="*80 + "\n")
    
    @staticmethod
    def save_chart(fig: go.Figure, filename: str) -> None:
        """Save a chart to an HTML file."""
        if fig:
            fig.write_html(filename)
            print(f"📁 Chart saved to: {filename}")
