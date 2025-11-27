"""Test script to verify the setup and basic functionality."""
import sys


def test_imports():
    """Test that all required packages can be imported."""
    print("Testing imports...")
    
    try:
        import sqlalchemy
        print("  ✅ SQLAlchemy")
    except ImportError:
        print("  ❌ SQLAlchemy - run: pip install sqlalchemy")
        return False
    
    try:
        import strawberry
        print("  ✅ Strawberry GraphQL")
    except ImportError:
        print("  ❌ Strawberry GraphQL - run: pip install strawberry-graphql")
        return False
    
    try:
        import langchain
        print("  ✅ LangChain")
    except ImportError:
        print("  ❌ LangChain - run: pip install langchain")
        return False
    
    try:
        import plotly
        print("  ✅ Plotly")
    except ImportError:
        print("  ❌ Plotly - run: pip install plotly")
        return False
    
    try:
        import pandas
        print("  ✅ Pandas")
    except ImportError:
        print("  ❌ Pandas - run: pip install pandas")
        return False
    
    try:
        from faker import Faker
        print("  ✅ Faker")
    except ImportError:
        print("  ❌ Faker - run: pip install faker")
        return False
    
    try:
        from dotenv import load_dotenv
        print("  ✅ Python-dotenv")
    except ImportError:
        print("  ❌ Python-dotenv - run: pip install python-dotenv")
        return False
    
    return True


def test_config():
    """Test configuration."""
    print("\nTesting configuration...")
    
    try:
        from config import OPENAI_API_KEY, ANTHROPIC_API_KEY, LLM_PROVIDER
        
        if LLM_PROVIDER == "openai":
            if OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key_here":
                print(f"  ✅ OpenAI API key configured")
            else:
                print(f"  ⚠️  OpenAI API key not configured in .env file")
                return False
        elif LLM_PROVIDER == "anthropic":
            if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your_anthropic_api_key_here":
                print(f"  ✅ Anthropic API key configured")
            else:
                print(f"  ⚠️  Anthropic API key not configured in .env file")
                return False
        else:
            print(f"  ⚠️  Unknown LLM provider: {LLM_PROVIDER}")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False


def test_database():
    """Test database initialization."""
    print("\nTesting database...")
    
    try:
        from database import init_db, get_session
        from database.models import Brand, Watch
        
        init_db()
        print("  ✅ Database initialized")
        
        session = get_session()
        brand_count = session.query(Brand).count()
        watch_count = session.query(Watch).count()
        session.close()
        
        if brand_count > 0 and watch_count > 0:
            print(f"  ✅ Database has data ({brand_count} brands, {watch_count} watches)")
        else:
            print(f"  ⚠️  Database is empty - run: python main.py init")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False


def test_graphql():
    """Test GraphQL schema."""
    print("\nTesting GraphQL schema...")
    
    try:
        from graphql_layer import schema
        
        query = """
        query {
          brands(limit: 1) {
            id
            name
          }
        }
        """
        
        result = schema.execute_sync(query)
        
        if result.errors:
            print(f"  ❌ GraphQL errors: {result.errors}")
            return False
        
        if result.data and result.data.get("brands"):
            print(f"  ✅ GraphQL schema working")
            return True
        else:
            print(f"  ⚠️  GraphQL returned no data")
            return False
    except Exception as e:
        print(f"  ❌ GraphQL error: {e}")
        return False


def test_agent():
    """Test the NL to GraphQL agent."""
    print("\nTesting agent...")
    
    try:
        from agent import NLToGraphQLAgent
        
        agent = NLToGraphQLAgent()
        print("  ✅ Agent initialized")
        
        # Test query generation (without executing)
        query = agent.generate_graphql_query("Show me all brands")
        
        if "brands" in query.lower():
            print("  ✅ Agent can generate GraphQL queries")
            return True
        else:
            print("  ⚠️  Agent generated unexpected query")
            return False
    except Exception as e:
        print(f"  ❌ Agent error: {e}")
        print(f"     Make sure your API key is configured correctly")
        return False


def main():
    """Run all tests."""
    print("="*80)
    print("Watch Retail Enterprise System - Setup Test")
    print("="*80 + "\n")
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Database", test_database()))
    results.append(("GraphQL", test_graphql()))
    results.append(("Agent", test_agent()))
    
    print("\n" + "="*80)
    print("Test Results:")
    print("="*80)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    print("="*80 + "\n")
    
    if all_passed:
        print("🎉 All tests passed! The system is ready to use.")
        print("\nRun the application with: python main.py")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Configure API key in .env file")
        print("  3. Initialize database: python main.py init")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
