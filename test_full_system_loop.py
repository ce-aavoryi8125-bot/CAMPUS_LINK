import unittest
import json
import base64
from app import app

class FullSystemLoopTest(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_image_upload_api(self):
        # 1. Base64 dummy image upload test
        dummy_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        res = self.client.post('/api/upload-image', data=json.dumps({"image_data": dummy_base64}), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIn('assets/', data['image_url'])
        print(f"  [OK] PASS  |  Image Upload API: Uploaded ({data['image_url']})")

    def test_post_listing_with_image(self):
        payload = {
            "owner_id": 1,
            "category_id": 1,
            "title": "Leica TS07 Total Station",
            "description": "High precision total station with tripod",
            "subcategory": "Surveying Equipment",
            "brand": "Leica",
            "model": "TS07",
            "purchase_year": 2023,
            "rental_rate_per_day": 150.0,
            "deposit_amount": 500.0,
            "condition": "Good",
            "pickup_location": "Chamber of Mines Hostel",
            "available_from": "2026-08-10",
            "available_until": "2026-11-10",
            "thumbnail_path": "assets/leica_ts07.jpg"
        }
        res = self.client.post('/api/listings', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        print(f"  [OK] PASS  |  Post Equipment Listing with Image (ID: {data['listing_id']})")

    def test_user_profile_and_password_update(self):
        # Update profile
        payload_prof = {
            "user_id": 1,
            "phone": "+233249998877",
            "department": "Geomatic Engineering",
            "hostel": "Chamber of Mines Hostel"
        }
        res_p = self.client.post('/api/user/profile', data=json.dumps(payload_prof), content_type='application/json')
        self.assertEqual(res_p.status_code, 200)
        data_p = json.loads(res_p.data)
        self.assertTrue(data_p['success'])
        print(f"  [OK] PASS  |  User Profile Update API")

        # Change password
        payload_pw = {
            "user_id": 1,
            "old_password": "Student123",
            "new_password": "Student123"
        }
        res_pw = self.client.post('/api/user/change-password', data=json.dumps(payload_pw), content_type='application/json')
        self.assertEqual(res_pw.status_code, 200)
        data_pw = json.loads(res_pw.data)
        self.assertTrue(data_pw['success'])
        print(f"  [OK] PASS  |  Password Change Security API")

if __name__ == '__main__':
    unittest.main()
