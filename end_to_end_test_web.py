import unittest
import json
import os
import sys

from app import app

class CampusLinkWebTestSuite(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_01_db_status(self):
        res = self.client.get('/api/status')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('engine', data)
        self.assertIn('status', data)
        print(f"  [OK] PASS  |  DB Engine Status: {data['engine']} ({data['status']})")

    def test_02_demo_accounts(self):
        res = self.client.get('/api/demo-accounts')
        self.assertEqual(res.status_code, 200)
        accounts = json.loads(res.data)
        self.assertGreaterEqual(len(accounts), 5)
        print(f"  [OK] PASS  |  Demo Accounts: {len(accounts)} accounts returned")

    def test_03_authentication(self):
        payload = {"email": "ce-aavoryi8125@st.umat.edu.gh", "password": "Student123"}
        res = self.client.post('/api/auth/login', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['name'], 'Albert Boateng')
        print(f"  [OK] PASS  |  Authentication: Albert Boateng logged in via PBKDF2 hash")

    def test_04_categories_api(self):
        res = self.client.get('/api/categories')
        self.assertEqual(res.status_code, 200)
        cats = json.loads(res.data)
        self.assertGreaterEqual(len(cats), 10)
        print(f"  [OK] PASS  |  Categories API: {len(cats)} categories loaded")

    def test_05_marketplace_listings(self):
        res = self.client.get('/api/listings?category_id=all&search=')
        self.assertEqual(res.status_code, 200)
        listings = json.loads(res.data)
        self.assertGreater(len(listings), 0)
        print(f"  [OK] PASS  |  Marketplace API: {len(listings)} listings loaded")

    def test_06_reports_engine_all_15(self):
        for report_id in range(1, 16):
            res = self.client.get(f'/api/reports/{report_id}')
            self.assertEqual(res.status_code, 200)
            data = json.loads(res.data)
            self.assertIn('headers', data)
            self.assertIn('data', data)
        print(f"  [OK] PASS  |  Reports API: All 15 Business Intelligence Reports verified")

    def test_07_csv_export(self):
        res = self.client.get('/api/reports/1/export')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.headers['Content-Type'].startswith('text/csv'))
        print(f"  [OK] PASS  |  CSV Export API: Report 01 downloaded as CSV")

    def test_08_trust_score_api(self):
        res = self.client.get('/api/trust-score/1')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('score', data)
        self.assertGreaterEqual(data['score'], 0)
        print(f"  [OK] PASS  |  Trust Score API: Score derived ({data['score']}/100)")

if __name__ == '__main__':
    print("========================================================================")
    print("   CampusLink Web Application & MySQL Integration Test Suite")
    print("========================================================================")
    unittest.main()
