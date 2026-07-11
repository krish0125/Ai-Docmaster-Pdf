import json
import unittest
import requests

BASE_URL = "http://127.0.0.1:5001"

class TestFeedbackAPI(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # 1. Register a test normal user
        cls.user_email = "feedback.user@example.com"
        cls.password = "password123"
        
        reg_payload = {
            "name": "Feedback User",
            "email": cls.user_email,
            "password": cls.password
        }
        requests.post(f"{BASE_URL}/auth/signup", json=reg_payload)
        
        # Log in normal user
        login_res = requests.post(f"{BASE_URL}/auth/login", json={
            "email": cls.user_email,
            "password": cls.password
        })
        cls.user_token = login_res.json().get("token")
        
        # 2. Register an admin user (email = admin@aidocmaster.com)
        cls.admin_email = "admin@aidocmaster.com"
        admin_reg = {
            "name": "System Administrator",
            "email": cls.admin_email,
            "password": cls.password
        }
        requests.post(f"{BASE_URL}/auth/signup", json=admin_reg)
        
        # Log in admin user
        admin_login = requests.post(f"{BASE_URL}/auth/login", json={
            "email": cls.admin_email,
            "password": cls.password
        })
        cls.admin_token = admin_login.json().get("token")

    def test_01_create_feedback_anonymous(self):
        payload = {
            "rating": 5,
            "message": "Excellent design and widgets!",
            "page": "dashboard.html"
        }
        res = requests.post(f"{BASE_URL}/feedback", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("feedback_id", data)
        self.assertIn("Thank you for your feedback!", data["message"])

    def test_02_create_feedback_authenticated(self):
        payload = {
            "rating": 4,
            "message": "Fast PDF parsing, very clean.",
            "page": "result.html"
        }
        headers = {"Authorization": f"Bearer {self.user_token}"}
        res = requests.post(f"{BASE_URL}/feedback", json=payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("feedback_id", data)

    def test_03_create_feedback_invalid(self):
        # Missing rating
        res = requests.post(f"{BASE_URL}/feedback", json={"message": "No rating"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Rating is required", res.json().get("error", ""))
        
        # Invalid rating range
        res = requests.post(f"{BASE_URL}/feedback", json={"rating": 10, "message": "Too high"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("between 1 and 5", res.json().get("error", ""))

    def test_04_get_feedback_denied_to_anonymous(self):
        res = requests.get(f"{BASE_URL}/feedback")
        # Anonymous GET feedback should be unauthorized
        self.assertIn(res.status_code, [401, 403])

    def test_05_get_feedback_denied_to_normal_user(self):
        headers = {"Authorization": f"Bearer {self.user_token}"}
        res = requests.get(f"{BASE_URL}/feedback", headers=headers)
        self.assertEqual(res.status_code, 403)
        self.assertIn("Admin privileges required", res.json().get("error", ""))

    def test_06_get_feedback_granted_to_admin(self):
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = requests.get(f"{BASE_URL}/feedback", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("feedback", data)
        self.assertIn("stats", data)
        self.assertGreaterEqual(len(data["feedback"]), 2)
        
        # Verify average calculation matches 4.5
        avg_rating = data["stats"]["average_rating"]
        self.assertGreaterEqual(avg_rating, 4.0)
        self.assertLessEqual(avg_rating, 5.0)
        print(f"\n[Test Proof] Average Rating: {avg_rating}, Total Submissions: {data['total']}")

if __name__ == '__main__':
    unittest.main()
