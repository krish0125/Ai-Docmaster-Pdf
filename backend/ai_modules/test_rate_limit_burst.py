import requests
import concurrent.futures

BASE_URL = 'http://127.0.0.1:5001'

def run_test():
    # 1. Login to get token
    try:
        r = requests.post(f'{BASE_URL}/auth/login', json={'email': 'auth_test_1@test.com', 'password': 'password123'})
        token = r.json().get('token')
        if not token:
            print('Login failed')
            return
    except Exception as e:
        print('Login request failed:', e)
        return

    headers = {'Authorization': f'Bearer {token}'}

    # 2. Create a dummy pdf
    with open('dummy_burst.pdf', 'wb') as f:
        f.write(b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Count 1\n/Kids [3 0 R]\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Burst Test PDF) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000219 00000 n\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n314\n%%EOF\n')

    def make_request(i):
        print(f'Starting request {i}...')
        with open('dummy_burst.pdf', 'rb') as f:
            files = {'file': ('dummy_burst.pdf', f, 'application/pdf')}
            data = {'mode': 'brief'}
            try:
                res = requests.post(f'{BASE_URL}/ai/summary', headers=headers, files=files, data=data)
                try:
                    return f"Req {i} -> Status: {res.status_code}, Response: {res.json()}"
                except:
                    return f"Req {i} -> Status: {res.status_code}, Response text: {res.text[:100]}"
            except Exception as e:
                return f"Req {i} -> Exception: {str(e)}"

    print('Firing 4 concurrent summary requests to trigger rate limiting...')
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(make_request, i) for i in range(1, 5)]
        for future in concurrent.futures.as_completed(futures):
            print(future.result())

if __name__ == '__main__':
    run_test()
