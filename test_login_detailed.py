"""
Enhanced test to capture backend errors
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_login():
    """Test login endpoint with detailed error capture"""
    
    payload = {
        "email": "admin@medtrack-demo.com",
        "password": "Demo@1234",
        "tenant_id": "b5ef68c4-18be-4fa6-a439-a23c34877550"
    }
    
    print(f"Testing login endpoint: {BASE_URL}/auth/login\n")
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=payload, timeout=5)
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}\n")
        
        if response.status_code == 200:
            print("✅ LOGIN SUCCESSFUL!")
            result = response.json()
            print(f"\nToken: {result.get('access_token', 'N/A')[:50]}...")
            print(f"User ID: {result.get('user_id')}")
            print(f"Email: {result.get('email')}")
            print(f"Role: {result.get('role')}")
        else:
            print(f"❌ LOGIN FAILED with status {response.status_code}\n")
            print("Response Text:")
            print(response.text[:500])
            
            # Try to parse as JSON
            try:
                error_json = response.json()
                print("\nParsed Error Response:")
                print(json.dumps(error_json, indent=2))
            except:
                print("\n(Response is not JSON)")
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Cannot reach backend at {BASE_URL}")
        print(f"   Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("=" * 70)
    print("  Testing Backend Login API (Enhanced)")
    print("=" * 70 + "\n")
    test_login()
    print("\n" + "=" * 70)
