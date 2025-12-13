"""
Evaluation module for the self-correcting multi-agent system.

This module provides tools for measuring and analyzing system performance,
generating synthetic test data, and comparing different configurations.
"""

from .metrics import PerformanceMetrics, calculate_metrics
from .evaluator import SystemEvaluator
from .synthetic_data import SyntheticDataGenerator

__all__ = ['PerformanceMetrics', 'calculate_metrics', 'SystemEvaluator', 'SyntheticDataGenerator']