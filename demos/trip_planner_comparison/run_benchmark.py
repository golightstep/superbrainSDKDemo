import subprocess
import os
import json
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VANILLA_DIR = os.path.join(BASE_DIR, "vanilla")
SDK_DIR = os.path.join(BASE_DIR, "superbrain_sdk")

def run_implementation(path, name):
    print(f"\n🚀 Running {name} Implementation...")
    # Add dummy env vars if needed
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{env.get('PYTHONPATH', '')}:{path}"
    
    try:
        # Run in headless mode (main.py detects TTY.isatty())
        process = subprocess.run(
            [sys.executable, "main.py"],
            cwd=path,
            env=env,
            capture_output=True,
            text=True,
            timeout=30 # Limit for the demo
        )
        print(f"✅ {name} Finished.")
        
        # Read metrics
        metrics_file = os.path.join(path, "metrics.json")
        if os.path.exists(metrics_file):
            with open(metrics_file, "r") as f:
                return json.load(f)
    except subprocess.TimeoutExpired:
        print(f"⚠️ {name} timed out.")
    except Exception as e:
        print(f"❌ Error running {name}: {e}")
    
    return None

def main():
    print("🧠 SuperBrain vs Vanilla: Trip Planner Benchmark")
    print("==============================================")
    
    vanilla_metrics = run_implementation(VANILLA_DIR, "Vanilla")
    sdk_metrics = run_implementation(SDK_DIR, "SuperBrain SDK")
    
    if not vanilla_metrics or not sdk_metrics:
        print("❌ Error: Benchmark failed to generate real metrics.")
        sys.exit(1)
        
    comparison = {
        "vanilla": vanilla_metrics,
        "superbrain_sdk": sdk_metrics
    }
    
    with open(os.path.join(BASE_DIR, "comparison_results.json"), "w") as f:
        json.dump(comparison, f, indent=4)
        
    print("\n📊 Benchmark Results Saved to comparison_results.json")
    print(f"Comparison: {comparison['vanilla']['state_sharing_latency_us'] / comparison['superbrain_sdk']['state_sharing_latency_us']:.1f}x speedup in state sharing latency!")
    
    v_tokens = comparison['vanilla']['total_tokens_processed']
    s_tokens = comparison['superbrain_sdk']['total_tokens_processed']
    print(f"Token Efficiency: {((v_tokens - s_tokens) / v_tokens * 100):.1f}% fewer tokens processed!")

if __name__ == "__main__":
    main()
