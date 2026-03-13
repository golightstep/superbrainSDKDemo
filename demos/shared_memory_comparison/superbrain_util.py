import time
import json
import os

# Use a directory for separate context files
MOCK_DIR = "/tmp/superbrain_mock"
if not os.path.exists(MOCK_DIR):
    os.makedirs(MOCK_DIR, exist_ok=True)

def get_fabric():
    use_native = os.getenv("USE_NATIVE_SUPERBRAIN", "false").lower() == "true"
    
    if use_native:
        try:
            from superbrain import DistributedContextFabric
            return DistributedContextFabric()
        except: pass

    class MockContext:
        def __init__(self, name):
            self.name = name
            self.path = os.path.join(MOCK_DIR, f"{name}.json")
        
        def write(self, k, v):
            try:
                # Read-Modify-Write with ATOMIC RENAME (No fcntl to avoid hangs)
                data = {}
                if os.path.exists(self.path):
                    with open(self.path, "r") as f:
                        data = json.load(f)
                
                data[k] = v
                
                tmp_path = self.path + ".tmp"
                with open(tmp_path, "w") as f:
                    json.dump(data, f)
                os.rename(tmp_path, self.path)
            except:
                pass
            
        def read(self, k):
            if not os.path.exists(self.path):
                return None
            try:
                with open(self.path, "r") as f:
                    data = json.load(f)
                return data.get(k)
            except:
                return None
            
        def list_keys(self):
            if not os.path.exists(self.path):
                return []
            try:
                with open(self.path, "r") as f:
                    data = json.load(f)
                return list(data.keys())
            except:
                return []

    class MockFabric:
        def attach_context(self, name):
            return MockContext(name)
    
    return MockFabric()
