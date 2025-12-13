"""
System Evaluator - Comprehensive evaluation framework for the multi-agent system.
"""

import time
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import pandas as pd
import numpy as np

from agents.orchestrator import Orchestrator, SystemResult
from utils.config import SystemConfig, get_config
from evaluation.metrics import PerformanceMetrics, calculate_metrics
from evaluation.synthetic_data import SyntheticDataGenerator, EvaluationCase

# EvaluationCase now imported from synthetic_data

@dataclass
class EvaluationResult:
    """Result of evaluating a single test case."""
    case: EvaluationCase
    system_result: SystemResult
    single_agent_result: Optional[Dict[str, Any]] = None
    evaluation_metrics: Optional[Dict[str, float]] = None
    timestamp: float = 0.0

class SystemEvaluator:
    """
    Comprehensive evaluator for the self-correcting multi-agent system.
    
    Provides tools for systematic testing, performance measurement,
    and comparison against baselines.
    """
    
    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or get_config()
        self.orchestrator = Orchestrator(self.config)
        self.synthetic_generator = SyntheticDataGenerator()
        self.results_dir = Path("data/evaluation_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def evaluate_test_cases(
        self, 
        test_cases: List[EvaluationCase],
        include_single_agent_comparison: bool = True,
        save_results: bool = True
    ) -> List[EvaluationResult]:
        """
        Evaluate the system on a set of test cases.
        
        Args:
            test_cases: List of test cases to evaluate
            include_single_agent_comparison: Whether to compare with single agent
            save_results: Whether to save results to disk
            
        Returns:
            List of EvaluationResult objects
        """
        results = []
        
        print(f"🧪 Starting evaluation of {len(test_cases)} test cases...")
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n📝 Evaluating case {i}/{len(test_cases)}: {case.category}")
            print(f"   Question: {case.question[:60]}...")
            
            start_time = time.time()
            
            # Run multi-agent system
            system_result = self.orchestrator.process(case.question, case.context)
            
            # Run single agent comparison if requested
            single_agent_result = None
            if include_single_agent_comparison:
                comparison = self.orchestrator.compare_single_vs_multi_agent(
                    case.question, case.context
                )
                single_agent_result = comparison['single_agent']
            
            # Calculate evaluation metrics
            eval_metrics = self._calculate_case_metrics(case, system_result, single_agent_result)
            
            # Create result
            result = EvaluationResult(
                case=case,
                system_result=system_result,
                single_agent_result=single_agent_result,
                evaluation_metrics=eval_metrics,
                timestamp=time.time()
            )
            
            results.append(result)
            
            # Progress update
            elapsed = time.time() - start_time
            print(f"   ✅ Completed in {elapsed:.1f}s - "
                  f"Confidence: {system_result.confidence:.2f}, "
                  f"Accepted: {'✅' if system_result.accepted else '❌'}")
        
        if save_results:
            self._save_evaluation_results(results)
        
        print(f"\n🎯 Evaluation complete! {len(results)} cases processed.")
        return results
    
    def _calculate_case_metrics(
        self, 
        case: EvaluationCase, 
        system_result: SystemResult,
        single_agent_result: Optional[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate metrics for a single evaluation case."""
        metrics = {
            'confidence': system_result.confidence,
            'accepted': float(system_result.accepted),
            'iterations': float(system_result.total_iterations),
            'latency_ms': system_result.total_latency_ms,
            'tokens_used': float(system_result.total_tokens)
        }
        
        # Add comparison metrics if single agent result available
        if single_agent_result:
            metrics.update({
                'confidence_improvement': system_result.confidence - single_agent_result['confidence'],
                'latency_overhead': system_result.total_latency_ms - single_agent_result['latency_ms'],
                'validation_added': float(system_result.accepted)
            })
        
        # Add ground truth metrics if available
        if case.ground_truth:
            metrics.update(self._calculate_ground_truth_metrics(case, system_result))
        
        return metrics
    
    def _calculate_ground_truth_metrics(
        self, 
        case: EvaluationCase, 
        system_result: SystemResult
    ) -> Dict[str, float]:
        """Calculate metrics against ground truth if available."""
        # This is a placeholder for ground truth evaluation
        # In a real implementation, you would compare against known correct answers
        
        ground_truth = case.ground_truth or {}
        metrics = {}
        
        # Example: if ground truth has expected confidence range
        if 'expected_confidence_min' in ground_truth:
            min_conf = ground_truth['expected_confidence_min']
            metrics['confidence_meets_expectation'] = float(
                system_result.confidence >= min_conf
            )
        
        # Example: if ground truth has expected keywords in answer
        if 'required_keywords' in ground_truth:
            keywords = ground_truth['required_keywords']
            answer_lower = system_result.final_answer.lower()
            keyword_matches = sum(1 for kw in keywords if kw.lower() in answer_lower)
            metrics['keyword_coverage'] = keyword_matches / len(keywords) if keywords else 0.0
        
        return metrics
    
    def generate_performance_report(
        self, 
        results: List[EvaluationResult]
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report from evaluation results.
        
        Args:
            results: List of evaluation results
            
        Returns:
            Dictionary containing performance analysis
        """
        if not results:
            return {"error": "No results to analyze"}
        
        # Extract system results for metrics calculation
        system_results = [r.system_result for r in results]
        single_agent_baseline = [r.single_agent_result for r in results if r.single_agent_result]
        
        # Calculate overall metrics
        overall_metrics = calculate_metrics(system_results, single_agent_baseline)
        
        # Category breakdown
        categories = list(set(r.case.category for r in results))
        category_analysis = {}
        
        for category in categories:
            category_results = [r for r in results if r.case.category == category]
            category_system_results = [r.system_result for r in category_results]
            category_baseline = [r.single_agent_result for r in category_results if r.single_agent_result]
            
            category_metrics = calculate_metrics(category_system_results, category_baseline)
            category_analysis[category] = {
                'metrics': category_metrics,
                'test_count': len(category_results),
                'success_rate': sum(1 for r in category_results if r.system_result.accepted) / len(category_results)
            }
        
        # Difficulty analysis
        difficulties = list(set(r.case.difficulty for r in results))
        difficulty_analysis = {}
        
        for difficulty in difficulties:
            diff_results = [r for r in results if r.case.difficulty == difficulty]
            diff_system_results = [r.system_result for r in diff_results]
            
            difficulty_analysis[difficulty] = {
                'test_count': len(diff_results),
                'avg_confidence': np.mean([r.confidence for r in diff_system_results]),
                'success_rate': sum(1 for r in diff_results if r.system_result.accepted) / len(diff_results),
                'avg_iterations': np.mean([r.total_iterations for r in diff_system_results])
            }
        
        # Performance trends
        results_by_time = sorted(results, key=lambda r: r.timestamp)
        confidence_trend = [r.system_result.confidence for r in results_by_time]
        
        report = {
            'evaluation_summary': {
                'total_cases': len(results),
                'evaluation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'system_config': asdict(self.config)
            },
            'overall_metrics': asdict(overall_metrics),
            'category_analysis': category_analysis,
            'difficulty_analysis': difficulty_analysis,
            'performance_trends': {
                'confidence_trend': confidence_trend,
                'avg_confidence': np.mean(confidence_trend),
                'confidence_std': np.std(confidence_trend)
            },
            'recommendations': self._generate_recommendations(overall_metrics, category_analysis)
        }
        
        return report
    
    def _generate_recommendations(
        self, 
        overall_metrics: PerformanceMetrics,
        category_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations based on evaluation results."""
        recommendations = []
        
        # Confidence-based recommendations
        if overall_metrics.confidence_score < 0.7:
            recommendations.append(
                "Consider lowering judge confidence threshold or improving prompts - "
                f"average confidence is {overall_metrics.confidence_score:.2f}"
            )
        
        # Iteration-based recommendations
        if overall_metrics.avg_iterations > 2.5:
            recommendations.append(
                f"High iteration count ({overall_metrics.avg_iterations:.1f}) suggests "
                "critic may be too strict - consider tuning critic prompts"
            )
        
        # Success rate recommendations
        if overall_metrics.success_rate < 0.6:
            recommendations.append(
                f"Low success rate ({overall_metrics.success_rate:.1%}) - "
                "consider lowering validation thresholds or improving agent prompts"
            )
        
        # Category-specific recommendations
        for category, analysis in category_analysis.items():
            if analysis['success_rate'] < 0.5:
                recommendations.append(
                    f"Category '{category}' has low success rate ({analysis['success_rate']:.1%}) - "
                    "consider specialized prompts or tools for this domain"
                )
        
        # Performance recommendations
        if overall_metrics.avg_latency_ms > 10000:  # 10 seconds
            recommendations.append(
                f"High latency ({overall_metrics.avg_latency_ms/1000:.1f}s) - "
                "consider using faster models or reducing max iterations"
            )
        
        if not recommendations:
            recommendations.append("System performance looks good! Consider testing on more diverse cases.")
        
        return recommendations
    
    def _save_evaluation_results(self, results: List[EvaluationResult]) -> None:
        """Save evaluation results to disk."""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"evaluation_results_{timestamp}.json"
        filepath = self.results_dir / filename
        
        # Convert results to serializable format
        serializable_results = []
        for result in results:
            serializable_result = {
                'case': asdict(result.case),
                'system_result': asdict(result.system_result),
                'single_agent_result': result.single_agent_result,
                'evaluation_metrics': result.evaluation_metrics,
                'timestamp': result.timestamp
            }
            serializable_results.append(serializable_result)
        
        with open(filepath, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)
        
        print(f"💾 Results saved to {filepath}")
    
    def load_evaluation_results(self, filepath: str) -> List[EvaluationResult]:
        """Load evaluation results from disk."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        results = []
        for item in data:
            # Reconstruct objects from serialized data
            case = EvaluationCase(**item['case'])
            # Note: SystemResult reconstruction would need custom logic
            # This is a simplified version
            result = EvaluationResult(
                case=case,
                system_result=None,  # Would need proper reconstruction
                single_agent_result=item['single_agent_result'],
                evaluation_metrics=item['evaluation_metrics'],
                timestamp=item['timestamp']
            )
            results.append(result)
        
        return results
    
    def run_benchmark_suite(self) -> Dict[str, Any]:
        """Run a comprehensive benchmark suite."""
        print("🏃‍♂️ Running comprehensive benchmark suite...")
        
        # Generate diverse test cases
        test_cases = []
        
        # Simple factual questions
        test_cases.extend([
            EvaluationCase(
                id="fact_1",
                question="What is the capital of Japan?",
                category="Simple Factual",
                difficulty="Easy"
            ),
            EvaluationCase(
                id="fact_2", 
                question="Who wrote the novel '1984'?",
                category="Simple Factual",
                difficulty="Easy"
            )
        ])
        
        # Conceptual questions
        test_cases.extend([
            EvaluationCase(
                id="concept_1",
                question="Explain the difference between artificial intelligence and machine learning.",
                category="Conceptual",
                difficulty="Medium"
            ),
            EvaluationCase(
                id="concept_2",
                question="What is the greenhouse effect and how does it contribute to climate change?",
                category="Conceptual", 
                difficulty="Medium"
            )
        ])
        
        # Complex reasoning
        test_cases.extend([
            EvaluationCase(
                id="complex_1",
                question="If a company's revenue increased by 15% but costs increased by 20%, what happened to their profit margin and what might this indicate about their business?",
                category="Complex Reasoning",
                difficulty="Hard"
            )
        ])
        
        # Run evaluation
        results = self.evaluate_test_cases(test_cases)
        
        # Generate report
        report = self.generate_performance_report(results)
        
        # Save benchmark report
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        report_file = self.results_dir / f"benchmark_report_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📊 Benchmark complete! Report saved to {report_file}")
        return report

# Example usage and testing
def test_evaluator():
    """Test function for the evaluator."""
    evaluator = SystemEvaluator()
    
    # Create simple test case
    test_case = EvaluationCase(
        id="test_1",
        question="What is 2 + 2?",
        category="Math",
        difficulty="Easy"
    )
    
    # Run evaluation
    results = evaluator.evaluate_test_cases([test_case])
    
    # Generate report
    report = evaluator.generate_performance_report(results)
    
    print("Evaluation Report:")
    print(json.dumps(report, indent=2, default=str))

if __name__ == "__main__":
    test_evaluator()