"""
Graph Database Connector
Supports Neo4j, ArangoDB, GraphDB, Amazon Neptune, Azure CosmosDB
"""

import os
from typing import Dict, Any, List, Optional
from cache.schema_cache import SchemaCache


class GraphConnector:
    """Connector for graph databases with schema introspection"""
    
    def __init__(self, cache: SchemaCache):
        self.cache = cache
        self.clients: Dict[str, Any] = {}
    
    async def get_schema(self, database_type: str) -> Dict[str, Any]:
        """Get database schema from cache or fetch it"""
        cache_key = f"graph_{database_type}"
        
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
        cache_key = f"graph_{database_type}"
        self.cache.invalidate(cache_key)
        await self.get_schema(database_type)
    
    async def _fetch_schema(self, database_type: str) -> Dict[str, Any]:
        """Fetch schema from graph database"""
        if database_type == "neo4j":
            return await self._fetch_neo4j_schema()
        elif database_type == "arangodb":
            return await self._fetch_arangodb_schema()
        elif database_type == "graphdb":
            return await self._fetch_graphdb_schema()
        elif database_type == "neptune":
            return await self._fetch_neptune_schema()
        elif database_type == "cosmosdb":
            return await self._fetch_cosmosdb_schema()
        else:
            raise ValueError(f"Unsupported graph database type: {database_type}")
    
    async def _fetch_neo4j_schema(self) -> Dict[str, Any]:
        """Fetch Neo4j schema"""
        from neo4j import GraphDatabase
        
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        schema = {
            "database_type": "neo4j",
            "node_labels": [],
            "relationship_types": [],
            "constraints": [],
            "indexes": []
        }
        
        with driver.session() as session:
            # Get node labels with properties
            labels_result = session.run("CALL db.labels()")
            for record in labels_result:
                label = record[0]
                
                # Get properties for this label
                props_query = f"MATCH (n:{label}) RETURN DISTINCT keys(n) AS props LIMIT 100"
                props_result = session.run(props_query)
                
                all_props = set()
                for prop_record in props_result:
                    all_props.update(prop_record["props"])
                
                schema["node_labels"].append({
                    "label": label,
                    "properties": list(all_props)
                })
            
            # Get relationship types with properties
            rels_result = session.run("CALL db.relationshipTypes()")
            for record in rels_result:
                rel_type = record[0]
                
                # Get properties and connected node types
                rel_query = f"MATCH (a)-[r:{rel_type}]->(b) RETURN DISTINCT labels(a) AS from_labels, labels(b) AS to_labels, keys(r) AS props LIMIT 100"
                rel_details = session.run(rel_query)
                
                relationships = []
                for rel_record in rel_details:
                    relationships.append({
                        "from": rel_record["from_labels"],
                        "to": rel_record["to_labels"],
                        "properties": rel_record["props"]
                    })
                
                schema["relationship_types"].append({
                    "type": rel_type,
                    "relationships": relationships
                })
            
            # Get constraints
            constraints_result = session.run("SHOW CONSTRAINTS")
            for record in constraints_result:
                schema["constraints"].append({
                    "name": record.get("name"),
                    "type": record.get("type"),
                    "entity_type": record.get("entityType"),
                    "properties": record.get("properties")
                })
            
            # Get indexes
            indexes_result = session.run("SHOW INDEXES")
            for record in indexes_result:
                schema["indexes"].append({
                    "name": record.get("name"),
                    "type": record.get("type"),
                    "entity_type": record.get("entityType"),
                    "properties": record.get("properties")
                })
        
        driver.close()
        return schema
    
    async def _fetch_arangodb_schema(self) -> Dict[str, Any]:
        """Fetch ArangoDB schema"""
        from arango import ArangoClient
        
        host = os.getenv("ARANGODB_HOST", "http://localhost:8529")
        user = os.getenv("ARANGODB_USER", "root")
        password = os.getenv("ARANGODB_PASSWORD", "")
        database = os.getenv("ARANGODB_DATABASE", "_system")
        
        client = ArangoClient(hosts=host)
        db = client.db(database, username=user, password=password)
        
        schema = {
            "database_type": "arangodb",
            "collections": [],
            "graphs": []
        }
        
        # Get all collections
        for collection in db.collections():
            if not collection['name'].startswith('_'):
                coll = db.collection(collection['name'])
                
                # Sample documents to infer schema
                sample_docs = list(coll.all(limit=100))
                properties = set()
                for doc in sample_docs:
                    properties.update(doc.keys())
                
                schema["collections"].append({
                    "name": collection['name'],
                    "type": collection['type'],
                    "properties": list(properties)
                })
        
        # Get graph definitions
        for graph in db.graphs():
            graph_obj = db.graph(graph['name'])
            
            edge_definitions = []
            for edge_def in graph['edgeDefinitions']:
                edge_definitions.append({
                    "collection": edge_def['collection'],
                    "from": edge_def['from'],
                    "to": edge_def['to']
                })
            
            schema["graphs"].append({
                "name": graph['name'],
                "edge_definitions": edge_definitions
            })
        
        return schema
    
    async def _fetch_graphdb_schema(self) -> Dict[str, Any]:
        """Fetch GraphDB (RDF) schema"""
        from SPARQLWrapper import SPARQLWrapper, JSON
        
        endpoint = os.getenv("GRAPHDB_ENDPOINT", "http://localhost:7200/repositories/")
        repository = os.getenv("GRAPHDB_REPOSITORY", "")
        
        sparql = SPARQLWrapper(f"{endpoint}{repository}")
        
        schema = {
            "database_type": "graphdb",
            "classes": [],
            "properties": []
        }
        
        # Get all classes
        sparql.setQuery("""
            SELECT DISTINCT ?class (COUNT(?instance) AS ?count)
            WHERE {
                ?instance a ?class .
            }
            GROUP BY ?class
            ORDER BY DESC(?count)
            LIMIT 100
        """)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        
        for result in results["results"]["bindings"]:
            schema["classes"].append({
                "uri": result["class"]["value"],
                "instance_count": int(result["count"]["value"])
            })
        
        # Get all properties
        sparql.setQuery("""
            SELECT DISTINCT ?property (COUNT(?s) AS ?count)
            WHERE {
                ?s ?property ?o .
                FILTER(!isBlank(?property))
            }
            GROUP BY ?property
            ORDER BY DESC(?count)
            LIMIT 100
        """)
        results = sparql.query().convert()
        
        for result in results["results"]["bindings"]:
            schema["properties"].append({
                "uri": result["property"]["value"],
                "usage_count": int(result["count"]["value"])
            })
        
        return schema
    
    async def _fetch_neptune_schema(self) -> Dict[str, Any]:
        """Fetch Amazon Neptune schema (Gremlin)"""
        from gremlin_python.driver import client, serializer
        
        endpoint = os.getenv("NEPTUNE_ENDPOINT", "")
        port = int(os.getenv("NEPTUNE_PORT", "8182"))
        
        gremlin_client = client.Client(
            f'wss://{endpoint}:{port}/gremlin',
            'g',
            message_serializer=serializer.GraphSONSerializersV2d0()
        )
        
        schema = {
            "database_type": "neptune",
            "vertex_labels": [],
            "edge_labels": []
        }
        
        # Get vertex labels
        vertex_labels = gremlin_client.submit("g.V().label().dedup()").all().result()
        
        for label in vertex_labels:
            # Get properties for this label
            props = gremlin_client.submit(
                f"g.V().hasLabel('{label}').limit(100).properties().key().dedup()"
            ).all().result()
            
            schema["vertex_labels"].append({
                "label": label,
                "properties": props
            })
        
        # Get edge labels
        edge_labels = gremlin_client.submit("g.E().label().dedup()").all().result()
        
        for label in edge_labels:
            # Get properties and connections
            props = gremlin_client.submit(
                f"g.E().hasLabel('{label}').limit(100).properties().key().dedup()"
            ).all().result()
            
            connections = gremlin_client.submit(
                f"g.E().hasLabel('{label}').limit(100).project('from', 'to').by(outV().label()).by(inV().label()).dedup()"
            ).all().result()
            
            schema["edge_labels"].append({
                "label": label,
                "properties": props,
                "connections": connections
            })
        
        gremlin_client.close()
        return schema
    
    async def _fetch_cosmosdb_schema(self) -> Dict[str, Any]:
        """Fetch Azure CosmosDB (Gremlin API) schema"""
        from gremlin_python.driver import client, serializer
        
        endpoint = os.getenv("COSMOSDB_ENDPOINT", "")
        key = os.getenv("COSMOSDB_KEY", "")
        database = os.getenv("COSMOSDB_DATABASE", "")
        collection = os.getenv("COSMOSDB_COLLECTION", "")
        
        gremlin_client = client.Client(
            f'wss://{endpoint}:443/',
            'g',
            username=f"/dbs/{database}/colls/{collection}",
            password=key,
            message_serializer=serializer.GraphSONSerializersV2d0()
        )
        
        schema = {
            "database_type": "cosmosdb",
            "vertex_labels": [],
            "edge_labels": []
        }
        
        # Get vertex labels
        vertex_labels = gremlin_client.submit("g.V().label().dedup()").all().result()
        
        for label in vertex_labels:
            props = gremlin_client.submit(
                f"g.V().hasLabel('{label}').limit(100).properties().key().dedup()"
            ).all().result()
            
            schema["vertex_labels"].append({
                "label": label,
                "properties": props
            })
        
        # Get edge labels
        edge_labels = gremlin_client.submit("g.E().label().dedup()").all().result()
        
        for label in edge_labels:
            props = gremlin_client.submit(
                f"g.E().hasLabel('{label}').limit(100).properties().key().dedup()"
            ).all().result()
            
            schema["edge_labels"].append({
                "label": label,
                "properties": props
            })
        
        gremlin_client.close()
        return schema
    
    async def execute_query(self, query: str, database_type: str) -> List[Dict[str, Any]]:
        """Execute graph query and return results"""
        if database_type == "neo4j":
            return await self._execute_neo4j(query)
        elif database_type == "arangodb":
            return await self._execute_arangodb(query)
        elif database_type == "graphdb":
            return await self._execute_graphdb(query)
        elif database_type in ["neptune", "cosmosdb"]:
            return await self._execute_gremlin(query, database_type)
        else:
            raise ValueError(f"Unsupported graph database type: {database_type}")
    
    async def _execute_neo4j(self, query: str) -> List[Dict[str, Any]]:
        """Execute Neo4j Cypher query"""
        from neo4j import GraphDatabase
        
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            result = session.run(query)
            records = [dict(record) for record in result]
        
        driver.close()
        return records
    
    async def _execute_arangodb(self, query: str) -> List[Dict[str, Any]]:
        """Execute ArangoDB AQL query"""
        from arango import ArangoClient
        
        host = os.getenv("ARANGODB_HOST", "http://localhost:8529")
        user = os.getenv("ARANGODB_USER", "root")
        password = os.getenv("ARANGODB_PASSWORD", "")
        database = os.getenv("ARANGODB_DATABASE", "_system")
        
        client = ArangoClient(hosts=host)
        db = client.db(database, username=user, password=password)
        
        cursor = db.aql.execute(query)
        results = list(cursor)
        
        return results
    
    async def _execute_graphdb(self, query: str) -> List[Dict[str, Any]]:
        """Execute GraphDB SPARQL query"""
        from SPARQLWrapper import SPARQLWrapper, JSON
        
        endpoint = os.getenv("GRAPHDB_ENDPOINT", "http://localhost:7200/repositories/")
        repository = os.getenv("GRAPHDB_REPOSITORY", "")
        
        sparql = SPARQLWrapper(f"{endpoint}{repository}")
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        
        results = sparql.query().convert()
        
        return results["results"]["bindings"]
    
    async def _execute_gremlin(self, query: str, database_type: str) -> List[Dict[str, Any]]:
        """Execute Gremlin query (Neptune/CosmosDB)"""
        from gremlin_python.driver import client, serializer
        
        if database_type == "neptune":
            endpoint = os.getenv("NEPTUNE_ENDPOINT", "")
            port = int(os.getenv("NEPTUNE_PORT", "8182"))
            
            gremlin_client = client.Client(
                f'wss://{endpoint}:{port}/gremlin',
                'g',
                message_serializer=serializer.GraphSONSerializersV2d0()
            )
        else:  # cosmosdb
            endpoint = os.getenv("COSMOSDB_ENDPOINT", "")
            key = os.getenv("COSMOSDB_KEY", "")
            database = os.getenv("COSMOSDB_DATABASE", "")
            collection = os.getenv("COSMOSDB_COLLECTION", "")
            
            gremlin_client = client.Client(
                f'wss://{endpoint}:443/',
                'g',
                username=f"/dbs/{database}/colls/{collection}",
                password=key,
                message_serializer=serializer.GraphSONSerializersV2d0()
            )
        
        results = gremlin_client.submit(query).all().result()
        gremlin_client.close()
        
        return [{"result": r} for r in results]
