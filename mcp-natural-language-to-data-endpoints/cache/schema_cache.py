"""
Schema caching system for database metadata
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib


class SchemaCache:
    """Cache for database schemas to improve query generation performance"""
    
    def __init__(self, cache_dir: str = ".cache", ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.ttl = timedelta(hours=ttl_hours)
        os.makedirs(cache_dir, exist_ok=True)
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached schema if available and not expired"""
        cache_file = self._get_cache_file(key)
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            
            # Check if cache is expired
            cached_time = datetime.fromisoformat(cached_data['timestamp'])
            if datetime.now() - cached_time > self.ttl:
                os.remove(cache_file)
                return None
            
            return cached_data['schema']
        
        except Exception:
            return None
    
    def set(self, key: str, schema: Dict[str, Any]) -> None:
        """Cache schema with timestamp"""
        cache_file = self._get_cache_file(key)
        
        cached_data = {
            'timestamp': datetime.now().isoformat(),
            'schema': schema
        }
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(cached_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to cache schema: {e}")
    
    def invalidate(self, key: str) -> None:
        """Invalidate cached schema"""
        cache_file = self._get_cache_file(key)
        if os.path.exists(cache_file):
            os.remove(cache_file)
    
    def clear_all(self) -> None:
        """Clear all cached schemas"""
        for file in os.listdir(self.cache_dir):
            if file.endswith('.json'):
                os.remove(os.path.join(self.cache_dir, file))
    
    def _get_cache_file(self, key: str) -> str:
        """Generate cache file path from key"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.json")
