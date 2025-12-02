"""
GraphQL API Connector
Supports various GraphQL APIs including Saleor
"""

import os
from typing import Dict, Any, List, Optional
import httpx
from cache.schema_cache import SchemaCache


class GraphQLConnector:
    """Connector for GraphQL APIs with schema introspection"""
    
    def __init__(self, cache: SchemaCache):
        self.cache = cache
    
    async def get_schema(self, api_endpoint: str) -> Dict[str, Any]:
        """Get GraphQL schema from cache or fetch it"""
        cache_key = f"graphql_{api_endpoint}"
        
        # Try cache first
        cached_schema = self.cache.get(cache_key)
        if cached_schema:
            return cached_schema
        
        # Fetch schema
        schema = await self._fetch_schema(api_endpoint)
        
        # Cache it
        self.cache.set(cache_key, schema)
        
        return schema
    
    async def refresh_schema(self, api_endpoint: str) -> None:
        """Force refresh of schema cache"""
        cache_key = f"graphql_{api_endpoint}"
        self.cache.invalidate(cache_key)
        await self.get_schema(api_endpoint)
    
    async def _fetch_schema(self, api_endpoint: str) -> Dict[str, Any]:
        """Fetch GraphQL schema using introspection query"""
        introspection_query = """
        query IntrospectionQuery {
            __schema {
                queryType { name }
                mutationType { name }
                subscriptionType { name }
                types {
                    ...FullType
                }
                directives {
                    name
                    description
                    locations
                    args {
                        ...InputValue
                    }
                }
            }
        }
        
        fragment FullType on __Type {
            kind
            name
            description
            fields(includeDeprecated: true) {
                name
                description
                args {
                    ...InputValue
                }
                type {
                    ...TypeRef
                }
                isDeprecated
                deprecationReason
            }
            inputFields {
                ...InputValue
            }
            interfaces {
                ...TypeRef
            }
            enumValues(includeDeprecated: true) {
                name
                description
                isDeprecated
                deprecationReason
            }
            possibleTypes {
                ...TypeRef
            }
        }
        
        fragment InputValue on __InputValue {
            name
            description
            type { ...TypeRef }
            defaultValue
        }
        
        fragment TypeRef on __Type {
            kind
            name
            ofType {
                kind
                name
                ofType {
                    kind
                    name
                    ofType {
                        kind
                        name
                        ofType {
                            kind
                            name
                            ofType {
                                kind
                                name
                                ofType {
                                    kind
                                    name
                                    ofType {
                                        kind
                                        name
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        headers = self._get_headers(api_endpoint)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_endpoint,
                json={"query": introspection_query},
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            
            introspection_result = response.json()
        
        # Process and simplify schema
        schema = self._process_introspection_result(introspection_result, api_endpoint)
        
        return schema
    
    def _process_introspection_result(self, introspection_result: Dict[str, Any], api_endpoint: str) -> Dict[str, Any]:
        """Process introspection result into simplified schema"""
        schema_data = introspection_result.get("data", {}).get("__schema", {})
        
        schema = {
            "api_endpoint": api_endpoint,
            "query_type": schema_data.get("queryType", {}).get("name"),
            "mutation_type": schema_data.get("mutationType", {}).get("name"),
            "subscription_type": schema_data.get("subscriptionType", {}).get("name"),
            "types": {},
            "queries": [],
            "mutations": [],
            "subscriptions": []
        }
        
        # Process types
        for type_info in schema_data.get("types", []):
            type_name = type_info.get("name")
            
            # Skip internal types
            if type_name and type_name.startswith("__"):
                continue
            
            schema["types"][type_name] = {
                "kind": type_info.get("kind"),
                "description": type_info.get("description"),
                "fields": []
            }
            
            # Process fields
            if type_info.get("fields"):
                for field in type_info["fields"]:
                    field_info = {
                        "name": field.get("name"),
                        "description": field.get("description"),
                        "type": self._extract_type_name(field.get("type")),
                        "args": []
                    }
                    
                    # Process arguments
                    if field.get("args"):
                        for arg in field["args"]:
                            field_info["args"].append({
                                "name": arg.get("name"),
                                "type": self._extract_type_name(arg.get("type")),
                                "description": arg.get("description")
                            })
                    
                    schema["types"][type_name]["fields"].append(field_info)
                    
                    # Categorize root operations
                    if type_name == schema["query_type"]:
                        schema["queries"].append(field_info)
                    elif type_name == schema["mutation_type"]:
                        schema["mutations"].append(field_info)
                    elif type_name == schema["subscription_type"]:
                        schema["subscriptions"].append(field_info)
        
        return schema
    
    def _extract_type_name(self, type_ref: Optional[Dict[str, Any]]) -> str:
        """Extract type name from nested type reference"""
        if not type_ref:
            return "Unknown"
        
        kind = type_ref.get("kind")
        name = type_ref.get("name")
        
        if kind == "NON_NULL":
            inner_type = self._extract_type_name(type_ref.get("ofType"))
            return f"{inner_type}!"
        elif kind == "LIST":
            inner_type = self._extract_type_name(type_ref.get("ofType"))
            return f"[{inner_type}]"
        else:
            return name or "Unknown"
    
    async def execute_query(self, query: str, api_endpoint: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute GraphQL query and return results"""
        headers = self._get_headers(api_endpoint)
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_endpoint,
                json=payload,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            
            return response.json()
    
    def _get_headers(self, api_endpoint: str) -> Dict[str, str]:
        """Get headers for GraphQL request"""
        headers = {
            "Content-Type": "application/json"
        }
        
        # Check for API-specific authentication
        if "saleor" in api_endpoint.lower():
            token = os.getenv("SALEOR_API_TOKEN")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        
        # Generic GraphQL token
        generic_token = os.getenv("GRAPHQL_API_TOKEN")
        if generic_token and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {generic_token}"
        
        # Custom headers from env
        custom_headers = os.getenv("GRAPHQL_CUSTOM_HEADERS")
        if custom_headers:
            try:
                import json
                headers.update(json.loads(custom_headers))
            except:
                pass
        
        return headers
