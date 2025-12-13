#!/usr/bin/env python3
"""
Simple demo script for the self-correcting multi-agent system.
This script demonstrates the system without relative import issues.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    print("🚀 Self-Correcting Multi-Agent System - Simple Demo")
    print("=" * 55)
    
    try:
        # Import components
        from agents import Orchestrator
        from utils import get_config, validate_config
        
        print("✅ Imports successful")
        
        # Test configuration
        config = get_config()
        validate_config(config)
        print("✅ Configuration valid")
        
        # Test orchestrator initialization
        orchestrator = Orchestrator(config)
        print("✅ Orchestrator initialized")
        
        # Test simple question
        question = "What is the capital of France and approximately how many people live there?"
        print(f"\n🤔 Testing question: {question}")
        
        result = orchestrator.process(question)
        
        print(f"\n📊 Results:")
        print(f"  Answer: {result.final_answer[:200]}...")
        print(f"  Accepted: {'✅' if result.accepted else '❌'}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Iterations: {result.total_iterations}")
        print(f"  Latency: {result.total_latency_ms:.0f}ms")
        
        # Show iteration details
        print(f"\n🔍 Iteration Details:")
        for i, iteration in enumerate(result.iterations, 1):
            print(f"  Iteration {i}:")
            print(f"    Solver Confidence: {iteration.solver_response.confidence:.2f}")
            if iteration.critic_response:
                print(f"    Critic Decision: {iteration.critic_response.status.value}")
                print(f"    Critic Confidence: {iteration.critic_response.confidence:.2f}")
            if iteration.judge_response:
                print(f"    Judge Decision: {iteration.judge_response.decision.value}")
                print(f"    Judge Confidence: {iteration.judge_response.confidence:.2f}")
            print(f"    Result: {iteration.reason}")
        
        print("\n✅ Demo completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)