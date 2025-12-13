"""
Performance metrics for evaluating the multi-agent system.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np
from agents.orchestrator import SystemResult

@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for the multi-agent system."""
    
    # Accuracy and Quality Metrics
    accuracy_score: float
    confidence_score: float
    validation_success_rate: float
    hallucination_rate: float
    groundedness_score: float
    
    # Efficiency Metrics
    avg_iterations: float
    avg_latency_ms: float
    avg_tokens_used: float
    cost_efficiency: float
    
    # Reliability Metrics
    success_rate: float
    error_rate: float
    consistency_score: float
    
    # Comparative Metrics (vs single agent)
    confidence_improvement: float
    latency_overhead: float
    cost_multiplier: float
    quality_gain: float

def calculate_metrics(results: List[SystemResult], single_agent_baseline: Optional[List[Dict]] = None) -> PerformanceMetrics:
    """
    Calculate comprehensive performance metrics from system results.
    
    Args:
        results: List of SystemResult objects from multi-agent system
        single_agent_baseline: Optional baseline results from single agent for comparison
        
    Returns:
        PerformanceMetrics object with calculated metrics
    """
    if not results:
        return PerformanceMetrics(
            accuracy_score=0.0, confidence_score=0.0, validation_success_rate=0.0,
            hallucination_rate=0.0, groundedness_score=0.0, avg_iterations=0.0,
            avg_latency_ms=0.0, avg_tokens_used=0.0, cost_efficiency=0.0,
            success_rate=0.0, error_rate=0.0, consistency_score=0.0,
            confidence_improvement=0.0, latency_overhead=0.0, cost_multiplier=0.0,
            quality_gain=0.0
        )
    
    # Basic statistics
    total_results = len(results)
    successful_results = [r for r in results if r.accepted]
    
    # Accuracy and Quality Metrics
    validation_success_rate = len(successful_results) / total_results
    confidence_scores = [r.confidence for r in results]
    avg_confidence = np.mean(confidence_scores)
    
    # Estimate accuracy based on confidence and validation
    # This is a proxy - in real evaluation you'd have ground truth
    accuracy_score = validation_success_rate * avg_confidence
    
    # Estimate hallucination rate (inverse of groundedness)
    # Higher confidence + validation success = lower hallucination
    hallucination_rate = max(0.0, 1.0 - (validation_success_rate * avg_confidence))
    
    # Groundedness score (based on validation and evidence quality)
    groundedness_score = validation_success_rate * 0.7 + avg_confidence * 0.3
    
    # Efficiency Metrics
    iterations = [r.total_iterations for r in results]
    latencies = [r.total_latency_ms for r in results]
    tokens = [r.total_tokens for r in results]
    
    avg_iterations = np.mean(iterations)
    avg_latency_ms = np.mean(latencies)
    avg_tokens_used = np.mean(tokens) if any(t > 0 for t in tokens) else 0.0
    
    # Cost efficiency (quality per unit cost)
    cost_efficiency = accuracy_score / max(avg_iterations, 1.0)
    
    # Reliability Metrics
    success_rate = validation_success_rate
    error_rate = 1.0 - success_rate
    
    # Consistency (how similar are confidence scores)
    consistency_score = 1.0 - (np.std(confidence_scores) / max(np.mean(confidence_scores), 0.1))
    consistency_score = max(0.0, min(1.0, consistency_score))
    
    # Comparative Metrics
    confidence_improvement = 0.0
    latency_overhead = 0.0
    cost_multiplier = avg_iterations  # Rough estimate
    quality_gain = 0.0
    
    if single_agent_baseline:
        baseline_confidence = np.mean([b.get('confidence', 0.5) for b in single_agent_baseline])
        baseline_latency = np.mean([b.get('latency_ms', 1000) for b in single_agent_baseline])
        
        confidence_improvement = avg_confidence - baseline_confidence
        latency_overhead = avg_latency_ms - baseline_latency
        
        # Quality gain combines confidence improvement and validation
        quality_gain = confidence_improvement + (validation_success_rate * 0.2)
    
    return PerformanceMetrics(
        accuracy_score=accuracy_score,
        confidence_score=avg_confidence,
        validation_success_rate=validation_success_rate,
        hallucination_rate=hallucination_rate,
        groundedness_score=groundedness_score,
        avg_iterations=avg_iterations,
        avg_latency_ms=avg_latency_ms,
        avg_tokens_used=avg_tokens_used,
        cost_efficiency=cost_efficiency,
        success_rate=success_rate,
        error_rate=error_rate,
        consistency_score=consistency_score,
        confidence_improvement=confidence_improvement,
        latency_overhead=latency_overhead,
        cost_multiplier=cost_multiplier,
        quality_gain=quality_gain
    )

def calculate_category_metrics(results: List[SystemResult], categories: List[str]) -> Dict[str, PerformanceMetrics]:
    """
    Calculate metrics broken down by category.
    
    Args:
        results: List of SystemResult objects
        categories: List of category names corresponding to results
        
    Returns:
        Dictionary mapping category names to PerformanceMetrics
    """
    if len(results) != len(categories):
        raise ValueError("Results and categories must have the same length")
    
    category_results = {}
    
    # Group results by category
    for result, category in zip(results, categories):
        if category not in category_results:
            category_results[category] = []
        category_results[category].append(result)
    
    # Calculate metrics for each category
    category_metrics = {}
    for category, cat_results in category_results.items():
        category_metrics[category] = calculate_metrics(cat_results)
    
    return category_metrics

def compare_configurations(
    config_results: Dict[str, List[SystemResult]]
) -> Dict[str, Dict[str, Any]]:
    """
    Compare performance across different system configurations.
    
    Args:
        config_results: Dictionary mapping configuration names to results
        
    Returns:
        Dictionary with comparative analysis
    """
    comparison = {}
    
    for config_name, results in config_results.items():
        metrics = calculate_metrics(results)
        comparison[config_name] = {
            'metrics': metrics,
            'summary': {
                'quality_score': (metrics.accuracy_score + metrics.confidence_score) / 2,
                'efficiency_score': 1.0 / max(metrics.avg_iterations, 1.0),
                'reliability_score': metrics.success_rate,
                'overall_score': (
                    metrics.accuracy_score * 0.4 +
                    metrics.success_rate * 0.3 +
                    (1.0 / max(metrics.avg_iterations, 1.0)) * 0.2 +
                    metrics.consistency_score * 0.1
                )
            }
        }
    
    # Find best configuration
    best_config = max(comparison.keys(), 
                     key=lambda k: comparison[k]['summary']['overall_score'])
    
    comparison['_analysis'] = {
        'best_overall': best_config,
        'best_quality': max(comparison.keys(), 
                           key=lambda k: comparison[k]['summary']['quality_score']),
        'best_efficiency': max(comparison.keys(), 
                              key=lambda k: comparison[k]['summary']['efficiency_score']),
        'best_reliability': max(comparison.keys(), 
                               key=lambda k: comparison[k]['summary']['reliability_score'])
    }
    
    return comparison

def generate_performance_report(metrics: PerformanceMetrics, config_name: str = "Default") -> str:
    """
    Generate a human-readable performance report.
    
    Args:
        metrics: PerformanceMetrics to report on
        config_name: Name of the configuration
        
    Returns:
        Formatted performance report string
    """
    report = f"Performance Report: {config_name}\n"
    report += "=" * (len(report) - 1) + "\n\n"
    
    # Quality Metrics
    report += "📊 Quality Metrics:\n"
    report += f"  Accuracy Score: {metrics.accuracy_score:.3f}\n"
    report += f"  Confidence Score: {metrics.confidence_score:.3f}\n"
    report += f"  Validation Success Rate: {metrics.validation_success_rate:.1%}\n"
    report += f"  Hallucination Rate: {metrics.hallucination_rate:.1%}\n"
    report += f"  Groundedness Score: {metrics.groundedness_score:.3f}\n\n"
    
    # Efficiency Metrics
    report += "⚡ Efficiency Metrics:\n"
    report += f"  Average Iterations: {metrics.avg_iterations:.1f}\n"
    report += f"  Average Latency: {metrics.avg_latency_ms:.0f}ms\n"
    report += f"  Average Tokens: {metrics.avg_tokens_used:.0f}\n"
    report += f"  Cost Efficiency: {metrics.cost_efficiency:.3f}\n\n"
    
    # Reliability Metrics
    report += "🔒 Reliability Metrics:\n"
    report += f"  Success Rate: {metrics.success_rate:.1%}\n"
    report += f"  Error Rate: {metrics.error_rate:.1%}\n"
    report += f"  Consistency Score: {metrics.consistency_score:.3f}\n\n"
    
    # Comparative Metrics (if available)
    if metrics.confidence_improvement != 0.0:
        report += "📈 Comparative Metrics (vs Single Agent):\n"
        report += f"  Confidence Improvement: {metrics.confidence_improvement:+.3f}\n"
        report += f"  Latency Overhead: {metrics.latency_overhead:+.0f}ms\n"
        report += f"  Cost Multiplier: {metrics.cost_multiplier:.1f}x\n"
        report += f"  Quality Gain: {metrics.quality_gain:+.3f}\n\n"
    
    # Overall Assessment
    overall_score = (
        metrics.accuracy_score * 0.4 +
        metrics.success_rate * 0.3 +
        (1.0 / max(metrics.avg_iterations, 1.0)) * 0.2 +
        metrics.consistency_score * 0.1
    )
    
    report += f"🎯 Overall Performance Score: {overall_score:.3f}\n"
    
    if overall_score >= 0.8:
        report += "   Assessment: Excellent performance ✅\n"
    elif overall_score >= 0.6:
        report += "   Assessment: Good performance 👍\n"
    elif overall_score >= 0.4:
        report += "   Assessment: Acceptable performance ⚠️\n"
    else:
        report += "   Assessment: Needs improvement ❌\n"
    
    return report