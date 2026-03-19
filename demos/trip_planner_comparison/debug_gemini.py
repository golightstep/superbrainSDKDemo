import os
import requests
import json

def test_gemini():
    env_path = ".env"
    api_key = None
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "GEMINI_API_KEYY" in line:
                    api_key = line.split("=")[1].strip().strip('"').strip("'")
                    break
    
    if not api_key:
        print("Error: GEMINI_API_KEYY not found in .env")
        return

    print(f"Testing key: {api_key[:4]}...{api_key[-4:]}")
    
    # 1. Test Key with ListModels
    url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("Success (v1)! Key is valid. Available models:")
            models = response.json().get("models", [])
            for m in models:
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    print(f" - {m.get('name')}")
            
            # 2. Test a simple completion
            print("\nTesting simple completion (v1/gemini-pro-latest)...")
            gen_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro-latest:generateContent?key={api_key}"
            payload = {"contents": [{"parts":[{"text": "Hello"}]}]}
            gen_resp = requests.post(gen_url, json=payload)
            if gen_resp.status_code == 200:
                print("Generation Success!")
                print(gen_resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", ""))
            else:
                print(f"Generation Failed: {gen_resp.status_code}")
                print(gen_resp.text)
        else:
            print(f"Auth Failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_gemini()
