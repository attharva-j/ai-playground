"""Main application for NL to GraphQL enterprise solution."""
import sys
import json
from database.seed_data import seed_database
from agent import NLToGraphQLAgent
from visualization import ChartGenerator


def initialize_system():
    """Initialize the database and seed it with data."""
    print("🚀 Initializing Watch Retail Enterprise System...")
    print("="*80)
    seed_database()
    print("="*80)


def run_interactive_mode():
    """Run the system in interactive mode."""
    print("\n💎 Welcome to the Watch Retail Intelligence System")
    print("="*80)
    print("Ask questions about watches, customers, orders, inventory, and sales!")
    print("Type 'exit' or 'quit' to end the session.")
    print("="*80 + "\n")
    
    agent = NLToGraphQLAgent()
    chart_gen = ChartGenerator()
    
    example_queries = [
        "Show me the top 5 best-selling watch models",
        "What's the revenue trend over the last 6 months?",
        "Which customers have spent more than $50,000?",
        "Show inventory levels for all watches",
        "What's the average price of watches by brand?",
    ]
    
    print("💡 Example queries you can try:")
    for i, query in enumerate(example_queries, 1):
        print(f"   {i}. {query}")
    print()
    
    while True:
        try:
            user_input = input("🔮 Your question: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit", "q"]:
                print("\n👋 Thank you for using the Watch Retail Intelligence System!")
                break
            
            # Process the query
            result = agent.process_query(user_input)
            
            if not result["success"]:
                print(f"\n❌ Error: {result['answer']}\n")
                continue
            
            # Display the answer
            print("\n" + "="*80)
            print("📋 ANSWER:")
            print("="*80)
            print(result["answer"])
            print("="*80 + "\n")
            
            # Display or generate visualization
            viz_config = result["visualization"]
            
            if viz_config and viz_config["chart_type"] != "table":
                print(f"📊 Generating {viz_config['chart_type']} chart...")
                fig = chart_gen.generate_chart(result["data"], viz_config)
                
                if fig:
                    # Save the chart
                    filename = f"chart_{viz_config['chart_type']}.html"
                    chart_gen.save_chart(fig, filename)
                    print(f"   Open '{filename}' in your browser to view the interactive chart.\n")
            else:
                # Display as table
                print("📊 Data Table:")
                chart_gen.display_as_table(result["data"])
            
            # Optionally show the GraphQL query
            show_query = input("🔍 Show GraphQL query? (y/n): ").strip().lower()
            if show_query == "y":
                print("\n" + "-"*80)
                print("GraphQL Query:")
                print("-"*80)
                print(result["graphql_query"])
                print("-"*80 + "\n")
        
        except KeyboardInterrupt:
            print("\n\n👋 Thank you for using the Watch Retail Intelligence System!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}\n")


def run_demo_queries():
    """Run a set of demo queries to showcase the system."""
    print("\n🎬 Running Demo Queries...")
    print("="*80 + "\n")
    
    agent = NLToGraphQLAgent()
    chart_gen = ChartGenerator()
    
    demo_queries = [
        "Show me the top 5 best-selling watch models",
        "What's the revenue trend over the last 12 months?",
        "List all VIP customers with their lifetime value",
        "Show me watches priced above $20,000",
        "What's the current inventory status for low stock items?",
    ]
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n{'='*80}")
        print(f"Demo Query {i}/{len(demo_queries)}: {query}")
        print('='*80)
        
        result = agent.process_query(query)
        
        if result["success"]:
            print(f"\n📋 Answer:\n{result['answer']}\n")
            
            viz_config = result["visualization"]
            if viz_config and viz_config["chart_type"] != "table":
                fig = chart_gen.generate_chart(result["data"], viz_config)
                if fig:
                    filename = f"demo_chart_{i}_{viz_config['chart_type']}.html"
                    chart_gen.save_chart(fig, filename)
        else:
            print(f"\n❌ Error: {result['answer']}\n")
        
        if i < len(demo_queries):
            input("\nPress Enter to continue to next demo query...")
    
    print("\n" + "="*80)
    print("🎉 Demo completed!")
    print("="*80 + "\n")


def main():
    """Main entry point."""
    # Check if database needs initialization
    import os
    db_path = "nl-to-graphql-enterprise-solution/watches_enterprise.db"
    if not os.path.exists(db_path):
        initialize_system()
    else:
        print("✅ Database already initialized.")
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "demo":
            run_demo_queries()
        elif sys.argv[1] == "init":
            initialize_system()
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Usage: python main.py [demo|init]")
    else:
        run_interactive_mode()


if __name__ == "__main__":
    main()
