#!/usr/bin/env python3
"""
Quick test script for the self-correcting multi-agent system.

This script provides a simple way to test the system without running
the full Jupyter notebook.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_basic_functionality():
    """Test basic system functionality."""
    print("🧪 Testing Self-Correcting Multi-Agent System")
    print("=" * 50)
    
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
        question = "What is 2 + 2?"
        print(f"\n🤔 Testing question: {question}")
        
        result = orchestrator.process(question)
        
        print(f"\n📊 Results:")
        print(f"  Answer: {result.final_answer[:100]}...")
        print(f"  Accepted: {'✅' if result.accepted else '❌'}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Iterations: {result.total_iterations}")
        print(f"  Latency: {result.total_latency_ms:.0f}ms")
        
        print("\n✅ Basic functionality test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_comparison():
    """Test single vs multi-agent comparison."""
    print("\n🔄 Testing Single vs Multi-Agent Comparison")
    print("-" * 50)
    
    try:
        from agents import Orchestrator
        from utils import get_config
        
        orchestrator = Orchestrator(get_config())
        
        question = "Explain the concept of artificial intelligence."
        print(f"Question: {question}")
        
        comparison = orchestrator.compare_single_vs_multi_agent(question)
        
        print(f"\n📊 Comparison Results:")
        print(f"Single Agent:")
        print(f"  Confidence: {comparison['single_agent']['confidence']:.2f}")
        print(f"  Latency: {comparison['single_agent']['latency_ms']:.0f}ms")
        
        print(f"Multi Agent:")
        print(f"  Confidence: {comparison['multi_agent']['confidence']:.2f}")
        print(f"  Latency: {comparison['multi_agent']['latency_ms']:.0f}ms")
        print(f"  Validated: {comparison['multi_agent']['validated']}")
        print(f"  Iterations: {comparison['multi_agent']['iterations']}")
        
        print(f"Improvement:")
        print(f"  Confidence Gain: {comparison['improvement']['confidence_gain']:+.2f}")
        print(f"  Latency Cost: {comparison['improvement']['latency_cost']:+.0f}ms")
        
        print("\n✅ Comparison test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Comparison test failed: {e}")
        return False

def test_tools():
    """Test tool functionality."""
    print("\n🔧 Testing Tools")
    print("-" * 50)
    
    try:
        # Test database tool
        from tools import DatabaseTool
        
        db_tool = DatabaseTool("data/test_financial.db")
        result = db_tool.execute_query("SELECT name FROM companies LIMIT 2")
        
        if result.success:
            print("✅ Database tool working")
            print(f"  Found {result.row_count} companies")
        else:
            print(f"⚠️ Database tool issue: {result.error}")
        
        # Test web search (if API key available)
        try:
            from tools import WebSearchTool
            web_tool = WebSearchTool()
            print("✅ Web search tool initialized")
        except Exception as e:
            print(f"⚠️ Web search tool not available: {e}")
        
        # Test document retriever
        from tools import DocumentRetriever
        doc_tool = DocumentRetriever("data/test_documents.db")
        results = doc_tool.search("machine learning", max_results=2)
        print(f"✅ Document retriever working ({len(results)} results)")
        
        print("\n✅ Tools test completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Tools test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Self-Correcting Multi-Agent System Test Suite")
    print("=" * 60)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Single vs Multi-Agent", test_comparison),
        ("Tools", test_tools)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        if test_func():
            passed += 1
    
    print(f"\n🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready to use.")
        print("\n📚 Next steps:")
        print("  1. Run the Jupyter notebook: jupyter lab self_correcting_agents_demo.ipynb")
        print("  2. Explore the configuration options in utils/config.py")
        print("  3. Add your own test cases and use cases")
        return True
    else:
        print("⚠️ Some tests failed. Check the error messages above.")
        print("\n🔧 Troubleshooting:")
        print("  1. Ensure all dependencies are installed: pip install -r requirements.txt")
        print("  2. Check that API keys are set in the .env file")
        print("  3. Verify Python version compatibility (3.8+)")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)