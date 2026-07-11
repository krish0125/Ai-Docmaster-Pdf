import os
import unittest
import requests
import time

BASE_URL = "http://127.0.0.1:5001"
FRONTEND_URL = "http://127.0.0.1:5500"

class TestE2EFlow(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Setup email and passwords for testing
        cls.test_email = f"e2e.tester.{int(time.time())}@example.com"
        cls.test_password = "password123"
        cls.admin_email = "admin@aidocmaster.com"
        cls.admin_password = "password123"

    def test_01_homepage_and_assets(self):
        """Verify frontend assets serve correctly on 5500."""
        pages = ["index.html", "login.html", "dashboard.html", "upload.html", "result.html", "chat.html", "admin-feedback.html"]
        for page in pages:
            res = requests.get(f"{FRONTEND_URL}/{page}")
            self.assertEqual(res.status_code, 200, f"Page {page} failed to serve.")
            print(f"[QA Check] Frontend page served: {page} | Status: 200 OK")

    def test_02_user_signup_and_login_flow(self):
        """Verify user signup, duplicate signup check, and login flow."""
        # 1. Signup normal user
        signup_payload = {
            "name": "E2E Tester",
            "email": self.test_email,
            "password": self.test_password
        }
        res = requests.post(f"{BASE_URL}/auth/signup", json=signup_payload)
        self.assertEqual(res.status_code, 201)
        print("[QA Check] E2E User Signup | Status: 201 Created")

        # 2. Test duplicate email signup
        res_dup = requests.post(f"{BASE_URL}/auth/signup", json=signup_payload)
        self.assertEqual(res_dup.status_code, 409)
        self.assertIn("already exists", res_dup.json().get("error", ""))
        print("[QA Check] Duplicate Email Signup | Status: 409 Conflict")

        # 3. Test wrong password login
        login_wrong = {
            "email": self.test_email,
            "password": "wrongpassword"
        }
        res_wrong = requests.post(f"{BASE_URL}/auth/login", json=login_wrong)
        self.assertEqual(res_wrong.status_code, 401)
        print("[QA Check] Wrong Password Login | Status: 401 Unauthorized")

        # 4. Successful login
        login_payload = {
            "email": self.test_email,
            "password": self.test_password
        }
        res_login = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
        self.assertEqual(res_login.status_code, 200)
        token = res_login.json().get("token")
        self.assertIsNotNone(token)
        print("[QA Check] Correct Credentials Login | Status: 200 OK")

    def test_03_auth_edge_cases(self):
        """Verify behavior with invalid, missing, or malformed tokens on protected routes."""
        # 1. Missing Token
        res = requests.get(f"{BASE_URL}/auth/profile")
        self.assertEqual(res.status_code, 401)
        print("[QA Check] Profile with missing JWT | Status: 401 Unauthorized")

        # 2. Invalid Token
        headers = {"Authorization": "Bearer invalidtokenstring"}
        res = requests.get(f"{BASE_URL}/auth/profile", headers=headers)
        self.assertEqual(res.status_code, 422)
        print("[QA Check] Profile with invalid JWT | Status: 422 Unprocessable Entity")

    def test_04_file_handling_edge_cases(self):
        """Verify behavior with empty files, wrong extensions, and huge files."""
        # Log in to get token
        login_res = requests.post(f"{BASE_URL}/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        token = login_res.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. 0-byte File Upload
        files = {'file': ('empty.pdf', b'')}
        res = requests.post(f"{BASE_URL}/pdf/upload", files=files, headers=headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn("empty", res.json().get("error", "").lower())
        print("[QA Check] 0-Byte File Upload | Status: 400 Bad Request")

        # 2. Wrong extension file upload
        files = {'file': ('wrong.exe', b'print("hello")')}
        res = requests.post(f"{BASE_URL}/pdf/upload", files=files, headers=headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn("only pdf", res.json().get("error", "").lower())
        print("[QA Check] Invalid Extension File Upload | Status: 400 Bad Request")

        # 3. File size exceeds max boundary
        too_big_data = b'0' * (55 * 1024 * 1024) # 55 MB (exceeds 50MB)
        files = {'file': ('huge.pdf', too_big_data)}
        res = requests.post(f"{BASE_URL}/pdf/upload", files=files, headers=headers)
        print(f"\n[DEBUG] Huge upload res: {res.status_code} | {res.text}")
        self.assertEqual(res.status_code, 413) # Payload Too Large
        print("[QA Check] File size > 50MB Upload | Status: 413 Payload Too Large")

    def test_05_feedback_flow_live(self):
        """Test submission and admin authorization list check."""
        # 1. Submit anonymous feedback
        payload = {
            "rating": 5,
            "message": "Dynamic feedback live check!",
            "page": "index.html"
        }
        res = requests.post(f"{BASE_URL}/feedback", json=payload)
        self.assertEqual(res.status_code, 201)
        print("[QA Check] Anonymous Feedback Submission | Status: 201 Created")

        # 2. Register/Login admin
        admin_payload = {
            "name": "Admin Tester",
            "email": self.admin_email,
            "password": self.admin_password
        }
        requests.post(f"{BASE_URL}/auth/signup", json=admin_payload)
        
        login_res = requests.post(f"{BASE_URL}/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        admin_token = login_res.json().get("token")

        # 3. Fetch feedback dashboard as admin
        headers = {"Authorization": f"Bearer {admin_token}"}
        res_list = requests.get(f"{BASE_URL}/feedback", headers=headers)
        self.assertEqual(res_list.status_code, 200)
        data = res_list.json()
        self.assertGreaterEqual(len(data.get("feedback", [])), 1)
        self.assertGreaterEqual(data["stats"]["total_count"], 4)
        print("[QA Check] Admin View Feedback Board | Status: 200 OK")

if __name__ == '__main__':
    unittest.main()
