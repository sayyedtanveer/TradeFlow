from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import get_settings

def run_test():
    with TestClient(app) as client:
        TENANT_ID = 'b5ef68c4-18be-4fa6-a439-a23c34877550'
        
        # login
        resp = client.post('/api/v1/auth/login', json={'email':'admin@medtrack-demo.com','password':'Demo@1234','tenant_id':TENANT_ID})
        token = resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        tmpl_body = {
            'code': 'DEBUG_API_2',
            'name': 'API T-Shirt',
            'attributes': [
                {'key': 'SIZE',  'label': 'Size'},
                {'key': 'COLOR', 'label': 'Color'}
            ]
        }
        
        # Catching 500 error directly inside python
        try:
            resp2 = client.post('/api/v1/products/templates', json=tmpl_body, headers=headers)
            print("Status Code:", resp2.status_code)
            print("Response:", resp2.text)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    run_test()
