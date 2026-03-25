"""
Test login API directly
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_login():
    """Test login endpoint directly"""
    
    payload = {
        "email": "admin@medtrack-demo.com",
        "password": "Demo@1234",
        "tenant_id": "b5ef68c4-18be-4fa6-a439-a23c34877550"
    }
    
    print(f"Testing login endpoint: {BASE_URL}/auth/login")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=payload, timeout=5)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}\n")
        print(f"Response Body:")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 200:
            print("\n✅ LOGIN SUCCESSFUL!")
            result = response.json()
            print(f"\nToken: {result.get('access_token', 'N/A')[:50]}...")
            print(f"User ID: {result.get('user_id')}")
            print(f"Email: {result.get('email')}")
            print(f"Role: {result.get('role')}")
        else:
            print(f"\n❌ LOGIN FAILED: {response.status_code}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ CONNECTION ERROR: Cannot connect to {BASE_URL}")
        print(f"   Make sure backend is running on port 8000")
        print(f"   Error: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    print("=" * 70)
    print("  Testing Backend Login API")
    print("=" * 70 + "\n")
    test_login()
    print("\n" + "=" * 70)
