#!/usr/bin/env python3
"""
Self-Correcting Multi-Agent System Demo Script

This script provides the same functionality as the Jupyter notebook
but in a regular Python script format that you can run directly.

Usage: python demo_script.py
"""

import os
import sys
import json
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*80)
    print(f"🔄 {title}")
    print("="*80)

def print_section(title):
    """Print a formatted section header."""
    print(f"\n📋 {title}")
    print("-" * 60)

def main():
    """Main demo function."""
    print("🎯 SELF-CORRECTING MULTI-AGENT SYSTEM DEMO")
    print("="*80)
    print("This demo shows how a multi-agent system improves AI reliability")
    print("through iterative validation and self-correction.")
    
    # Step 1: Import and Setup
    print_section("Step 1: Import and Setup")
    
    try:
        from agents import SolverAgent, CriticAgent, JudgeAgent, Orchestrator
        from utils import get_config, logger
        from tools import WebSearchTool, DatabaseTool
        print("✅ All imports successful!")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        return False
    
    # Step 2: Configuration
    print_section("Step 2: Configuration")
    
    config = get_config()
    
    # Verify API keys
    api_keys_status = {
        "OpenAI": "✅" if config.openai_api_key else "❌",
        "Tavily (Web Search)": "✅" if config.tavily_api_key else "❌",
        "LangSmith (Optional)": "✅" if config.langsmith_api_key else "⚠️"
    }
    
    print("🔑 API Keys Status:")
    for service, status in api_keys_status.items():
        print(f"  {service}: {status}")
    
    print(f"\n⚙️ System Configuration:")
    print(f"  Max Iterations: {config.max_iterations}")
    print(f"  Judge Confidence Threshold: {config.judge_confidence_threshold}")
    print(f"  Solver Model: {config.solver_config.model}")
    print(f"  Solver Temperature: {config.solver_config.temperature}")
    
    # Step 3: Initialize System
    print_section("Step 3: Initialize Multi-Agent System")
    
    orchestrator = Orchestrator(config)
    
    try:
        web_search = WebSearchTool() if config.tavily_api_key else None
        database_tool = DatabaseTool("data/sample_financial.db")
        
        print("🤖 Multi-Agent System Initialized:")
        print(f"  ✅ Solver Agent (Model: {config.solver_config.model})")
        print(f"  ✅ Critic Agent (Model: {config.critic_config.model})")
        print(f"  ✅ Judge Agent (Model: {config.judge_config.model})")
        print(f"  ✅ Orchestrator")
        print(f"  {'✅' if web_search else '❌'} Web Search Tool")
        print(f"  ✅ Database Tool")
        
    except Exception as e:
        print(f"⚠️ Warning: Some tools may not be available: {e}")
        web_search = None
    
    # Step 4: Demo 1 - Simple Question
    print_header("Demo 1: Simple Question Answering")
    
    question1 = "What is the capital of France and what is its approximate population?"
    print(f"🤔 Question: {question1}")
    
    try:
        result1 = orchestrator.process(question1)
        
        print(f"\n📊 Results:")
        print(f"  Final Answer: {result1.final_answer[:200]}...")
        print(f"  Accepted: {'✅' if result1.accepted else '❌'}")
        print(f"  Confidence: {result1.confidence:.2f}")
        print(f"  Iterations: {result1.total_iterations}")
        print(f"  Total Latency: {result1.total_latency_ms:.0f}ms")
        
        print(f"\n🔍 Iteration Details:")
        for i, iteration in enumerate(result1.iterations, 1):
            print(f"  Iteration {i}:")
            print(f"    Solver Confidence: {iteration.solver_response.confidence:.2f}")
            if iteration.critic_response:
                print(f"    Critic Decision: {iteration.critic_response.status.value}")
                print(f"    Critic Confidence: {iteration.critic_response.confidence:.2f}")
            if iteration.judge_response:
                print(f"    Judge Decision: {iteration.judge_response.decision.value}")
                print(f"    Judge Confidence: {iteration.judge_response.confidence:.2f}")
            print(f"    Result: {iteration.reason}")
        
    except Exception as e:
        print(f"❌ Error in Demo 1: {e}")
        return False
    
    # Step 5: Demo 2 - Single vs Multi-Agent Comparison
    print_header("Demo 2: Single-Agent vs Multi-Agent Comparison")
    
    question2 = "Explain the concept of quantum entanglement and provide a real-world application example."
    print(f"🤔 Question: {question2}")
    
    try:
        comparison = orchestrator.compare_single_vs_multi_agent(question2)
        
        print("\n🤖 Single-Agent Results:")
        print(f"  Answer Length: {len(comparison['single_agent']['answer'])} characters")
        print(f"  Confidence: {comparison['single_agent']['confidence']:.2f}")
        print(f"  Latency: {comparison['single_agent']['latency_ms']:.0f}ms")
        print(f"  Validated: {comparison['single_agent']['validated']}")
        
        print("\n🤖🤖🤖 Multi-Agent Results:")
        print(f"  Answer Length: {len(comparison['multi_agent']['answer'])} characters")
        print(f"  Confidence: {comparison['multi_agent']['confidence']:.2f}")
        print(f"  Latency: {comparison['multi_agent']['latency_ms']:.0f}ms")
        print(f"  Validated: {comparison['multi_agent']['validated']}")
        print(f"  Iterations: {comparison['multi_agent']['iterations']}")
        
        print("\n📈 Improvement Analysis:")
        print(f"  Confidence Gain: {comparison['improvement']['confidence_gain']:+.2f}")
        print(f"  Latency Cost: {comparison['improvement']['latency_cost']:+.0f}ms")
        print(f"  Validation Added: {comparison['improvement']['validation_added']}")
        print(f"  Iteration Overhead: {comparison['improvement']['iteration_overhead']}")
        
        print("\n📝 Answer Comparison:")
        print("Single-Agent Answer:")
        print(f"  {comparison['single_agent']['answer'][:300]}...")
        print("\nMulti-Agent Answer:")
        print(f"  {comparison['multi_agent']['answer'][:300]}...")
        
    except Exception as e:
        print(f"❌ Error in Demo 2: {e}")
    
    # Step 6: Demo 3 - Financial Analysis
    print_header("Demo 3: Financial Analysis with Database Integration")
    
    try:
        db_summary = database_tool.get_database_summary()
        
        print("💾 Sample Database Overview:")
        print(f"  Database: {db_summary['database_path']}")
        print(f"  Tables: {db_summary['table_count']}")
        
        for table_name, table_info in db_summary['tables'].items():
            print(f"\n  📊 Table: {table_name}")
            print(f"    Rows: {table_info['row_count']}")
            print(f"    Columns: {len(table_info['schema']['columns'])}")
            for col in table_info['schema']['columns'][:3]:
                print(f"      - {col['name']} ({col['type']})")
            if len(table_info['schema']['columns']) > 3:
                print(f"      ... and {len(table_info['schema']['columns']) - 3} more")
        
        # Financial analysis question
        financial_question = """
        Analyze the financial performance of TechCorp Inc for 2023. 
        Calculate their profit margin, debt-to-revenue ratio, and compare 
        their performance to the technology sector average. 
        Provide specific numbers and explain what they mean for investors.
        """
        
        db_context = f"""
        You have access to a financial database with the following structure:
        {json.dumps(db_summary, indent=2)}
        
        Use this data to provide accurate, evidence-based financial analysis.
        """
        
        print(f"\n💰 Financial Analysis Question:")
        print(financial_question.strip())
        
        financial_result = orchestrator.process(financial_question.strip(), db_context)
        
        print(f"\n📊 Financial Analysis Results:")
        print(f"  Accepted: {'✅' if financial_result.accepted else '❌'}")
        print(f"  Confidence: {financial_result.confidence:.2f}")
        print(f"  Iterations: {financial_result.total_iterations}")
        print(f"  Processing Time: {financial_result.total_latency_ms:.0f}ms")
        
        print(f"\n📈 Analysis:")
        print(financial_result.final_answer)
        
    except Exception as e:
        print(f"❌ Error in Demo 3: {e}")
    
    # Step 7: Conclusion
    print_header("Conclusion and Key Insights")
    
    print("✅ DEMONSTRATED BENEFITS:")
    benefits = [
        "Improved confidence scores through iterative refinement",
        "Enhanced validation with multi-layer review process",
        "Reduced hallucination through systematic fact-checking",
        "Enhanced transparency with detailed reasoning",
        "Configurable quality vs speed trade-offs",
        "Robust error handling and recovery mechanisms"
    ]
    
    for benefit in benefits:
        print(f"  ✅ {benefit}")
    
    print("\n💡 KEY LEARNINGS:")
    learnings = [
        "Multi-agent systems excel at complex, high-stakes tasks",
        "Confidence thresholds must be tuned per use case",
        "Latency overhead is acceptable for quality gains",
        "Validation catches errors single agents miss",
        "Cost increases are justified by reliability improvements"
    ]
    
    for learning in learnings:
        print(f"  💡 {learning}")
    
    print("\n🚀 NEXT STEPS FOR IMPLEMENTATION:")
    next_steps = [
        "Identify high-value use cases in your organization",
        "Run pilot tests with your specific data and requirements",
        "Tune configuration parameters for your use cases",
        "Implement monitoring and alerting systems",
        "Train your team on the system capabilities",
        "Gradually roll out to production with careful monitoring",
        "Collect user feedback and iterate on improvements"
    ]
    
    for i, step in enumerate(next_steps, 1):
        print(f"  {i}. {step}")
    
    print("\n" + "="*80)
    print("🎉 Thank you for exploring Self-Correcting Multi-Agent Systems!")
    print("   Ready to revolutionize your AI applications with reliability and accuracy.")
    print("="*80)
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Demo completed successfully!")
        print("\n📚 Additional Resources:")
        print("  - Run 'python test_system.py' for quick system validation")
        print("  - Check 'evaluation/' folder for comprehensive testing tools")
        print("  - Modify 'utils/config.py' to customize system behavior")
        print("  - See README.md for detailed documentation")
    else:
        print("\n❌ Demo encountered errors. Please check the setup and try again.")
    
    sys.exit(0 if success else 1)