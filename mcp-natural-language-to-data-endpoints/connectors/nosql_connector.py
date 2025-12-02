"""
NoSQL Database Connector
Supports MongoDB, Cassandra, Redis, DynamoDB, and cloud databases
"""

import os
from typing import Dict, Any, List, Optional
from cache.schema_cache import SchemaCache


class NoSQLConnector:
    """Connector for NoSQL databases with schema introspection"""
    
    def __init__(self, cache: SchemaCache):
        self.cache = cache
        self.clients: Dict[str, Any] = {}
    
    async def get_schema(self, database_type: str) -> Dict[str, Any]:
        """Get database schema from cache or fetch it"""
        cache_key = f"nosql_{database_type}"
        
        # Try cache first
        cached_schema = self.cache.get(cache_key)
        if cached_schema:
            return cached_schema
        
        # Fetch schema
        schema = await self._fetch_schema(database_type)
        
        # Cache it
        self.cache.set(cache_key, schema)
        
        return schema
    
    async def refresh_schema(self, database_type: str) -> None:
        """Force refresh of schema cache"""
        cache_key = f"nosql_{database_type}"
        self.cache.invalidate(cache_key)
        await self.get_schema(database_type)
    
    async def _fetch_schema(self, database_type: str) -> Dict[str, Any]:
        """Fetch schema from NoSQL database"""
        if database_type == "mongodb":
            return await self._fetch_mongodb_schema()
        elif database_type == "cassandra":
            return await self._fetch_cassandra_schema()
        elif database_type == "redis":
            return await self._fetch_redis_schema()
        elif database_type == "dynamodb":
            return await self._fetch_dynamodb_schema()
        else:
            raise ValueError(f"Unsupported NoSQL database type: {database_type}")
    
    async def _fetch_mongodb_schema(self) -> Dict[str, Any]:
        """Fetch MongoDB schema"""
        from pymongo import MongoClient
        
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        database_name = os.getenv("MONGODB_DATABASE", "")
        
        client = MongoClient(uri)
        db = client[database_name]
        
        schema = {
            "database_type": "mongodb",
            "database": database_name,
            "collections": []
        }
        
        # Get all collections
        for collection_name in db.list_collection_names():
            collection = db[collection_name]
            
            # Sample documents to infer schema
            sample_docs = list(collection.find().limit(100))
            
            # Infer fields from samples
            fields = {}
            for doc in sample_docs:
                for key, value in doc.items():
                    if key not in fields:
                        fields[key] = {
                            "name": key,
                            "type": type(value).__name__,
                            "examples": []
                        }
                    if len(fields[key]["examples"]) < 3:
                        fields[key]["examples"].append(str(value)[:50])
            
            # Get indexes
            indexes = []
            for index in collection.list_indexes():
                indexes.append({
                    "name": index.get("name"),
                    "keys": list(index.get("key", {}).keys())
                })
            
            schema["collections"].append({
                "name": collection_name,
                "fields": list(fields.values()),
                "indexes": indexes,
                "document_count": collection.count_documents({})
            })
        
        client.close()
        return schema
    
    async def _fetch_cassandra_schema(self) -> Dict[str, Any]:
        """Fetch Cassandra schema"""
        from cassandra.cluster import Cluster
        
        hosts = os.getenv("CASSANDRA_HOSTS", "localhost").split(",")
        port = int(os.getenv("CASSANDRA_PORT", "9042"))
        keyspace = os.getenv("CASSANDRA_KEYSPACE", "")
        
        cluster = Cluster(hosts, port=port)
        session = cluster.connect(keyspace)
        
        schema = {
            "database_type": "cassandra",
            "keyspace": keyspace,
            "tables": []
        }
        
        # Get all tables
        rows = session.execute(f"SELECT table_name FROM system_schema.tables WHERE keyspace_name = '{keyspace}'")
        
        for row in rows:
            table_name = row.table_name
            
            # Get columns
            columns_query = f"SELECT column_name, type, kind FROM system_schema.columns WHERE keyspace_name = '{keyspace}' AND table_name = '{table_name}'"
            columns = []
            
            for col in session.execute(columns_query):
                columns.append({
                    "name": col.column_name,
                    "type": col.type,
                    "kind": col.kind
                })
            
            schema["tables"].append({
                "name": table_name,
                "columns": columns
            })
        
        cluster.shutdown()
        return schema
    
    async def _fetch_redis_schema(self) -> Dict[str, Any]:
        """Fetch Redis schema (key patterns)"""
        import redis
        
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        password = os.getenv("REDIS_PASSWORD", None)
        db = int(os.getenv("REDIS_DB", "0"))
        
        client = redis.Redis(host=host, port=port, password=password, db=db, decode_responses=True)
        
        # Sample keys to identify patterns
        keys = client.keys("*")[:1000]  # Limit to 1000 keys
        
        # Group by patterns
        patterns = {}
        for key in keys:
            key_type = client.type(key)
            pattern = self._extract_redis_pattern(key)
            
            if pattern not in patterns:
                patterns[pattern] = {
                    "pattern": pattern,
                    "type": key_type,
                    "examples": []
                }
            
            if len(patterns[pattern]["examples"]) < 5:
                patterns[pattern]["examples"].append(key)
        
        schema = {
            "database_type": "redis",
            "database": db,
            "key_patterns": list(patterns.values()),
            "total_keys": client.dbsize()
        }
        
        client.close()
        return schema
    
    async def _fetch_dynamodb_schema(self) -> Dict[str, Any]:
        """Fetch DynamoDB schema"""
        import boto3
        
        region = os.getenv("AWS_REGION", "us-east-1")
        
        dynamodb = boto3.client('dynamodb', region_name=region)
        
        schema = {
            "database_type": "dynamodb",
            "region": region,
            "tables": []
        }
        
        # List all tables
        response = dynamodb.list_tables()
        
        for table_name in response.get('TableNames', []):
            # Describe table
            table_desc = dynamodb.describe_table(TableName=table_name)
            table_info = table_desc['Table']
            
            # Get key schema
            key_schema = []
            for key in table_info.get('KeySchema', []):
                key_schema.append({
                    "attribute": key['AttributeName'],
                    "type": key['KeyType']
                })
            
            # Get attributes
            attributes = []
            for attr in table_info.get('AttributeDefinitions', []):
                attributes.append({
                    "name": attr['AttributeName'],
                    "type": attr['AttributeType']
                })
            
            # Get GSIs
            gsis = []
            for gsi in table_info.get('GlobalSecondaryIndexes', []):
                gsis.append({
                    "name": gsi['IndexName'],
                    "keys": [k['AttributeName'] for k in gsi['KeySchema']]
                })
            
            schema["tables"].append({
                "name": table_name,
                "key_schema": key_schema,
                "attributes": attributes,
                "global_secondary_indexes": gsis
            })
        
        return schema
    
    async def execute_query(self, query: Any, database_type: str) -> List[Dict[str, Any]]:
        """Execute NoSQL query and return results"""
        if database_type == "mongodb":
            return await self._execute_mongodb(query)
        elif database_type == "cassandra":
            return await self._execute_cassandra(query)
        elif database_type == "redis":
            return await self._execute_redis(query)
        elif database_type == "dynamodb":
            return await self._execute_dynamodb(query)
        else:
            raise ValueError(f"Unsupported NoSQL database type: {database_type}")
    
    async def _execute_mongodb(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute MongoDB query"""
        from pymongo import MongoClient
        
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        database_name = os.getenv("MONGODB_DATABASE", "")
        
        client = MongoClient(uri)
        db = client[database_name]
        
        collection_name = query.get("collection")
        operation = query.get("operation", "find")
        params = query.get("params", {})
        
        collection = db[collection_name]
        
        if operation == "find":
            results = list(collection.find(params))
        elif operation == "aggregate":
            results = list(collection.aggregate(params))
        else:
            results = []
        
        client.close()
        
        # Convert ObjectId to string
        for result in results:
            if '_id' in result:
                result['_id'] = str(result['_id'])
        
        return results
    
    async def _execute_cassandra(self, query: str) -> List[Dict[str, Any]]:
        """Execute Cassandra query"""
        from cassandra.cluster import Cluster
        
        hosts = os.getenv("CASSANDRA_HOSTS", "localhost").split(",")
        port = int(os.getenv("CASSANDRA_PORT", "9042"))
        keyspace = os.getenv("CASSANDRA_KEYSPACE", "")
        
        cluster = Cluster(hosts, port=port)
        session = cluster.connect(keyspace)
        
        rows = session.execute(query)
        results = [dict(row._asdict()) for row in rows]
        
        cluster.shutdown()
        return results
    
    async def _execute_redis(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute Redis command"""
        import redis
        
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        password = os.getenv("REDIS_PASSWORD", None)
        db = int(os.getenv("REDIS_DB", "0"))
        
        client = redis.Redis(host=host, port=port, password=password, db=db, decode_responses=True)
        
        command = query.get("command")
        args = query.get("args", [])
        
        result = client.execute_command(command, *args)
        
        client.close()
        
        return [{"result": result}]
    
    async def _execute_dynamodb(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute DynamoDB query"""
        import boto3
        
        region = os.getenv("AWS_REGION", "us-east-1")
        dynamodb = boto3.resource('dynamodb', region_name=region)
        
        table_name = query.get("table")
        operation = query.get("operation", "scan")
        params = query.get("params", {})
        
        table = dynamodb.Table(table_name)
        
        if operation == "scan":
            response = table.scan(**params)
        elif operation == "query":
            response = table.query(**params)
        else:
            response = {"Items": []}
        
        return response.get("Items", [])
    
    def _extract_redis_pattern(self, key: str) -> str:
        """Extract pattern from Redis key"""
        # Simple pattern extraction (can be enhanced)
        parts = key.split(":")
        if len(parts) > 1:
            return ":".join(parts[:-1]) + ":*"
        return key
