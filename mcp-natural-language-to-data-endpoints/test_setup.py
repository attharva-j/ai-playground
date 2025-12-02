#!/usr/bin/env python3
"""
Test Setup Script for MCP Natural Language to Data Endpoints

This script tests all configured database connections and LLM provider
connectivity before running the MCP server. It's HIGHLY RECOMMENDED to run
this script after initial setup and before each server start.

What it tests:
    ✓ LLM Provider connectivity (OpenAI/Anthropic)
    ✓ SQL databases (MySQL, PostgreSQL, Oracle, MS-SQL, Snowflake)
    ✓ NoSQL databases (MongoDB, Redis, Cassandra, DynamoDB)
    ✓ Graph databases (Neo4j, ArangoDB, Neptune)
    ✓ GraphQL APIs (Generic, Saleor)
    ✓ Python package dependencies

Usage:
    python test_setup.py              # Full test with API calls
    python test_setup.py --quick      # Skip slow tests (faster)
    python test_setup.py --verbose    # Detailed output

When to run:
    - After initial setup
    - Before starting the server
    - After changing .env configuration
    - When troubleshooting connection issues
    - After database infrastructure changes

Exit codes:
    0 - All tests passed
    1 - Some tests failed or no connections configured
"""

import os
import sys
from typing import Dict, List, Tuple
from dotenv import load_dotenv
import argparse

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")

class SetupTester:
    def __init__(self, verbose: bool = False, quick: bool = False):
        self.verbose = verbose
        self.quick = quick
        self.results: Dict[str, List[Tuple[str, bool, str]]] = {
            'llm': [],
            'sql': [],
            'nosql': [],
            'graph': [],
            'graphql': []
        }
        load_dotenv()

    def test_llm_providers(self):
        """Test LLM provider configuration and connectivity"""
        print_header("Testing LLM Providers")
        
        provider = os.getenv('MCP_LLM_PROVIDER', '').lower()
        model = os.getenv('MCP_LLM_MODEL', '')
        
        if not provider:
            print_error("MCP_LLM_PROVIDER not set in .env file")
            self.results['llm'].append(('Provider Config', False, 'Not configured'))
            return
        
        print_info(f"Configured Provider: {provider}")
        print_info(f"Configured Model: {model}")
        
        # Test OpenAI
        if provider == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                print_error("OPENAI_API_KEY not set")
                self.results['llm'].append(('OpenAI', False, 'API key missing'))
            else:
                try:
                    import openai
                    client = openai.OpenAI(api_key=api_key)
                    # Test with a minimal request
                    if not self.quick:
                        response = client.chat.completions.create(
                            model=model or "gpt-3.5-turbo",
                            messages=[{"role": "user", "content": "test"}],
                            max_tokens=5
                        )
                        print_success(f"OpenAI API connection successful (Model: {model})")
                        self.results['llm'].append(('OpenAI', True, 'Connected'))
                    else:
                        print_success("OpenAI API key configured (skipped connection test)")
                        self.results['llm'].append(('OpenAI', True, 'Key configured'))
                except ImportError:
                    print_error("openai package not installed. Run: pip install openai")
                    self.results['llm'].append(('OpenAI', False, 'Package missing'))
                except Exception as e:
                    print_error(f"OpenAI connection failed: {str(e)}")
                    self.results['llm'].append(('OpenAI', False, str(e)))
        
        # Test Anthropic
        elif provider == 'anthropic':
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                print_error("ANTHROPIC_API_KEY not set")
                self.results['llm'].append(('Anthropic', False, 'API key missing'))
            else:
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=api_key)
                    if not self.quick:
                        response = client.messages.create(
                            model=model or "claude-3-haiku-20240307",
                            max_tokens=10,
                            messages=[{"role": "user", "content": "test"}]
                        )
                        print_success(f"Anthropic API connection successful (Model: {model})")
                        self.results['llm'].append(('Anthropic', True, 'Connected'))
                    else:
                        print_success("Anthropic API key configured (skipped connection test)")
                        self.results['llm'].append(('Anthropic', True, 'Key configured'))
                except ImportError:
                    print_error("anthropic package not installed. Run: pip install anthropic")
                    self.results['llm'].append(('Anthropic', False, 'Package missing'))
                except Exception as e:
                    print_error(f"Anthropic connection failed: {str(e)}")
                    self.results['llm'].append(('Anthropic', False, str(e)))
        else:
            print_error(f"Unknown provider: {provider}")
            self.results['llm'].append(('Provider', False, f'Unknown: {provider}'))

    def test_sql_databases(self):
        """Test SQL database connections"""
        print_header("Testing SQL Databases")
        
        # Test MySQL
        if os.getenv('MYSQL_HOST'):
            try:
                import pymysql
                conn = pymysql.connect(
                    host=os.getenv('MYSQL_HOST'),
                    port=int(os.getenv('MYSQL_PORT', 3306)),
                    user=os.getenv('MYSQL_USER'),
                    password=os.getenv('MYSQL_PASSWORD'),
                    database=os.getenv('MYSQL_DATABASE'),
                    connect_timeout=5
                )
                conn.close()
                print_success(f"MySQL connection successful ({os.getenv('MYSQL_HOST')})")
                self.results['sql'].append(('MySQL', True, 'Connected'))
            except ImportError:
                print_error("pymysql not installed. Run: pip install pymysql")
                self.results['sql'].append(('MySQL', False, 'Package missing'))
            except Exception as e:
                print_error(f"MySQL connection failed: {str(e)}")
                self.results['sql'].append(('MySQL', False, str(e)))
        
        # Test PostgreSQL
        if os.getenv('POSTGRESQL_HOST'):
            try:
                import psycopg2
                conn = psycopg2.connect(
                    host=os.getenv('POSTGRESQL_HOST'),
                    port=int(os.getenv('POSTGRESQL_PORT', 5432)),
                    user=os.getenv('POSTGRESQL_USER'),
                    password=os.getenv('POSTGRESQL_PASSWORD'),
                    database=os.getenv('POSTGRESQL_DATABASE'),
                    connect_timeout=5
                )
                conn.close()
                print_success(f"PostgreSQL connection successful ({os.getenv('POSTGRESQL_HOST')})")
                self.results['sql'].append(('PostgreSQL', True, 'Connected'))
            except ImportError:
                print_error("psycopg2 not installed. Run: pip install psycopg2-binary")
                self.results['sql'].append(('PostgreSQL', False, 'Package missing'))
            except Exception as e:
                print_error(f"PostgreSQL connection failed: {str(e)}")
                self.results['sql'].append(('PostgreSQL', False, str(e)))
        
        # Test Oracle
        if os.getenv('ORACLE_HOST'):
            try:
                import cx_Oracle
                dsn = cx_Oracle.makedsn(
                    os.getenv('ORACLE_HOST'),
                    int(os.getenv('ORACLE_PORT', 1521)),
                    service_name=os.getenv('ORACLE_SERVICE_NAME')
                )
                conn = cx_Oracle.connect(
                    user=os.getenv('ORACLE_USER'),
                    password=os.getenv('ORACLE_PASSWORD'),
                    dsn=dsn
                )
                conn.close()
                print_success(f"Oracle connection successful ({os.getenv('ORACLE_HOST')})")
                self.results['sql'].append(('Oracle', True, 'Connected'))
            except ImportError:
                print_error("cx_Oracle not installed. Run: pip install cx_Oracle")
                self.results['sql'].append(('Oracle', False, 'Package missing'))
            except Exception as e:
                print_error(f"Oracle connection failed: {str(e)}")
                self.results['sql'].append(('Oracle', False, str(e)))
        
        # Test MS SQL Server
        if os.getenv('MSSQL_HOST'):
            try:
                import pyodbc
                conn_str = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={os.getenv('MSSQL_HOST')},{os.getenv('MSSQL_PORT', 1433)};"
                    f"DATABASE={os.getenv('MSSQL_DATABASE')};"
                    f"UID={os.getenv('MSSQL_USER')};"
                    f"PWD={os.getenv('MSSQL_PASSWORD')}"
                )
                conn = pyodbc.connect(conn_str, timeout=5)
                conn.close()
                print_success(f"MS SQL Server connection successful ({os.getenv('MSSQL_HOST')})")
                self.results['sql'].append(('MS SQL Server', True, 'Connected'))
            except ImportError:
                print_error("pyodbc not installed. Run: pip install pyodbc")
                self.results['sql'].append(('MS SQL Server', False, 'Package missing'))
            except Exception as e:
                print_error(f"MS SQL Server connection failed: {str(e)}")
                self.results['sql'].append(('MS SQL Server', False, str(e)))
        
        # Test Snowflake
        if os.getenv('SNOWFLAKE_ACCOUNT'):
            try:
                import snowflake.connector
                conn = snowflake.connector.connect(
                    account=os.getenv('SNOWFLAKE_ACCOUNT'),
                    user=os.getenv('SNOWFLAKE_USER'),
                    password=os.getenv('SNOWFLAKE_PASSWORD'),
                    database=os.getenv('SNOWFLAKE_DATABASE'),
                    schema=os.getenv('SNOWFLAKE_SCHEMA'),
                    warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
                    login_timeout=10
                )
                conn.close()
                print_success(f"Snowflake connection successful ({os.getenv('SNOWFLAKE_ACCOUNT')})")
                self.results['sql'].append(('Snowflake', True, 'Connected'))
            except ImportError:
                print_error("snowflake-connector-python not installed")
                self.results['sql'].append(('Snowflake', False, 'Package missing'))
            except Exception as e:
                print_error(f"Snowflake connection failed: {str(e)}")
                self.results['sql'].append(('Snowflake', False, str(e)))
        
        if not any([os.getenv('MYSQL_HOST'), os.getenv('POSTGRESQL_HOST'), 
                    os.getenv('ORACLE_HOST'), os.getenv('MSSQL_HOST'), 
                    os.getenv('SNOWFLAKE_ACCOUNT')]):
            print_warning("No SQL databases configured")

    def test_nosql_databases(self):
        """Test NoSQL database connections"""
        print_header("Testing NoSQL Databases")
        
        # Test MongoDB
        if os.getenv('MONGODB_URI'):
            try:
                from pymongo import MongoClient
                from pymongo.server_api import ServerApi
                client = MongoClient(
                    os.getenv('MONGODB_URI'),
                    server_api=ServerApi('1'),
                    serverSelectionTimeoutMS=5000
                )
                # Test connection
                client.admin.command('ping')
                db_name = os.getenv('MONGODB_DATABASE', 'test')
                db = client[db_name]
                print_success(f"MongoDB connection successful (Database: {db_name})")
                self.results['nosql'].append(('MongoDB', True, 'Connected'))
                client.close()
            except ImportError:
                print_error("pymongo not installed. Run: pip install pymongo")
                self.results['nosql'].append(('MongoDB', False, 'Package missing'))
            except Exception as e:
                print_error(f"MongoDB connection failed: {str(e)}")
                self.results['nosql'].append(('MongoDB', False, str(e)))
        
        # Test Redis
        if os.getenv('REDIS_HOST'):
            try:
                import redis
                client = redis.Redis(
                    host=os.getenv('REDIS_HOST'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    password=os.getenv('REDIS_PASSWORD'),
                    db=int(os.getenv('REDIS_DB', 0)),
                    socket_connect_timeout=5
                )
                client.ping()
                print_success(f"Redis connection successful ({os.getenv('REDIS_HOST')})")
                self.results['nosql'].append(('Redis', True, 'Connected'))
            except ImportError:
                print_error("redis not installed. Run: pip install redis")
                self.results['nosql'].append(('Redis', False, 'Package missing'))
            except Exception as e:
                print_error(f"Redis connection failed: {str(e)}")
                self.results['nosql'].append(('Redis', False, str(e)))
        
        # Test Cassandra
        if os.getenv('CASSANDRA_HOST'):
            try:
                from cassandra.cluster import Cluster
                from cassandra.auth import PlainTextAuthProvider
                
                auth_provider = None
                if os.getenv('CASSANDRA_USER'):
                    auth_provider = PlainTextAuthProvider(
                        username=os.getenv('CASSANDRA_USER'),
                        password=os.getenv('CASSANDRA_PASSWORD')
                    )
                
                cluster = Cluster(
                    [os.getenv('CASSANDRA_HOST')],
                    port=int(os.getenv('CASSANDRA_PORT', 9042)),
                    auth_provider=auth_provider,
                    connect_timeout=5
                )
                session = cluster.connect()
                cluster.shutdown()
                print_success(f"Cassandra connection successful ({os.getenv('CASSANDRA_HOST')})")
                self.results['nosql'].append(('Cassandra', True, 'Connected'))
            except ImportError:
                print_error("cassandra-driver not installed. Run: pip install cassandra-driver")
                self.results['nosql'].append(('Cassandra', False, 'Package missing'))
            except Exception as e:
                print_error(f"Cassandra connection failed: {str(e)}")
                self.results['nosql'].append(('Cassandra', False, str(e)))
        
        # Test DynamoDB
        if os.getenv('AWS_REGION'):
            try:
                import boto3
                dynamodb = boto3.resource(
                    'dynamodb',
                    region_name=os.getenv('AWS_REGION'),
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                )
                # List tables to test connection
                client = boto3.client(
                    'dynamodb',
                    region_name=os.getenv('AWS_REGION'),
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                )
                client.list_tables()
                print_success(f"DynamoDB connection successful (Region: {os.getenv('AWS_REGION')})")
                self.results['nosql'].append(('DynamoDB', True, 'Connected'))
            except ImportError:
                print_error("boto3 not installed. Run: pip install boto3")
                self.results['nosql'].append(('DynamoDB', False, 'Package missing'))
            except Exception as e:
                print_error(f"DynamoDB connection failed: {str(e)}")
                self.results['nosql'].append(('DynamoDB', False, str(e)))
        
        if not any([os.getenv('MONGODB_URI'), os.getenv('REDIS_HOST'), 
                    os.getenv('CASSANDRA_HOST'), os.getenv('AWS_REGION')]):
            print_warning("No NoSQL databases configured")

    def test_graph_databases(self):
        """Test Graph database connections"""
        print_header("Testing Graph Databases")
        
        # Test Neo4j
        if os.getenv('NEO4J_URI'):
            try:
                from neo4j import GraphDatabase
                driver = GraphDatabase.driver(
                    os.getenv('NEO4J_URI'),
                    auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
                )
                driver.verify_connectivity()
                driver.close()
                print_success(f"Neo4j connection successful ({os.getenv('NEO4J_URI')})")
                self.results['graph'].append(('Neo4j', True, 'Connected'))
            except ImportError:
                print_error("neo4j not installed. Run: pip install neo4j")
                self.results['graph'].append(('Neo4j', False, 'Package missing'))
            except Exception as e:
                print_error(f"Neo4j connection failed: {str(e)}")
                self.results['graph'].append(('Neo4j', False, str(e)))
        
        # Test ArangoDB
        if os.getenv('ARANGO_HOST'):
            try:
                from arango import ArangoClient
                client = ArangoClient(hosts=f"http://{os.getenv('ARANGO_HOST')}:{os.getenv('ARANGO_PORT', 8529)}")
                db = client.db(
                    os.getenv('ARANGO_DATABASE', '_system'),
                    username=os.getenv('ARANGO_USER', 'root'),
                    password=os.getenv('ARANGO_PASSWORD')
                )
                db.version()
                print_success(f"ArangoDB connection successful ({os.getenv('ARANGO_HOST')})")
                self.results['graph'].append(('ArangoDB', True, 'Connected'))
            except ImportError:
                print_error("python-arango not installed. Run: pip install python-arango")
                self.results['graph'].append(('ArangoDB', False, 'Package missing'))
            except Exception as e:
                print_error(f"ArangoDB connection failed: {str(e)}")
                self.results['graph'].append(('ArangoDB', False, str(e)))
        
        # Test Neptune (Gremlin)
        if os.getenv('NEPTUNE_ENDPOINT'):
            try:
                from gremlin_python.driver import client, serializer
                neptune_client = client.Client(
                    f"wss://{os.getenv('NEPTUNE_ENDPOINT')}:{os.getenv('NEPTUNE_PORT', 8182)}/gremlin",
                    'g',
                    message_serializer=serializer.GraphSONSerializersV2d0()
                )
                # Simple test query
                result = neptune_client.submit('g.V().limit(1)').all().result()
                neptune_client.close()
                print_success(f"Neptune connection successful ({os.getenv('NEPTUNE_ENDPOINT')})")
                self.results['graph'].append(('Neptune', True, 'Connected'))
            except ImportError:
                print_error("gremlinpython not installed. Run: pip install gremlinpython")
                self.results['graph'].append(('Neptune', False, 'Package missing'))
            except Exception as e:
                print_error(f"Neptune connection failed: {str(e)}")
                self.results['graph'].append(('Neptune', False, str(e)))
        
        if not any([os.getenv('NEO4J_URI'), os.getenv('ARANGO_HOST'), 
                    os.getenv('NEPTUNE_ENDPOINT')]):
            print_warning("No Graph databases configured")
    
    def test_graphql_apis(self):
        """Test GraphQL API connections"""
        print_header("Testing GraphQL APIs")
        
        # Test Generic GraphQL endpoint
        if os.getenv('GRAPHQL_ENDPOINT'):
            try:
                import httpx
                endpoint = os.getenv('GRAPHQL_ENDPOINT')
                headers = {}
                if os.getenv('GRAPHQL_API_TOKEN'):
                    headers['Authorization'] = f"Bearer {os.getenv('GRAPHQL_API_TOKEN')}"
                
                # Test with introspection query
                introspection_query = '{ __schema { queryType { name } } }'
                response = httpx.post(
                    endpoint,
                    json={'query': introspection_query},
                    headers=headers,
                    timeout=10
                )
                if response.status_code == 200:
                    print_success(f"GraphQL API connection successful ({endpoint})")
                    self.results['graphql'].append(('GraphQL API', True, 'Connected'))
                else:
                    print_error(f"GraphQL API returned status {response.status_code}")
                    self.results['graphql'].append(('GraphQL API', False, f'Status {response.status_code}'))
            except ImportError:
                print_error("httpx not installed. Run: pip install httpx")
                self.results['graphql'].append(('GraphQL API', False, 'Package missing'))
            except Exception as e:
                print_error(f"GraphQL API connection failed: {str(e)}")
                self.results['graphql'].append(('GraphQL API', False, str(e)))
        
        # Test Saleor API
        if os.getenv('SALEOR_API_ENDPOINT'):
            try:
                import httpx
                endpoint = os.getenv('SALEOR_API_ENDPOINT')
                headers = {}
                if os.getenv('SALEOR_API_TOKEN'):
                    headers['Authorization'] = f"Bearer {os.getenv('SALEOR_API_TOKEN')}"
                
                introspection_query = '{ __schema { queryType { name } } }'
                response = httpx.post(
                    endpoint,
                    json={'query': introspection_query},
                    headers=headers,
                    timeout=10
                )
                if response.status_code == 200:
                    print_success(f"Saleor API connection successful ({endpoint})")
                    self.results['graphql'].append(('Saleor API', True, 'Connected'))
                else:
                    print_error(f"Saleor API returned status {response.status_code}")
                    self.results['graphql'].append(('Saleor API', False, f'Status {response.status_code}'))
            except ImportError:
                print_error("httpx not installed. Run: pip install httpx")
                self.results['graphql'].append(('Saleor API', False, 'Package missing'))
            except Exception as e:
                print_error(f"Saleor API connection failed: {str(e)}")
                self.results['graphql'].append(('Saleor API', False, str(e)))
        
        if not any([os.getenv('GRAPHQL_ENDPOINT'), os.getenv('SALEOR_API_ENDPOINT')]):
            print_warning("No GraphQL APIs configured")

    def print_summary(self):
        """Print test summary"""
        print_header("Test Summary")
        
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for category, tests in self.results.items():
            if tests:
                print(f"\n{Colors.BOLD}{category.upper()}:{Colors.RESET}")
                for name, passed, message in tests:
                    total_tests += 1
                    if passed:
                        total_passed += 1
                        print_success(f"{name}: {message}")
                    else:
                        total_failed += 1
                        print_error(f"{name}: {message}")
        
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Total Tests: {total_tests}{Colors.RESET}")
        print(f"{Colors.GREEN}Passed: {total_passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {total_failed}{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
        
        if total_failed == 0 and total_tests > 0:
            print_success("All configured connections are working! ✨")
            print_info("You can now run the MCP server with: python server.py")
            print_info("\nTip: Run this test script again if you:")
            print_info("  • Change your .env configuration")
            print_info("  • Experience connection issues")
            print_info("  • Update database infrastructure")
            return 0
        elif total_tests == 0:
            print_warning("No connections configured. Please set up your .env file.")
            print_info("See SETUP_GUIDE.md for configuration instructions.")
            print_info("\nMinimal setup requires:")
            print_info("  1. LLM provider (OpenAI or Anthropic)")
            print_info("  2. At least one database connection")
            return 1
        else:
            print_error(f"{total_failed} connection(s) failed. Please check your configuration.")
            print_info("Review the errors above and update your .env file accordingly.")
            print_info("\nCommon fixes:")
            print_info("  • Verify credentials in .env file")
            print_info("  • Check network connectivity")
            print_info("  • Install missing packages: pip install -r requirements.txt")
            print_info("  • Review SETUP_GUIDE.md for detailed instructions")
            return 1
    
    def run_all_tests(self):
        """Run all connectivity tests"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}")
        print("╔════════════════════════════════════════════════════════════╗")
        print("║  MCP Natural Language to Data Endpoints - Setup Test       ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print(f"{Colors.RESET}")
        
        if self.quick:
            print_info("Running in QUICK mode (skipping slow tests)")
        
        self.test_llm_providers()
        self.test_sql_databases()
        self.test_nosql_databases()
        self.test_graph_databases()
        self.test_graphql_apis()
        
        return self.print_summary()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Test MCP Natural Language to Data Endpoints setup'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='Skip slow tests (e.g., actual LLM API calls)'
    )
    
    args = parser.parse_args()
    
    # Check if .env file exists
    if not os.path.exists('../.env') and not os.path.exists('.env'):
        print_error("No .env file found!")
        print_info("Please copy .env.example to .env and configure your credentials.")
        print_info("Run: cp ../.env.example ../.env")
        return 1
    
    tester = SetupTester(verbose=args.verbose, quick=args.quick)
    return tester.run_all_tests()

if __name__ == '__main__':
    sys.exit(main())
