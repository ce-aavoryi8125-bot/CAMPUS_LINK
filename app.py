import os
import io
import csv
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify, Response, send_from_directory, g

from decimal import Decimal
import db_engine
import controllers
from core.config import PlatformConfig, CommissionService
from core.security import create_access_token, decode_access_token
from core.auth_middleware import require_auth, require_roles, get_auth_user_id
from core.rate_limiter import rate_limit
from core.media import process_and_reencode_image, decode_base64_image
from core.validators import validate_email, sanitize_text
from core.security_headers import register_security_headers
from core.audit_logger import log_security_event, log_financial_event
from core.wallet_service import FinancialService
from core.reconciliation import ReconciliationEngine
from core.momo_adapter import get_payment_gateway
from core.redis_client import check_redis_health
from tasks.webhook_tasks import process_momo_deposit_webhook_task, process_momo_payout_webhook_task
from tasks.reconciliation_tasks import run_periodic_reconciliation_task
from tasks.escrow_tasks import sweep_overdue_rentals_task
from tasks.notification_tasks import dispatch_notification_task

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = PlatformConfig.SECRET_KEY

# Enforce strict production configuration validation on startup
PlatformConfig.assert_production_ready()

# Register OWASP Security Headers (X-Content-Type-Options, X-Frame-Options, etc.)
register_security_headers(app)

# --- ROOT & STATIC SERVING ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    assets_dir = os.path.join(app.root_path, 'assets')
    return send_from_directory(assets_dir, filename)

# --- SYSTEM OBSERVABILITY & HEALTH PROBES ---

@app.route('/healthz', methods=['GET'])
def liveness_probe():
    """
    Lightweight Liveness Probe.
    Returns HTTP 200 if the WSGI application process is running and responsive.
    Contains zero external network/database I/O dependencies.
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": PlatformConfig.CAMPUSLINK_ENV,
        "version": "2.0.0"
    }), 200

@app.route('/readyz', methods=['GET'])
def readiness_probe():
    """
    Subsystem Readiness Probe.
    Evaluates active database connectivity and Redis broker availability.
    Returns HTTP 200 when ready to receive traffic, HTTP 503 if critical dependencies are down.
    """
    db_health = db_engine.check_database_health()
    redis_health = check_redis_health()
    
    is_prod = PlatformConfig.is_production()
    
    # In production, both MySQL and Redis MUST be healthy
    if is_prod:
        is_ready = (
            db_health.get("status") == "healthy" and 
            db_health.get("engine") == "MYSQL" and
            redis_health.get("status") == "healthy"
        )
    else:
        # In development/testing, active SQLite/MySQL is required; Redis fallback is acceptable
        is_ready = (db_health.get("status") == "healthy")
        
    response_payload = {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": PlatformConfig.CAMPUSLINK_ENV,
        "checks": {
            "database": db_health,
            "redis": redis_health
        }
    }
    
    status_code = 200 if is_ready else 503
    return jsonify(response_payload), status_code

@app.route('/api/status', methods=['GET'])
def get_status():
    status = db_engine.get_engine_status()
    return jsonify(status)

@app.route('/api/db/config', methods=['POST'])
@require_auth
@require_roles('Admin')
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
@rate_limit(max_requests=5, window_seconds=60)
def login():
    data = request.json or {}
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    result = controllers.authenticate_user(email, password)
    if isinstance(result, dict):
        # Generate JWT access token
        token = create_access_token(
            user_id=result["user_id"],
            email=result["email"],
            role=result.get("verification_level", "Verified Student"),
            name=result.get("name", "")
        )
        log_security_event("LOGIN_SUCCESS", result["user_id"], "SUCCESS", request.remote_addr)
        
        resp = jsonify({
            "success": True,
            "user": result,
            "access_token": token,
            "token_type": "Bearer"
        })
        resp.set_cookie("campuslink_session", token, httponly=True, samesite='Strict')
        return resp
    elif result == -2:
        log_security_event("LOGIN_SUSPENDED", None, "FORBIDDEN", request.remote_addr, {"email": email})
        return jsonify({"success": False, "message": "Account suspended by administration."}), 403
    else:
        log_security_event("LOGIN_FAILED", None, "UNAUTHORIZED", request.remote_addr, {"email": email})
        return jsonify({"success": False, "message": "Invalid institutional email or password."}), 401

@app.route('/api/auth/register', methods=['POST'])
@rate_limit(max_requests=3, window_seconds=600)
def register():
    data = request.json or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    student_id = data.get('student_id', '').strip()
    phone = data.get('phone', '').strip()
    department = data.get('department', 'Geomatic Engineering').strip()
    hostel = data.get('hostel', 'Chamber of Mines Hostel').strip()
    
    if not validate_email(email):
        return jsonify({"success": False, "message": "Please enter a valid institutional email address."}), 400
        
    res = controllers.register_user(name, email, password, student_id, phone, department, hostel)
    if res > 0:
        user = controllers.authenticate_user(email, password)
        token = create_access_token(
            user_id=user["user_id"],
            email=user["email"],
            role=user.get("verification_level", "Unverified"),
            name=user.get("name", "")
        )
        resp = jsonify({
            "success": True,
            "user": user,
            "access_token": token,
            "token_type": "Bearer"
        })
        resp.set_cookie("campuslink_session", token, httponly=True, samesite='Strict')
        return resp
    else:
        return jsonify({"success": False, "message": "Registration failed. Email or Student/Index ID may already exist."}), 400

# --- USER PROFILE & MEDIA ---

@app.route('/api/upload-image', methods=['POST'])
@require_auth
def upload_image():
    """
    Secure file upload endpoint with image re-encoding via Pillow.
    Strips EXIF, enforces dimensions and size limits, and saves clean re-encoded images.
    """
    save_dir = os.path.join(app.root_path, 'assets')
    
    # 1. Handle multipart form file upload
    if 'image' in request.files:
        file = request.files['image']
        if file.filename != '':
            raw_bytes = file.read()
            success, result_path, _ = process_and_reencode_image(raw_bytes, save_dir)
            if success:
                return jsonify({"success": True, "image_url": result_path})
            return jsonify({"success": False, "message": result_path}), 400

    # 2. Handle base64 encoded image string
    data = request.json or {}
    image_data = data.get('image_data', '')
    if image_data:
        ok, raw_bytes, err = decode_base64_image(image_data)
        if not ok or not raw_bytes:
            return jsonify({"success": False, "message": err or "Invalid base64 payload"}), 400
            
        success, result_path, _ = process_and_reencode_image(raw_bytes, save_dir)
        if success:
            return jsonify({"success": True, "image_url": result_path})
        return jsonify({"success": False, "message": result_path}), 400
        
    elif data.get('image_url'):
        # Whitelisted asset reference
        url = str(data.get('image_url'))
        if url.startswith('assets/'):
            return jsonify({"success": True, "image_url": url})

    return jsonify({"success": False, "message": "No valid image uploaded."}), 400

@app.route('/api/user/profile', methods=['POST'])
@require_auth
def update_profile():
    # Server-derived authenticated user ID
    auth_uid = get_auth_user_id()
    data = request.json or {}
    
    # If client attempts to specify a different user_id, ensure they are not modifying other users
    target_uid = data.get('user_id', auth_uid)
    if int(target_uid) != auth_uid and g.current_user.get("role") != "Admin":
        return jsonify({"success": False, "message": "Unauthorized. You cannot modify another user's profile."}), 403
        
    phone = data.get('phone', '')
    department = data.get('department', '')
    hostel = data.get('hostel', '')
    avatar_path = data.get('avatar_path')
    
    controllers.update_user_profile(auth_uid, phone, department, hostel, avatar_path)
    return jsonify({"success": True, "message": "Profile updated successfully"})

@app.route('/api/user/change-password', methods=['POST'])
@require_auth
@rate_limit(max_requests=3, window_seconds=300)
def change_password():
    # Server-derived authenticated user ID
    auth_uid = get_auth_user_id()
    data = request.json or {}
    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')
    
    if not old_pw or not new_pw:
        return jsonify({"success": False, "message": "Current and new password required"}), 400
        
    res = controllers.change_user_password(auth_uid, old_pw, new_pw)
    if res > 0:
        log_security_event("PASSWORD_CHANGE", auth_uid, "SUCCESS", request.remote_addr)
        return jsonify({"success": True, "message": "Password changed successfully"})
    else:
        log_security_event("PASSWORD_CHANGE_FAILED", auth_uid, "FAILED", request.remote_addr)
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
@require_auth
def create_listing():
    data = request.json or {}
    auth_owner_id = get_auth_user_id()
    
    try:
        res = controllers.create_listing(
            owner_id=auth_owner_id, # Server-derived owner ID
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
@require_auth
def submit_request():
    data = request.json or {}
    auth_borrower_id = get_auth_user_id()
    
    try:
        req_id = controllers.submit_rental_request(
            listing_id=int(data['listing_id']),
            borrower_id=auth_borrower_id, # Server-derived borrower ID
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
@require_auth
def get_user_requests(user_id):
    auth_uid = get_auth_user_id()
    if user_id != auth_uid and g.current_user.get("role") != "Admin":
        return jsonify({"success": False, "message": "Unauthorized access to other user's requests."}), 403

    borrowed_reqs = controllers.get_my_requests(auth_uid) or []
    incoming_reqs = controllers.get_incoming_requests(auth_uid) or []
    lent_items = controllers.get_my_lent_items(auth_uid) or []
    
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
@require_auth
def approve_request():
    data = request.json or {}
    req_id = int(data['request_id'])
    auth_uid = get_auth_user_id()
    
    # Ownership Check: Verify that the authenticated user owns the listing for this request
    listing_owner = db_engine.execute_query("""
    SELECT l.owner_id FROM listings l
    INNER JOIN rental_requests r ON l.listing_id = r.listing_id
    WHERE r.request_id = ?;
    """, (req_id,), fetchone=True)
    
    if not listing_owner:
        return jsonify({"success": False, "message": "Rental request not found."}), 404
        
    if listing_owner["owner_id"] != auth_uid and g.current_user.get("role") != "Admin":
        log_security_event("UNAUTHORIZED_APPROVAL", auth_uid, "FORBIDDEN", request.remote_addr, {"request_id": req_id})
        return jsonify({"success": False, "message": "Unauthorized. Only the listing owner can approve rental requests."}), 403

    res = controllers.approve_request(req_id)
    if res == 1:
        return jsonify({"success": True, "message": "Approved successfully"})
    elif res == -2:
        return jsonify({"success": False, "message": "Listing is no longer available"}), 400
    else:
        return jsonify({"success": False, "message": "Could not approve request"}), 400

@app.route('/api/rentals/return', methods=['POST'])
@require_auth
def process_return():
    data = request.json or {}
    tx_id = int(data['transaction_id'])
    auth_uid = get_auth_user_id()
    
    # Participant Check: Verify caller is borrower or owner on the transaction
    tx_party = db_engine.execute_query("""
    SELECT t.borrower_id, l.owner_id FROM rental_transactions t
    INNER JOIN listings l ON t.listing_id = l.listing_id
    WHERE t.transaction_id = ?;
    """, (tx_id,), fetchone=True)
    
    if not tx_party:
        return jsonify({"success": False, "message": "Transaction not found."}), 404
        
    if auth_uid not in (tx_party["borrower_id"], tx_party["owner_id"]) and g.current_user.get("role") != "Admin":
        return jsonify({"success": False, "message": "Unauthorized. You are not a party to this transaction."}), 403

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
@require_auth
def submit_review():
    data = request.json or {}
    auth_uid = get_auth_user_id()
    
    res = controllers.submit_review(
        transaction_id=int(data['transaction_id']),
        reviewer_id=auth_uid, # Server-derived reviewer
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
@require_auth
def get_wishlist():
    auth_uid = get_auth_user_id()
    items = controllers.get_my_wishlist(auth_uid) or []
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
@require_auth
def add_wishlist():
    data = request.json or {}
    auth_uid = get_auth_user_id()
    controllers.add_to_wishlist(
        user_id=auth_uid,
        category_id=data.get('category_id'),
        keyword=data.get('keyword', '')
    )
    return jsonify({"success": True})

@app.route('/api/saved-listings', methods=['GET'])
@require_auth
def get_saved_listings():
    auth_uid = get_auth_user_id()
    items = controllers.get_my_saved_listings(auth_uid) or []
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
@require_auth
def save_listing():
    data = request.json or {}
    auth_uid = get_auth_user_id()
    controllers.save_listing(auth_uid, int(data['listing_id']))
    return jsonify({"success": True})

# --- REPORTS ENGINE (All 15 Reports - Protected by Admin/Staff Role) ---

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
@require_auth
@require_roles('Admin', 'Verified Staff')
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
@require_auth
@require_roles('Admin', 'Verified Staff')
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

# --- NOTIFICATIONS & MOMO & LOCATIONS API ---

@app.route('/api/notifications', methods=['GET'])
@require_auth
def get_notifications():
    auth_uid = get_auth_user_id()
    rows = controllers.get_user_notifications(auth_uid) or []
    unread = controllers.get_unread_notification_count(auth_uid)
    items = []
    for r in rows:
        items.append({
            "notification_id": r[0],
            "title": r[1],
            "message": r[2],
            "type": r[3],
            "is_read": bool(r[4]),
            "created_at": r[5]
        })
    return jsonify({"notifications": items, "unread_count": unread})

@app.route('/api/notifications/mark-read', methods=['POST'])
@require_auth
def mark_notification_read():
    data = request.json or {}
    nid = data.get('notification_id')
    if nid:
        controllers.mark_notification_as_read(int(nid))
    return jsonify({"success": True})

@app.route('/api/momo/pay', methods=['POST'])
@require_auth
@rate_limit(max_requests=5, window_seconds=60)
def momo_pay():
    data = request.json or {}
    auth_uid = get_auth_user_id()
    amount = float(data.get('amount', 0.0))
    network = data.get('network', 'MTN MoMo')
    phone = data.get('phone_number', '')
    res = controllers.process_momo_payment(auth_uid, amount, network, phone)
    if res.get('success'):
        return jsonify(res)
    return jsonify(res), 400

@app.route('/api/campus-locations', methods=['GET'])
def get_locations():
    return jsonify(controllers.get_campus_locations())

# =============================================================================
# PHASE 3: SERVICES & SKILLS MARKETPLACE API ENDPOINTS
# =============================================================================

@app.route('/api/services', methods=['GET'])
def list_services():
    cat_id = request.args.get('category_id')
    search = request.args.get('search', '')
    status = request.args.get('status', 'Active')
    
    services_raw = controllers.get_services(category_id=cat_id, keyword=search, status=status)
    res = []
    if services_raw:
        for s in services_raw:
            res.append({
                "service_id": s[0],
                "provider_id": s[1],
                "provider_name": s[2],
                "provider_department": s[3],
                "verification_level": s[4],
                "category_id": s[5],
                "category_name": s[6],
                "title": s[7],
                "description": s[8],
                "subcategory": s[9],
                "pricing_model": s[10],
                "price": float(s[11]),
                "delivery_time_days": int(s[12]),
                "portfolio_urls": s[13] if s[13] else "",
                "status": s[14],
                "avg_rating": round(float(s[15]), 1) if s[15] is not None else 5.0,
                "review_count": int(s[16]) if len(s) > 16 else 0
            })
    return jsonify(res)

@app.route('/api/services/<int:service_id>', methods=['GET'])
def get_service_details(service_id):
    svc = controllers.get_service_by_id(service_id)
    if not svc:
        return jsonify({"success": False, "message": "Service not found"}), 404
    return jsonify({"success": True, "service": svc})

@app.route('/api/services', methods=['POST'])
@require_auth
def create_new_service():
    auth_provider_id = get_auth_user_id()
    data = request.json or {}
    
    try:
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        category_id = int(data['category_id'])
        subcategory = data.get('subcategory', '').strip()
        pricing_model = data.get('pricing_model', 'Fixed')
        price = float(data['price'])
        delivery_time_days = int(data.get('delivery_time_days', 3))
        portfolio_urls = data.get('portfolio_urls')
        
        if not title or price < 0 or delivery_time_days < 1:
            return jsonify({"success": False, "message": "Invalid service parameters."}), 400
            
        svc_id = controllers.create_service(
            provider_id=auth_provider_id, # Server-derived identity
            category_id=category_id,
            title=title,
            description=description,
            subcategory=subcategory,
            pricing_model=pricing_model,
            price=price,
            delivery_time_days=delivery_time_days,
            portfolio_urls=portfolio_urls
        )
        if svc_id > 0:
            return jsonify({"success": True, "service_id": svc_id})
        return jsonify({"success": False, "message": "Failed to create service"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/services/<int:service_id>', methods=['PUT'])
@require_auth
def update_existing_service(service_id):
    auth_provider_id = get_auth_user_id()
    data = request.json or {}
    
    try:
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        subcategory = data.get('subcategory', '').strip()
        pricing_model = data.get('pricing_model', 'Fixed')
        price = float(data['price'])
        delivery_time_days = int(data.get('delivery_time_days', 3))
        portfolio_urls = data.get('portfolio_urls')
        
        res = controllers.update_service(
            service_id=service_id,
            provider_id=auth_provider_id, # Ownership asserted in controller
            title=title,
            description=description,
            subcategory=subcategory,
            pricing_model=pricing_model,
            price=price,
            delivery_time_days=delivery_time_days,
            portfolio_urls=portfolio_urls
        )
        if res > 0:
            return jsonify({"success": True, "message": "Service updated successfully"})
        elif res == -3:
            return jsonify({"success": False, "message": "Unauthorized. You do not own this service."}), 403
        else:
            return jsonify({"success": False, "message": "Service not found or update failed."}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/services/<int:service_id>/status', methods=['POST'])
@require_auth
def set_service_status(service_id):
    auth_provider_id = get_auth_user_id()
    data = request.json or {}
    status = data.get('status', 'Active')
    
    res = controllers.update_service_status(service_id, auth_provider_id, status)
    if res > 0:
        return jsonify({"success": True, "message": f"Service status set to {status}"})
    elif res == -3:
        return jsonify({"success": False, "message": "Unauthorized. You do not own this service."}), 403
    return jsonify({"success": False, "message": "Could not update service status."}), 400

@app.route('/api/services/my-services', methods=['GET'])
@require_auth
def get_my_created_services():
    auth_provider_id = get_auth_user_id()
    services_raw = controllers.get_my_services(auth_provider_id) or []
    res = []
    for s in services_raw:
        res.append({
            "service_id": s[0],
            "category_id": s[1],
            "category_name": s[2],
            "title": s[3],
            "description": s[4],
            "subcategory": s[5],
            "pricing_model": s[6],
            "price": float(s[7]),
            "delivery_time_days": int(s[8]),
            "status": s[9],
            "created_at": s[10]
        })
    return jsonify(res)

# --- SERVICE ORDERS ENDPOINTS ---

@app.route('/api/services/orders', methods=['POST'])
@require_auth
def place_service_order():
    auth_client_id = get_auth_user_id()
    data = request.json or {}
    
    try:
        service_id = int(data['service_id'])
        requirements = data.get('requirements', '').strip()
        due_date = data.get('due_date', datetime.now().strftime("%Y-%m-%d"))
        
        if not requirements:
            return jsonify({"success": False, "message": "Requirements must be specified."}), 400
            
        order_id = controllers.create_service_order(
            service_id=service_id,
            client_id=auth_client_id, # Server-derived client identity
            requirements=requirements,
            due_date=due_date
        )
        if order_id > 0:
            log_financial_event("SERVICE_ORDER_ESCROW_HOLD", auth_client_id, float(data.get('amount', 0.0)), "service_order", order_id, "HELD")
            return jsonify({"success": True, "order_id": order_id})
        elif order_id == -4:
            return jsonify({"success": False, "message": "You cannot order your own service."}), 400
        elif order_id == -2:
            return jsonify({"success": False, "message": "This service is currently not active."}), 400
        else:
            return jsonify({"success": False, "message": "Failed to create service order."}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/services/orders/client', methods=['GET'])
@require_auth
def get_my_client_orders():
    auth_client_id = get_auth_user_id()
    orders_raw = controllers.get_client_orders(auth_client_id) or []
    res = []
    for o in orders_raw:
        res.append({
            "order_id": o[0],
            "service_id": o[1],
            "service_title": o[2],
            "provider_id": o[3],
            "provider_name": o[4],
            "requirements": o[5],
            "amount": float(o[6]),
            "status": o[7],
            "escrow_status": o[8],
            "due_date": o[9],
            "delivered_at": o[10],
            "completed_at": o[11],
            "created_at": o[12]
        })
    return jsonify(res)

@app.route('/api/services/orders/provider', methods=['GET'])
@require_auth
def get_my_provider_orders():
    auth_provider_id = get_auth_user_id()
    orders_raw = controllers.get_provider_orders(auth_provider_id) or []
    res = []
    for o in orders_raw:
        res.append({
            "order_id": o[0],
            "service_id": o[1],
            "service_title": o[2],
            "client_id": o[3],
            "client_name": o[4],
            "requirements": o[5],
            "amount": float(o[6]),
            "platform_fee": float(o[7]),
            "provider_earnings": float(o[8]),
            "status": o[9],
            "escrow_status": o[10],
            "due_date": o[11],
            "delivered_at": o[12],
            "completed_at": o[13],
            "created_at": o[14]
        })
    return jsonify(res)

@app.route('/api/services/orders/<int:order_id>', methods=['GET'])
@require_auth
def get_order_details_endpoint(order_id):
    auth_uid = get_auth_user_id()
    res = controllers.get_service_order_details(order_id, auth_uid)
    if res == -3:
        return jsonify({"success": False, "message": "Unauthorized. You are not a party to this order."}), 403
    if not res:
        return jsonify({"success": False, "message": "Order not found."}), 404
    return jsonify({"success": True, "order": res})

@app.route('/api/services/orders/<int:order_id>/accept', methods=['POST'])
@require_auth
def accept_order_endpoint(order_id):
    auth_provider_id = get_auth_user_id()
    res = controllers.accept_service_order(order_id, auth_provider_id)
    if res == 1:
        return jsonify({"success": True, "message": "Order accepted successfully"})
    elif res == -3:
        return jsonify({"success": False, "message": "Unauthorized. Only the assigned provider can accept this order."}), 403
    return jsonify({"success": False, "message": "Could not accept order."}), 400

@app.route('/api/services/orders/<int:order_id>/start', methods=['POST'])
@require_auth
def start_order_endpoint(order_id):
    auth_provider_id = get_auth_user_id()
    res = controllers.start_service_order(order_id, auth_provider_id)
    if res == 1:
        return jsonify({"success": True, "message": "Order marked as In Progress"})
    elif res == -3:
        return jsonify({"success": False, "message": "Unauthorized. Only the assigned provider can start this order."}), 403
    return jsonify({"success": False, "message": "Could not start order."}), 400

@app.route('/api/services/orders/<int:order_id>/deliver', methods=['POST'])
@require_auth
def deliver_order_endpoint(order_id):
    auth_provider_id = get_auth_user_id()
    data = request.json or {}
    notes = data.get('delivery_notes', '')
    res = controllers.deliver_service_order(order_id, auth_provider_id, notes)
    if res == 1:
        return jsonify({"success": True, "message": "Deliverables submitted for client review"})
    elif res == -3:
        return jsonify({"success": False, "message": "Unauthorized. Only the assigned provider can submit deliverables."}), 403
    return jsonify({"success": False, "message": "Could not deliver order."}), 400

@app.route('/api/services/orders/<int:order_id>/complete', methods=['POST'])
@require_auth
def complete_order_endpoint(order_id):
    auth_client_id = get_auth_user_id()
    res = controllers.complete_service_order(order_id, auth_client_id)
    if res == 1:
        log_financial_event("SERVICE_ORDER_ESCROW_RELEASE", auth_client_id, 0.0, "service_order", order_id, "RELEASED")
        return jsonify({"success": True, "message": "Order completed and earnings released to provider."})
    elif res == -3:
        return jsonify({"success": False, "message": "Unauthorized. Only the client who placed the order can confirm completion."}), 403
    return jsonify({"success": False, "message": "Order cannot be completed in its current state."}), 400

@app.route('/api/services/orders/<int:order_id>/cancel', methods=['POST'])
@require_auth
def cancel_order_endpoint(order_id):
    auth_uid = get_auth_user_id()
    data = request.json or {}
    reason = data.get('reason', 'Cancelled by user')
    res = controllers.cancel_service_order(order_id, auth_uid, reason)
    if res == 1:
        log_financial_event("SERVICE_ORDER_ESCROW_REFUND", auth_uid, 0.0, "service_order", order_id, "REFUNDED")
        return jsonify({"success": True, "message": "Order cancelled and escrow refunded."})
    elif res == -3:
        return jsonify({"success": False, "message": "Unauthorized. You cannot cancel this order."}), 403
    return jsonify({"success": False, "message": "Order cannot be cancelled in its current state."}), 400

@app.route('/api/services/reviews', methods=['POST'])
@require_auth
def submit_service_review_endpoint():
    auth_client_id = get_auth_user_id()
    data = request.json or {}
    
    try:
        order_id = int(data['order_id'])
        rating = int(data['rating'])
        comment = data.get('comment', '').strip()
        
        if rating < 1 or rating > 5:
            return jsonify({"success": False, "message": "Rating must be between 1 and 5."}), 400
            
        res = controllers.submit_service_review(order_id, auth_client_id, rating, comment)
        if res > 0:
            return jsonify({"success": True, "review_id": res})
        elif res == -3:
            return jsonify({"success": False, "message": "Unauthorized. Only the purchasing client can review this order."}), 403
        elif res == -2:
            return jsonify({"success": False, "message": "Reviews can only be submitted for Completed orders."}), 400
        elif res == -4:
            return jsonify({"success": False, "message": "You have already reviewed this service order."}), 400
        return jsonify({"success": False, "message": "Failed to submit review."}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

# =============================================================================
# PHASE 4: WALLET, ESCROW, PAYOUTS & MOBILE MONEY API ENDPOINTS
# =============================================================================

@app.route('/api/user/wallet', methods=['GET'])
@require_auth
def get_user_wallet_endpoint():
    auth_uid = get_auth_user_id()
    summary = FinancialService.get_wallet_summary(auth_uid)
    
    txs_raw = db_engine.execute_query("""
    SELECT wallet_tx_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes, created_at
    FROM wallet_transactions WHERE user_id = ?
    ORDER BY created_at DESC;
    """, (auth_uid,), fetch="all")
    
    formatted_txs = []
    if txs_raw:
        for t in txs_raw:
            formatted_txs.append({
                "wallet_tx_id": t["wallet_tx_id"],
                "entry_type": t["entry_type"],
                "tx_type": t["tx_type"],
                "amount": float(t["amount"]),
                "reference_type": t["reference_type"],
                "reference_id": t["reference_id"],
                "idempotency_key": t["idempotency_key"],
                "status": t["status"],
                "notes": t["notes"],
                "created_at": t["created_at"]
            })
            
    return jsonify({
        "success": True,
        "wallet": summary,
        "transactions": formatted_txs
    })

@app.route('/api/wallet/deposit/momo', methods=['POST'])
@require_auth
@rate_limit(max_requests=5, window_seconds=60)
def initiate_momo_deposit_endpoint():
    auth_uid = get_auth_user_id()
    data = request.json or {}
    
    try:
        amount = Decimal(str(data.get('amount', '0.00')))
        network = data.get('network', 'MTN MoMo')
        phone = data.get('phone_number', '').strip()
        
        ok, msg, result = FinancialService.initiate_momo_deposit(
            user_id=auth_uid,
            amount=amount,
            network=network,
            phone_number=phone
        )
        if ok:
            return jsonify({"success": True, "message": msg, "deposit": result})
        return jsonify({"success": False, "message": msg}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/wallet/withdraw/momo', methods=['POST'])
@require_auth
@rate_limit(max_requests=3, window_seconds=300)
def initiate_momo_withdrawal_endpoint():
    auth_uid = get_auth_user_id()
    data = request.json or {}
    
    try:
        amount = Decimal(str(data.get('amount', '0.00')))
        network = data.get('network', 'MTN MoMo')
        phone = data.get('phone_number', '').strip()
        
        ok, msg, result = FinancialService.request_momo_withdrawal(
            user_id=auth_uid,
            amount=amount,
            network=network,
            phone_number=phone
        )
        if ok:
            return jsonify({"success": True, "message": msg, "withdrawal": result})
        return jsonify({"success": False, "message": msg}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/payments/momo/verify/<path:reference>', methods=['GET'])
@require_auth
def verify_momo_transaction_endpoint(reference):
    gateway = get_payment_gateway()
    gw_resp = gateway.verify_transaction(reference)
    return jsonify(gw_resp.to_dict())

@app.route('/api/payments/momo/webhook', methods=['POST'])
def handle_momo_webhook_endpoint():
    """
    Cryptographically authenticated, timestamp-validated, and atomically idempotent webhook handler.
    Supports deposit settlements and payout confirmations from Mobile Money gateways.
    """
    raw_payload = request.get_data()
    sig_header = request.headers.get("X-CampusLink-Signature") or request.headers.get("X-Paystack-Signature", "")
    
    gateway = get_payment_gateway()
    if not gateway.verify_webhook_signature(raw_payload, sig_header):
        log_security_event("INVALID_WEBHOOK_SIGNATURE", None, "UNAUTHORIZED", request.remote_addr)
        return jsonify({"success": False, "message": "Invalid cryptographic webhook signature."}), 401
        
    data = request.json or {}
    event_type = data.get("event", "")
    payload_data = data.get("data", {})
    ts = data.get("timestamp", 0)
    
    # Replay protection: Check timestamp freshness (within 300 seconds)
    import time
    if abs(time.time() - ts) > 300:
        log_security_event("EXPIRED_WEBHOOK_TIMESTAMP", None, "UNAUTHORIZED", request.remote_addr, {"timestamp": ts})
        return jsonify({"success": False, "message": "Webhook timestamp expired."}), 401
        
    ref = payload_data.get("reference", "")
    gw_status = payload_data.get("status", "")
    gw_id = payload_data.get("gateway_tx_id", f"GW_{ref}")
    amount = Decimal(str(payload_data.get("amount", "0.00")))
    user_id = payload_data.get("customer", {}).get("user_id")
    
    if "charge" in event_type or "deposit" in event_type:
        if gw_status == "Successful":
            task = process_momo_deposit_webhook_task.delay(
                reference=ref,
                user_id=int(user_id),
                amount_str=str(amount),
                gateway_tx_id=gw_id
            )
            if PlatformConfig.CELERY_ALWAYS_EAGER:
                res = task.result or {}
                return jsonify({"success": res.get("success", False), "message": res.get("message", "")})
            else:
                return jsonify({
                    "success": True,
                    "message": "Deposit webhook accepted for background settlement.",
                    "task_id": task.id,
                    "reference": ref
                }), 202
        else:
            return jsonify({"success": True, "message": f"Deposit status '{gw_status}' recorded; no funds credited."})
            
    elif "payout" in event_type or "transfer" in event_type:
        success = (gw_status == "Successful")
        task = process_momo_payout_webhook_task.delay(
            reference=ref,
            success=success,
            notes=f"Gateway: {gw_id}"
        )
        if PlatformConfig.CELERY_ALWAYS_EAGER:
            res = task.result or {}
            return jsonify({"success": res.get("success", False), "message": res.get("message", "")})
        else:
            return jsonify({
                "success": True,
                "message": "Payout webhook accepted for background processing.",
                "task_id": task.id,
                "reference": ref
            }), 202

    return jsonify({"success": True, "message": "Event processed."})

@app.route('/api/admin/financial/reconcile', methods=['POST'])
@require_auth
@require_roles('Admin')
def run_financial_reconciliation_endpoint():
    data = request.json or {}
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    task = run_periodic_reconciliation_task.delay(start_date=start_date, end_date=end_date)
    if PlatformConfig.CELERY_ALWAYS_EAGER:
        report = ReconciliationEngine.reconcile_transactions(start_date=start_date, end_date=end_date)
        return jsonify(report)
    else:
        return jsonify({
            "success": True,
            "message": "Financial reconciliation task queued.",
            "task_id": task.id
        }), 202


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[SERVER] Launching CampusLink Web Server on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
