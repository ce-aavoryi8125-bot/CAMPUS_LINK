import os
import io
import csv
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, send_from_directory

import db_engine
import controllers

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'campuslink_umat_secret_key_2026'

# --- ROOT & STATIC SERVING ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    assets_dir = os.path.join(app.root_path, 'assets')
    return send_from_directory(assets_dir, filename)

# --- SYSTEM & DATABASE HEALTH ---

@app.route('/api/status', methods=['GET'])
def get_status():
    status = db_engine.get_engine_status()
    return jsonify(status)

@app.route('/api/db/config', methods=['POST'])
def configure_db():
    data = request.json or {}
    host = data.get('host', 'localhost')
    port = data.get('port', 3306)
    user = data.get('user', 'root')
    password = data.get('password', '')
    database = data.get('database', 'campuslink_umat')
    
    db_engine.set_mysql_credentials(host, port, user, password, database)
    status = db_engine.get_engine_status()
    
    if status['engine'] == 'MYSQL':
        try:
            from database import db_seeder_mysql
            db_seeder_mysql.seed_database_engine()
            status['seeded'] = True
        except Exception as e:
            status['seeder_error'] = str(e)
            
    return jsonify(status)

# --- AUTHENTICATION & DEMO ACCOUNTS ---

@app.route('/api/demo-accounts', methods=['GET'])
def get_demo_accounts():
    accounts = [
        {"user_id": 1, "name": "Albert Boateng", "email": "ce-aavoryi8125@st.umat.edu.gh", "password": "Student123", "role": "Verified Student (Lender)", "department": "Geomatic Engineering"},
        {"user_id": 2, "name": "Benedict Osei", "email": "benedict@st.umat.edu.gh", "password": "Student123", "role": "Verified Student (Lender)", "department": "Mining Engineering"},
        {"user_id": 3, "name": "Grace Mensah", "email": "grace@st.umat.edu.gh", "password": "Student123", "role": "Borrower (Student)", "department": "Petroleum Engineering"},
        {"user_id": 4, "name": "Dr. Kwame Asante", "email": "kasante@umat.edu.gh", "password": "Staff123", "role": "Verified Staff (Lender)", "department": "Electrical & Electronic Engineering"},
        {"user_id": 6, "name": "Admin CampusLink", "email": "admin@umat.edu.gh", "password": "Admin123", "role": "System Administrator", "department": "Computer Science & Engineering"}
    ]
    return jsonify(accounts)

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    result = controllers.authenticate_user(email, password)
    if isinstance(result, dict):
        return jsonify({"success": True, "user": result})
    elif result == -2:
        return jsonify({"success": False, "message": "Account suspended by administration."}), 403
    else:
        return jsonify({"success": False, "message": "Invalid institutional email or password."}), 401

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    student_id = data.get('student_id', '').strip()
    phone = data.get('phone', '').strip()
    department = data.get('department', 'Geomatic Engineering').strip()
    hostel = data.get('hostel', 'Chamber of Mines Hostel').strip()
    
    if '@' not in email or '.' not in email:
        return jsonify({"success": False, "message": "Please enter a valid email address."}), 400
        
    res = controllers.register_user(name, email, password, student_id, phone, department, hostel)
    if res > 0:
        user = controllers.authenticate_user(email, password)
        return jsonify({"success": True, "user": user})
    else:
        return jsonify({"success": False, "message": "Registration failed. Email or Student/Index ID may already exist."}), 400

# --- USER PROFILE & MEDIA ---

@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    import base64
    import time
    try:
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'png'
                filename = f"item_{int(time.time())}_{file.filename}"
                save_dir = os.path.join(app.root_path, 'assets')
                os.makedirs(save_dir, exist_ok=True)
                file.save(os.path.join(save_dir, filename))
                return jsonify({"success": True, "image_url": f"assets/{filename}"})
        
        data = request.json or {}
        image_data = data.get('image_data', '')
        if image_data.startswith('data:image'):
            header, encoded = image_data.split(',', 1)
            ext = 'png'
            if 'jpeg' in header or 'jpg' in header: ext = 'jpg'
            filename = f"upload_{int(time.time())}.{ext}"
            save_dir = os.path.join(app.root_path, 'assets')
            os.makedirs(save_dir, exist_ok=True)
            with open(os.path.join(save_dir, filename), 'wb') as f:
                f.write(base64.b64decode(encoded))
            return jsonify({"success": True, "image_url": f"assets/{filename}"})
        elif data.get('image_url'):
            return jsonify({"success": True, "image_url": data.get('image_url')})
            
        return jsonify({"success": False, "message": "No valid image uploaded"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/user/profile', methods=['POST'])
def update_profile():
    data = request.json or {}
    user_id = data.get('user_id')
    phone = data.get('phone', '')
    department = data.get('department', '')
    hostel = data.get('hostel', '')
    avatar_path = data.get('avatar_path')
    
    if not user_id:
        return jsonify({"success": False, "message": "User ID required"}), 400
        
    controllers.update_user_profile(user_id, phone, department, hostel, avatar_path)
    return jsonify({"success": True, "message": "Profile updated successfully"})

@app.route('/api/user/change-password', methods=['POST'])
def change_password():
    data = request.json or {}
    user_id = data.get('user_id')
    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')
    
    if not user_id or not old_pw or not new_pw:
        return jsonify({"success": False, "message": "All fields required"}), 400
        
    res = controllers.change_user_password(user_id, old_pw, new_pw)
    if res > 0:
        return jsonify({"success": True, "message": "Password changed successfully"})
    else:
        return jsonify({"success": False, "message": "Incorrect current password"}), 400

# --- MARKETPLACE & LISTINGS ---

@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = controllers.get_categories()
    res = []
    if categories:
        for c in categories:
            res.append({
                "category_id": c[0],
                "name": c[1],
                "description": c[2]
            })
    return jsonify(res)

@app.route('/api/listings', methods=['GET'])
def search_listings():
    cat_id = request.args.get('category_id')
    search = request.args.get('search', '')
    
    if cat_id and cat_id != 'all':
        cat_id = int(cat_id)
    else:
        cat_id = None
        
    listings = controllers.get_filtered_listings(keyword=search, category_id=cat_id)
    res = []
    if listings:
        for l in listings:
            res.append({
                "listing_id": l[0],
                "title": l[1],
                "description": l[2] if len(l) > 2 else "",
                "subcategory": l[3] if len(l) > 3 else "",
                "brand": l[4] if len(l) > 4 else "",
                "model": l[5] if len(l) > 5 else "",
                "rental_rate_per_day": float(l[6]) if len(l) > 6 else 0.0,
                "deposit_amount": float(l[7]) if len(l) > 7 else 0.0,
                "condition": l[8] if len(l) > 8 else "Good",
                "status": l[9] if len(l) > 9 else "Available",
                "pickup_location": l[10] if len(l) > 10 else "",
                "owner_name": l[11] if len(l) > 11 else "",
                "category_name": l[12] if len(l) > 12 else "",
                "available_from": l[13] if len(l) > 13 else "",
                "available_until": l[14] if len(l) > 14 else "",
                "owner_id": l[15] if len(l) > 15 else 1,
                "category_id": l[16] if len(l) > 16 else 1,
                "thumbnail_path": l[17] if (len(l) > 17 and l[17]) else "assets/logo.jpg"
            })
    return jsonify(res)

@app.route('/api/listings', methods=['POST'])
def create_listing():
    data = request.json or {}
    try:
        res = controllers.create_listing(
            owner_id=int(data['owner_id']),
            category_id=int(data['category_id']),
            title=data['title'],
            description=data.get('description', ''),
            subcategory=data['subcategory'],
            brand=data['brand'],
            model=data['model'],
            purchase_year=int(data.get('purchase_year', 2023)),
            rate=float(data['rental_rate_per_day']),
            deposit=float(data['deposit_amount']),
            condition=data.get('condition', 'Good'),
            location=data['pickup_location'],
            start_date=data['available_from'],
            end_date=data['available_until'],
            thumbnail_path=data.get('thumbnail_path', 'assets/logo.jpg')
        )
        if res > 0:
            return jsonify({"success": True, "listing_id": res})
        else:
            return jsonify({"success": False, "message": "Failed to create listing"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

# --- RENTAL WORKFLOW ---

@app.route('/api/rentals/request', methods=['POST'])
def submit_request():
    data = request.json or {}
    try:
        req_id = controllers.submit_rental_request(
            listing_id=int(data['listing_id']),
            borrower_id=int(data['borrower_id']),
            start_date=data['rent_start_date'],
            end_date=data['rent_end_date'],
            purpose=data['rental_purpose'],
            notes=data.get('notes', '')
        )
        if req_id > 0:
            return jsonify({"success": True, "request_id": req_id})
        else:
            return jsonify({"success": False, "message": "Dates unavailable or listing inactive"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/rentals/my-requests/<int:user_id>', methods=['GET'])
def get_user_requests(user_id):
    borrowed_reqs = controllers.get_my_requests(user_id) or []
    incoming_reqs = controllers.get_incoming_requests(user_id) or []
    lent_items = controllers.get_my_lent_items(user_id) or []
    
    formatted_incoming = []
    for r in incoming_reqs:
        formatted_incoming.append({
            "request_id": r[0],
            "listing_title": r[1],
            "borrower_name": r[2],
            "rent_start_date": r[3],
            "rent_end_date": r[4],
            "rental_purpose": r[5],
            "status": r[6],
            "notes": r[7],
            "listing_id": r[8],
            "borrower_id": r[9]
        })
        
    formatted_outgoing = []
    for r in borrowed_reqs:
        formatted_outgoing.append({
            "request_id": r[0],
            "listing_title": r[1],
            "owner_name": r[2],
            "rent_start_date": r[3],
            "rent_end_date": r[4],
            "rental_purpose": r[5],
            "status": r[6],
            "notes": r[7],
            "listing_id": r[8]
        })
        
    formatted_lent = []
    for t in lent_items:
        formatted_lent.append({
            "transaction_id": t[0],
            "listing_title": t[1],
            "borrower_name": t[2],
            "rent_start_date": t[3],
            "rent_end_date": t[4],
            "rental_status": t[5],
            "deposit_held": float(t[6]),
            "gross_amount": float(t[7]),
            "listing_id": t[8]
        })

    return jsonify({
        "incoming": formatted_incoming,
        "outgoing": formatted_outgoing,
        "active_lent": formatted_lent
    })

@app.route('/api/rentals/approve', methods=['POST'])
def approve_request():
    data = request.json or {}
    req_id = int(data['request_id'])
    res = controllers.approve_request(req_id)
    if res == 1:
        return jsonify({"success": True, "message": "Approved successfully"})
    elif res == -2:
        return jsonify({"success": False, "message": "Listing is no longer available"}), 400
    else:
        return jsonify({"success": False, "message": "Could not approve request"}), 400

@app.route('/api/rentals/return', methods=['POST'])
def process_return():
    data = request.json or {}
    tx_id = int(data['transaction_id'])
    has_damage = data.get('has_damage', False)
    damage_condition = 'Minor' if has_damage else 'Good'
    cost = float(data.get('repair_cost', 0.0))
    notes = data.get('return_notes', 'Returned via Web App')
    
    res = controllers.process_return(
        transaction_id=tx_id,
        return_notes=notes,
        damage_condition=damage_condition,
        claim_amount=cost
    )
    if res == 1:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Could not process return"}), 400

# --- REVIEWS & TRUST SCORE ---

@app.route('/api/trust-score/<int:user_id>', methods=['GET'])
def get_trust_score(user_id):
    trust = controllers.calculate_trust_score(user_id)
    return jsonify(trust)

@app.route('/api/reviews', methods=['POST'])
def submit_review():
    data = request.json or {}
    res = controllers.submit_review(
        transaction_id=int(data['transaction_id']),
        reviewer_id=int(data['reviewer_id']),
        reviewee_id=int(data['reviewee_id']),
        reviewee_type=data['reviewee_type'],
        rating=int(data['rating']),
        comment=data.get('comment', '')
    )
    if res > 0:
        return jsonify({"success": True, "review_id": res})
    else:
        return jsonify({"success": False, "message": "Duplicate review or transaction error"}), 400

# --- WISHLIST & SAVED LISTINGS ---

@app.route('/api/wishlist', methods=['GET'])
def get_wishlist():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify([])
    items = controllers.get_my_wishlist(user_id) or []
    res = []
    for item in items:
        res.append({
            "wishlist_id": item[0],
            "category_name": item[1],
            "keyword": item[2],
            "created_at": item[3]
        })
    return jsonify(res)

@app.route('/api/wishlist', methods=['POST'])
def add_wishlist():
    data = request.json or {}
    res = controllers.add_to_wishlist(
        user_id=int(data['user_id']),
        category_id=data.get('category_id'),
        keyword=data.get('keyword', '')
    )
    return jsonify({"success": True})

@app.route('/api/saved-listings', methods=['GET'])
def get_saved_listings():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify([])
    items = controllers.get_my_saved_listings(user_id) or []
    res = []
    for item in items:
        res.append({
            "saved_id": item[0],
            "listing_id": item[1],
            "title": item[2],
            "rental_rate_per_day": float(item[3]),
            "deposit_amount": float(item[4]),
            "condition": item[5],
            "status": item[6],
            "owner_name": item[7]
        })
    return jsonify(res)

@app.route('/api/saved-listings', methods=['POST'])
def save_listing():
    data = request.json or {}
    controllers.save_listing(int(data['user_id']), int(data['listing_id']))
    return jsonify({"success": True})

# --- REPORTS ENGINE (All 15 Reports) ---

REPORTS_TITLES = {
    1: "Platform Revenue & Commission Summary",
    2: "Top 10 Lenders by Total Earnings",
    3: "Most Active Borrowers",
    4: "Category Revenue Performance",
    5: "Currently Active Rentals Overview",
    6: "Maintenance & Repair Expenses",
    7: "High Risk Overdue Rentals",
    8: "Unborrowed Idle Listings",
    9: "Rental Purpose Distribution",
    10: "Average Rental Rates by Category",
    11: "User Trust Score Rankings",
    12: "Hostel Equipment Density Report",
    13: "Monthly Rental Trends",
    14: "Lender vs Borrower Ratings Comparison",
    15: "Delisted Equipment Audit Log"
}

@app.route('/api/reports/<int:report_id>', methods=['GET'])
def get_report(report_id):
    if report_id not in REPORTS_TITLES:
        return jsonify({"error": "Invalid Report ID"}), 404
        
    title = REPORTS_TITLES[report_id]
    headers, rows = controllers.get_report_data(report_id)
    
    formatted_rows = []
    if rows:
        for r in rows:
            formatted_rows.append([str(val) if val is not None else "" for val in r])
        
    return jsonify({
        "report_id": report_id,
        "title": title,
        "headers": headers,
        "data": formatted_rows
    })

@app.route('/api/reports/<int:report_id>/export', methods=['GET'])
def export_report_csv(report_id):
    if report_id not in REPORTS_TITLES:
        return jsonify({"error": "Invalid Report ID"}), 404
        
    title = REPORTS_TITLES[report_id]
    headers, rows = controllers.get_report_data(report_id)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    if rows:
        writer.writerows(rows)
    
    filename = f"CampusLink_Report_{report_id:02d}_{title.replace(' ', '_')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[SERVER] Launching CampusLink Web Server on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
