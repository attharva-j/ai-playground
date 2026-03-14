import os
import logging
from datetime import datetime
from clients.secrets_client import get_secret

import boto3

secrets = get_secret()

def log_metric(metric_name: str, value: float, unit: str = "Count") -> None:
    """
    Log a custom metric to CloudWatch.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        unit: Metric unit (Count, Seconds, etc.)
    """
    try:
        if secrets["ENABLE_CLOUDWATCH_METRICS"].lower() != "true":
            return
        
        cloudwatch = boto3.client(
            'cloudwatch',
            region_name=secrets["AWS_REGION"]
        )
        
        cloudwatch.put_metric_data(
            Namespace='MCP/ImageGenerator',
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': unit,
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to log metric {metric_name}: {str(e)}")