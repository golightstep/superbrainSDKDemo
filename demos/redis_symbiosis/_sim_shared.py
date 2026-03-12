import time
import os
import json
import redis

# This module mocks the 'superbrain' SDK when it's not installed locally.
# Because the real SDK uses mmap/RDMA to share memory natively, we must 
# mock it using Redis just so the 3 separate GCP VMs can communicate for the demo.

class MockFabric:
    def create_context(self, name, size_mb=100):
        return MockContext(name)
        
    def attach_context(self, name):
        return MockContext(name)

class MockContext:
    def __init__(self, name):
        self.name = name
        # Use the Iowa IP if provided via env var, else local
        host = os.environ.get("REDIS_HOST", "127.0.0.1")
        self.r = redis.Redis(host=host, port=6379, decode_responses=True)
        # Verify connection
        try:
            self.r.ping()
        except:
            pass
        
    def write(self, key, value):
        self.r.set(f"mock_sb:{self.name}:{key}", json.dumps(value))
        
    def read(self, key):
        val = self.r.get(f"mock_sb:{self.name}:{key}")
        if val:
            return json.loads(val)
        return None
