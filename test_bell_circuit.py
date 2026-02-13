#!/usr/bin/env python3
"""
Test script to verify the Operations Agent fix
"""
import requests
import json

def test_bell_circuit():
    """Test creating a Bell circuit"""
    url = "http://127.0.0.1:8000/api/v1/messages"
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Crea un circuito Bell con 2 qubits"
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print("=" * 80)
    print("🧪 Testing Operations Agent with Bell Circuit")
    print("=" * 80)
    print(f"URL: {url}")
    print(f"Request: {json.dumps(payload, indent=2)}")
    print("=" * 80)
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        print(f"Status Code: {response.status_code}")
        print("=" * 80)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS!")
            print("=" * 80)
            print("Response:")
            print(json.dumps(result, indent=2))
        else:
            print("❌ FAILED!")
            print("=" * 80)
            print("Response:")
            print(response.text)
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    print("=" * 80)

if __name__ == "__main__":
    test_bell_circuit()
