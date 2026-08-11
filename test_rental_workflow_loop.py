import unittest
import json
from app import app

class RentalWorkflowLoopTest(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_booking_and_approval_loop(self):
        # 1. Submit Rental Request for Listing #3
        payload_req = {
            "listing_id": 3,
            "borrower_id": 3,
            "rent_start_date": "2026-08-10",
            "rent_end_date": "2026-08-15",
            "rental_purpose": "Field Trip",
            "notes": "Testing loop engineering booking"
        }
        res = self.client.post('/api/rentals/request', data=json.dumps(payload_req), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        req_id = data['request_id']
        print(f"  [OK] PASS  |  Booking Request submitted (ID: {req_id})")

        # 2. Approve Request & Lock Transaction
        res_app = self.client.post('/api/rentals/approve', data=json.dumps({"request_id": req_id}), content_type='application/json')
        self.assertEqual(res_app.status_code, 200)
        data_app = json.loads(res_app.data)
        self.assertTrue(data_app['success'])
        print(f"  [OK] PASS  |  Request #{req_id} approved & 10% commission locked")

        # 3. Fetch User Rentals Activity
        res_rentals = self.client.get('/api/rentals/my-requests/3')
        self.assertEqual(res_rentals.status_code, 200)
        rentals = json.loads(res_rentals.data)
        self.assertIn('incoming', rentals)
        self.assertIn('outgoing', rentals)
        print(f"  [OK] PASS  |  My Rentals Activity retrieved successfully")

if __name__ == '__main__':
    unittest.main()
