"""
database/db_seeder_mysql.py
---------------------------
Authoritative Database Seeder for MySQL and SQLite Database Engines.
Executes using dialect-normalized db_engine.
Seeds:
1. 13 UMaT marketplace categories.
2. 8 Users (Albert, Benedict, Grace, Dr. Kwame Asante, Abena, Commission Vault 6, Escrow Vault 7, Clearinghouse 8).
3. 61 Realistic UMaT marketplace listings.
4. 6 Student skill & service marketplace offerings.
5. 8 User wallets & balanced initial dual-entry ledger transactions (GH₵ 90.00 DEBIT = GH₵ 90.00 CREDIT).
"""
import os
import sys
import hashlib
import random
from datetime import datetime, timedelta

try:
    import db_engine
    from database import database_schema as db_schema
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import db_engine
    import database_schema as db_schema

def hash_password(password, salt="umat_campuslink_2026"):
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"pbkdf2_sha256$100000${salt}${key.hex()}"

def seed_database_engine():
    print("[SEEDER] Initializing CampusLink Database Seeding...")
    db_type, conn = db_engine.get_connection()
    conn.close()
    
    print(f"[SEEDER] Target Database Engine: {db_type.upper()}")

    # Ensure SQLite tables exist if running on SQLite
    if db_type == "sqlite":
        db_schema.create_tables()

    # 1. Clear existing data in reverse relational dependency order
    tables = [
        "wallet_transactions", "user_wallets", "service_reviews", "service_orders",
        "services", "saved_listings", "wishlist", "reviews", "maintenance",
        "rental_transactions", "rental_requests", "notifications", "listings",
        "categories", "users"
    ]
    for tbl in tables:
        try:
            db_engine.execute_query(f"DELETE FROM {tbl};", fetch="rowcount")
        except Exception:
            pass

    if db_type == "sqlite":
        try:
            db_engine.execute_query("DELETE FROM sqlite_sequence;", fetch="rowcount")
        except Exception:
            pass
    elif db_type == "mysql":
        for tbl in tables:
            try:
                db_engine.execute_query(f"ALTER TABLE {tbl} AUTO_INCREMENT = 1;", fetch="rowcount")
            except Exception:
                pass

    # 2. Seed Categories (13 Categories)
    categories = [
        ('Computing Devices', 'Laptops, tablets, monitors, and computer accessories.'),
        ('Surveying Equipment', 'Total Stations, GPS units, theodolites, levelling instruments.'),
        ('Mining PPE & Gear', 'Safety helmets, boots, high-vis vests, respirators, safety goggles.'),
        ('Geology Field Equipment', 'Geological hammers, hand lenses, compasses, streak plates.'),
        ('Electrical & Lab Tools', 'Oscilloscopes, digital multimeters, soldering stations, breadboards.'),
        ('Calculators & Books', 'Financial and scientific calculators, engineering textbooks.'),
        ('Presentation Gear', 'Projectors, clickers, portable screens, laser pointers.'),
        ('Hostel Appliances', 'Mini refrigerators, microwave ovens, kettles, fans, irons.'),
        ('Sports & Fitness', 'Table tennis bats, footballs, basketballs, gym equipment.'),
        ('Cameras & Media', 'DSLR cameras, tripods, microphones, lighting kits.'),
        ('Musical Instruments', 'Acoustic guitars, keyboards, amplifiers, rhythm pads.'),
        ('Bicycles & Transport', 'Mountain bikes, electric scooters, helmets.'),
        ('Drawing & Drafting', 'T-squares, drafting boards, set squares, technical pens.')
    ]
    for c in categories:
        db_engine.execute_query("INSERT INTO categories (name, description) VALUES (?, ?);", c, fetch="rowcount")
    print(f"[SEEDER] Seeded {len(categories)} categories.")

    # 3. Seed Users (8 Users)
    pass_student = hash_password('Student123')
    pass_staff   = hash_password('Staff123')
    pass_admin   = hash_password('Admin123')

    users = [
        ('Albert Boateng', 'ce-aavoryi8125@st.umat.edu.gh', pass_student, 'FCM.41.008.043.25', '+233241234567', 'Verified Student', 'Active', 'Geomatic Engineering', 'Chamber of Mines Hostel'),
        ('Benedict Osei', 'benedict@st.umat.edu.gh', pass_student, 'FCM.41.008.044.25', '+233209876543', 'Verified Student', 'Active', 'Mining Engineering', 'Gold Refinery Hostel'),
        ('Grace Mensah', 'grace@st.umat.edu.gh', pass_student, 'FCM.41.008.045.25', '+233551122334', 'Unverified', 'Active', 'Petroleum Engineering', 'K.T. Hall'),
        ('Dr. Kwame Asante', 'kasante@umat.edu.gh', pass_staff, None, '+233277889900', 'Verified Staff', 'Active', 'Electrical & Electronic Engineering', 'Staff Quarters'),
        ('Abena Owusu', 'abena@st.umat.edu.gh', pass_student, 'FCM.41.008.046.25', '+233543210987', 'Unverified', 'Active', 'Geological Engineering', 'Dr. M.T. Kofi Hall'),
        ('Admin CampusLink', 'admin@umat.edu.gh', pass_admin, None, '+233200000000', 'Admin', 'Active', 'Computer Science & Engineering', 'Main Admin Block'),
        ('System Escrow Custody', 'escrow.custody@umat.edu.gh', pass_admin, None, '+233200000001', 'Admin', 'Active', 'Platform Treasury', 'CampusLink Escrow Vault'),
        ('MoMo Gateway Clearing', 'momo.clearing@umat.edu.gh', pass_admin, None, '+233200000002', 'Admin', 'Active', 'Settlement Node', 'Gateway Clearinghouse')
    ]
    for u in users:
        db_engine.execute_query("""
        INSERT INTO users (name, email, password_hash, student_id, phone, verification_level, account_status, department, hostel)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, u, fetch="rowcount")
    print(f"[SEEDER] Seeded {len(users)} users.")

    # 4. Seed Listings (61 Listings across 13 Categories)
    today = datetime.now().date()
    start_avail = today.strftime("%Y-%m-%d")
    end_avail = (today + timedelta(days=90)).strftime("%Y-%m-%d")

    TEMPLATES = {
        1: [
            ('Dell XPS 15 Laptop (Core i7, 32GB RAM)', 'Laptop', 'Dell', 'XPS 9510', 2022, 90.0, 400.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/dell_xps15.png', 'High performance laptop for CAD, GIS, and rendering.'),
            ('HP 27-inch 4K IPS Monitor', 'Monitor', 'HP', 'Z27k G3', 2022, 40.0, 200.0, 'Good', 'Available', 'Staff Quarters', 'assets/products/hp_4k_monitor.png', 'Color accurate USB-C IPS monitor for design.'),
            ('MacBook Pro 14 (M1 Pro, 16GB)', 'Laptop', 'Apple', 'MacBook Pro 2021', 2021, 100.0, 500.0, 'New', 'Available', 'Gold Refinery Hostel', 'assets/products/macbook_pro14.png', 'Fast Apple Silicon laptop for software dev & video rendering.'),
            ('Western Digital 2TB Portable HDD', 'External Drive', 'WD', 'My Passport', 2023, 15.0, 60.0, 'New', 'Available', 'K.T. Hall', 'assets/products/wd_2tb_hdd.png', 'High capacity USB 3.0 backup drive for project files.'),
            ('Wacom Intuos Drawing Tablet', 'Graphics Tablet', 'Wacom', 'CTL-4100WL', 2022, 25.0, 100.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/wacom_intuos.png', 'Digital sketching & CAD drafting graphic pen tablet.'),
            ('TP-Link 4G Mobile Wi-Fi Router', 'Portable Router', 'TP-Link', 'M7350', 2023, 20.0, 80.0, 'New', 'Available', 'Dr. M.T. Kofi Hall', 'assets/products/tplink_4g_router.png', 'High speed 4G LTE pocket Wi-Fi hotspot for hostel study groups.'),
            ('Anker 26800mAh Fast Power Bank', 'Power Bank', 'Anker', 'PowerCore 26K', 2023, 15.0, 50.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/anker_powerbank.png', 'High capacity power bank for long field trips and power cuts.'),
            ('Logitech MX Master 3S Wireless Mouse', 'Accessory', 'Logitech', 'MX Master 3S', 2023, 12.0, 40.0, 'New', 'Available', 'Gold Refinery Hostel', 'assets/products/logitech_mx_master3s.png', 'Ergonomic precision wireless mouse with silent clicks.')
        ],
        2: [
            ('Leica Total Station TS07', 'Total Station', 'Leica', 'FlexLine TS07', 2022, 120.0, 500.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/leica_total_station_ts07.png', 'High precision surveying total station for field practicals.'),
            ('Garmin Handheld GPSMAP 64sx', 'GPS Unit', 'Garmin', 'GPSMAP 64sx', 2021, 35.0, 150.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/garmin_gpsmap_64sx.png', 'Rugged handheld GPS with navigation sensors.'),
            ('Heavy-Duty Wooden Surveying Tripod', 'Survey Tripod', 'Nedo', 'Wooden Tripod', 2020, 15.0, 60.0, 'Good', 'Available', 'Gold Refinery Hostel', 'assets/products/surveying_wooden_tripod.png', 'Sturdy wooden surveying tripod compatible with total stations.'),
            ('Sokkia Automatic Optical Level B20', 'Automatic Level', 'Sokkia', 'B20-35', 2022, 45.0, 200.0, 'New', 'Available', 'Chamber of Mines Hostel', 'assets/products/sokkia_optical_level_b20.png', 'High accuracy optical levelling instrument for elevation survey.'),
            ('Aluminum Telescopic Ranging Rod 5m', 'Ranging Rod', 'GeoMax', '5m Staff', 2021, 10.0, 40.0, 'Good', 'Available', 'K.T. Hall', 'assets/products/ranging_rod_5m.png', 'Lightweight 5m telescopic leveling staff with bubble level.'),
            ('Trimble R12i GNSS Receiver Kit', 'RTK GPS', 'Trimble', 'R12i', 2023, 150.0, 600.0, 'New', 'Available', 'Staff Quarters', 'assets/products/trimble_r12i_rtk.png', 'Top-tier RTK GNSS receiver with tilt compensation.'),
            ('50m Fibreglass Measuring Tape', 'Measuring Tape', 'Stanley', 'FatMax 50m', 2022, 8.0, 30.0, 'Good', 'Available', 'Gold Refinery Hostel', 'assets/products/fibreglass_tape_50m.png', 'Durable non-stretch fibreglass tape for field layout measurements.'),
            ('Surveyors Prism & Target Pole Set', 'Prism Set', 'Leica', 'GPR111', 2021, 25.0, 100.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/surveyors_prism_set.png', 'Standard single tilting prism set for distance measurement.')
        ],
        3: [
            ('Mining Safety Helmet & Boots Combo', 'PPE Kit', 'JSP / CAT', 'EVO3 / Holton', 2023, 25.0, 80.0, 'New', 'Available', 'Gold Refinery Hostel', 'assets/products/mining_ppe_combo.png', 'Hard hat plus size 43 steel toe work boots for industrial visits.'),
            ('JSP EVO3 Industrial Safety Hard Hat', 'Hard Hat', 'JSP', 'EVO3 Comfort', 2023, 10.0, 30.0, 'New', 'Available', 'Gold Refinery Hostel', 'assets/products/jsp_evo3_hard_hat.png', 'Ventilated industrial safety helmet with wheel ratchet.'),
            ('Caterpillar Holton Steel Toe Boots (Size 42)', 'Safety Boots', 'Caterpillar', 'Holton S3', 2022, 20.0, 70.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/caterpillar_steel_boots.png', 'Heavy duty S3 rated steel toe leather work boots.'),
            ('High-Vis Reflective Safety Vest (Class 2)', 'Reflective Vest', '3M', 'Scotchlite Class 2', 2023, 6.0, 20.0, 'New', 'Available', 'K.T. Hall', 'assets/products/high_vis_safety_vest.png', 'High visibility mesh reflective safety vest for underground visits.'),
            ('3M Half Facepiece Respirator 6200 Kit', 'Respirator', '3M', '6200 + P100', 2022, 15.0, 50.0, 'Good', 'Available', 'Gold Refinery Hostel', 'assets/products/3m_respirator_6200.png', 'Reusable respirator mask with P100 dust & organic vapour filters.'),
            ('UVEX Supravision Safety Goggles', 'Safety Glasses', 'UVEX', 'Ultravision', 2023, 8.0, 25.0, 'New', 'Available', 'Dr. M.T. Kofi Hall', 'assets/products/uvex_safety_goggles.png', 'Anti-fog scratch-resistant impact safety goggles for lab & mine tours.'),
            ('Heavy-Duty Mining Headlamp 1000 Lumens', 'Mining Headlamp', 'Fenix', 'HP30R V2.0', 2023, 18.0, 60.0, 'New', 'Available', 'Gold Refinery Hostel', 'assets/products/mining_headlamp.png', 'Rechargeable waterproof LED headlamp for pit and underground tours.'),
            ('Leather Work Gloves & Ear Defenders Combo', 'PPE Accessory', 'Honeywell', 'Rig Dog', 2022, 10.0, 30.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/work_gloves_ear_defenders.png', 'Cut-resistant leather impact gloves plus noise-cancelling ear muffs.')
        ],
        4: [
            ('Estwing 22oz Pointed Tip Rock Hammer', 'Rock Hammer', 'Estwing', 'E3-22P 22oz', 2020, 15.0, 60.0, 'Good', 'Available', 'Gold Refinery Hostel', 'assets/products/estwing_rock_hammer.png', 'Pointed tip 22oz rock pick hammer for field geology work.'),
            ('Brunton Pocket Transit Compass (0-360°)', 'Geology Compass', 'Brunton', 'Geo Transit', 2021, 30.0, 120.0, 'Good', 'Available', 'Staff Quarters', 'assets/products/brunton_compass.png', 'Precision geological compass for measuring dip and strike.'),
            ('Geologists 10x/20x Dual Hand Lens', 'Hand Lens', 'Bausch & Lomb', 'Hastings Triplet', 2022, 8.0, 30.0, 'New', 'Available', 'Dr. M.T. Kofi Hall', 'assets/products/geologists_hand_lens.png', 'High magnification triplet loupe for mineral field identification.'),
            ('Mohs Hardness Scale Test Kit (1-9)', 'Mineral Test Kit', 'Shortmann', 'Mohs Kit', 2021, 12.0, 40.0, 'Good', 'Available', 'Gold Refinery Hostel', 'assets/products/mohs_hardness_kit.png', 'Complete mineral hardness scratch testing set with streak plate.'),
            ('Waterproof Field Notebook & Geological Map Pouch', 'Field Supplies', 'Rite in the Rain', 'All-Weather Kit', 2023, 10.0, 30.0, 'New', 'Available', 'K.T. Hall', 'assets/products/geological_field_notebook.png', 'All-weather waterproof notebook with geological scale card.')
        ],
        5: [
            ('Rigol Digital Oscilloscope 100MHz (2-CH)', 'Oscilloscope', 'Rigol', 'DS1102Z-E', 2021, 50.0, 300.0, 'Good', 'Available', 'Staff Quarters', 'assets/products/rigol_oscilloscope_100mhz.png', '2-channel digital oscilloscope for lab experiments and projects.'),
            ('Fluke 87V Industrial Digital Multimeter', 'Multimeter', 'Fluke', '87V True-RMS', 2022, 20.0, 100.0, 'New', 'Available', 'Staff Quarters', 'assets/products/fluke_87v_multimeter.png', 'True-RMS industrial multimeter with temperature probe.'),
            ('TS100 Digital Soldering Iron Station', 'Soldering Kit', 'Miniware', 'TS100 65W', 2022, 15.0, 50.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/ts100_soldering_station.png', 'Portable smart OLED soldering iron with temperature control.'),
            ('Arduino Uno R3 Ultimate Starter Kit', 'Maker Kit', 'Elegoo', 'Uno R3 Super', 2023, 18.0, 60.0, 'New', 'Available', 'Gold Refinery Hostel', 'assets/products/arduino_uno_r3_kit.png', 'Complete microcontroller learning kit with sensors and breadboards.'),
            ('Raspberry Pi 4 Model B (8GB RAM Kit)', 'SBC Kit', 'Raspberry Pi', 'RPi4 8GB', 2022, 25.0, 90.0, 'New', 'Available', 'Chamber of Mines Hostel', 'assets/products/raspberry_pi_4.png', 'Powerful single board computer with official case & power supply.'),
            ('ESP32 Wi-Fi + Bluetooth Dev Board Set (3-Pack)', 'Microcontroller', 'Espressif', 'ESP32 WROOM', 2023, 12.0, 40.0, 'New', 'Available', 'K.T. Hall', 'assets/products/esp32_dev_boards.png', 'Dual-core IoT development boards for embedded systems project.'),
            ('DC Variable Bench Power Supply 30V 10A', 'Power Supply', 'Korad', 'KA3005D', 2021, 25.0, 100.0, 'Good', 'Available', 'Staff Quarters', 'assets/products/dc_bench_power_supply.png', 'Adjustable digital DC bench power supply for circuit prototyping.')
        ],
        6: [
            ('Casio FX-991EX ClassWiz Calculator', 'Calculator', 'Casio', 'FX-991EX', 2023, 10.0, 40.0, 'New', 'Available', 'Gold Refinery Hostel', 'assets/products/casio_fx991ex.png', 'Approved non-programmable scientific calculator for engineering exams.'),
            ('Texas Instruments TI-BA II Plus Financial Calculator', 'Calculator', 'TI', 'BA II Plus', 2022, 12.0, 50.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/ti_ba2_plus_calculator.png', 'Approved financial calculator for engineering economics courses.'),
            ('Principles of Geotechnical Engineering (Das & Sobhan)', 'Textbook', 'Cengage', '9th Edition', 2021, 8.0, 30.0, 'Good', 'Available', 'Gold Refinery Hostel', 'assets/products/geotechnical_eng_textbook.png', 'Standard reference textbook for civil & geological engineering.'),
            ('Introduction to Mining Engineering (Hartman & Mutmansky)', 'Textbook', 'Wiley', '2nd Edition', 2020, 10.0, 35.0, 'Good', 'Available', 'Gold Refinery Hostel', 'assets/products/mining_eng_textbook.png', 'Essential core reference book for mining engineering practicals.'),
            ('Surveying Principles and Applications (Kavanagh)', 'Textbook', 'Pearson', '9th Edition', 2022, 8.0, 30.0, 'New', 'Available', 'Chamber of Mines Hostel', 'assets/products/surveying_textbook.png', 'Comprehensive surveying textbook for geomatic engineering.')
        ],
        7: [
            ('Epson Portable HD Projector 3600 Lumens', 'Projector', 'Epson', 'EX3280', 2023, 60.0, 250.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/epson_hd_projector.png', 'Bright 3600 lumens HDMI projector for group presentations.'),
            ('Logitech R800 Green Laser Presentation Clicker', 'Clicker', 'Logitech', 'R800', 2022, 10.0, 40.0, 'New', 'Available', 'Staff Quarters', 'assets/products/logitech_r800_clicker.png', 'Wireless presentation clicker with bright green laser and LCD timer.'),
            ('100-inch Tripod Portable Projection Screen', 'Screen', 'Elite Screens', 'T100UWS1', 2021, 25.0, 100.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/projection_screen_100in.png', 'Foldable 1:1 format portable projector screen on sturdy tripod stand.')
        ],
        8: [
            ('Hisense 90L Compact Mini Refrigerator', 'Fridge', 'Hisense', 'REF093DR 90L', 2022, 15.0, 200.0, 'Good', 'Available', 'Gold Refinery Hostel', 'assets/products/hisense_mini_fridge.png', 'Compact hostel room fridge. Low power consumption.'),
            ('Sharp 20L Microwave Oven (800W)', 'Microwave', 'Sharp', 'R-200KW', 2022, 12.0, 80.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/sharp_microwave_oven.png', 'Compact countertop microwave oven for quick hostel meals.'),
            ('Binatone 1.7L Stainless Electric Kettle', 'Kettle', 'Binatone', 'CEK-1704', 2023, 6.0, 25.0, 'New', 'Available', 'K.T. Hall', 'assets/products/binatone_kettle.png', 'Fast boil 1850W stainless steel electric kettle with auto shut-off.')
        ],
        9: [
            ('Stiga Pro Carbon Table Tennis Racket Set', 'Table Tennis Set', 'Stiga', 'Pro Carbon', 2023, 15.0, 50.0, 'New', 'Available', 'Gold Refinery Hostel', 'assets/products/stiga_table_tennis_set.png', 'Tournament level table tennis bat with ITTF approved rubber.'),
            ('Wilson Evolution Official Game Basketball', 'Basketball', 'Wilson', 'Evolution Size 7', 2022, 10.0, 40.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/wilson_basketball.png', 'Indoor composite leather basketball for campus court games.')
        ],
        10: [
            ('Canon EOS 90D DSLR Camera Kit (18-135mm)', 'DSLR Camera', 'Canon', 'EOS 90D', 2022, 80.0, 450.0, 'Good', 'Available', 'Staff Quarters', 'assets/products/canon_eos_90d.png', '32.5MP 4K DSLR camera for campus event photography & videography.'),
            ('DJI Ronin-SC 3-Axis Camera Gimbal Stabilizer', 'Camera Gimbal', 'DJI', 'Ronin-SC', 2022, 40.0, 200.0, 'Good', 'Available', 'Gold Refinery Hostel', 'assets/products/dji_ronin_sc.png', 'Lightweight 3-axis stabilizer for cinematic video production.')
        ],
        11: [
            ('Yamaha F310 Acoustic Guitar', 'Acoustic Guitar', 'Yamaha', 'F310 Natural', 2021, 20.0, 100.0, 'Good', 'Available', 'K.T. Hall', 'assets/products/yamaha_f310_guitar.png', 'Full size steel string acoustic guitar with padded gig bag.'),
            ('Yamaha PSR-E373 Portable 61-Key Keyboard', 'Keyboard Piano', 'Yamaha', 'PSR-E373', 2022, 35.0, 180.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/yamaha_keyboard_psre373.png', 'Touch sensitive 61-key electronic keyboard for fellowship events.')
        ],
        12: [
            ('Giant Talon 29er Mountain Bike', 'Mountain Bike', 'Giant', 'Talon 2', 2022, 30.0, 150.0, 'Good', 'Available', 'Gold Refinery Hostel', 'assets/products/giant_mountain_bike.png', 'Reliable 29-inch hardtail mountain bike for campus commuting.'),
            ('Segway Ninebot E22 Electric Scooter', 'E-Scooter', 'Segway', 'Ninebot E22', 2023, 45.0, 200.0, 'New', 'Available', 'Chamber of Mines Hostel', 'assets/products/segway_ninebot_escooter.png', '20km/h lightweight electric scooter with dual brakes.')
        ],
        13: [
            ('Rotring Isograph Technical Pen Set (0.2, 0.3, 0.5mm)', 'Technical Pens', 'Rotring', 'Isograph Set', 2022, 12.0, 40.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/rotring_technical_pens.png', 'Precision technical drawing pens for engineering graphics.'),
            ('Wooden A1 Drafting Board & T-Square Combo', 'Drafting Board', 'Maped', 'A1 Wooden Board', 2021, 15.0, 50.0, 'Good', 'Available', 'Gold Refinery Hostel', 'assets/products/drawing_board.png', 'Smooth wooden A1 drafting board with 90cm acrylic T-square.')
        ]
    }

    listings = []
    owner_cycle = [1, 2, 4, 1, 2, 5, 1, 2, 4, 3] # Albert, Benedict, Dr. Asante, Abena, Grace
    listing_count = 0

    for cat_id, tmpl_list in TEMPLATES.items():
        for item in tmpl_list:
            owner_id = owner_cycle[listing_count % len(owner_cycle)]
            listing_count += 1
            item_img_path = item[10]
            listings.append((
                owner_id, cat_id, item[0], item[1], item[2], item[3], item[4],
                item[5], item[6], item[7], item[8], item[9], item_img_path,
                start_avail, end_avail, item[11]
            ))

    var_idx = 1
    random.seed(42) # Deterministic pseudo-randomness across engines
    while len(listings) < 61:
        cat_id = (var_idx % 13) + 1
        base_item = TEMPLATES[cat_id][var_idx % len(TEMPLATES[cat_id])]
        owner_id = owner_cycle[len(listings) % len(owner_cycle)]
        variant_title = f"{base_item[0]} (Unit #{var_idx+1})"
        rate = round(base_item[5] * random.choice([0.9, 1.0, 1.1]), 2)
        deposit = round(base_item[6] * random.choice([0.95, 1.0, 1.05]), 2)
        cond = random.choice(['New', 'Good', 'Fair'])
        item_img_path = base_item[10]
        listings.append((
            owner_id, cat_id, variant_title, base_item[1], base_item[2], f"{base_item[3]}-v{var_idx}",
            base_item[4], rate, deposit, cond, 'Available', base_item[9],
            item_img_path, start_avail, end_avail,
            f"{base_item[11]} Clean tested unit available for rental on campus."
        ))
        var_idx += 1

    for lst in listings:
        db_engine.execute_query("""
        INSERT INTO listings (owner_id, category_id, title, subcategory, brand, model, purchase_year, rental_rate_per_day, deposit_amount, `condition`, status, pickup_location, thumbnail_path, available_from, available_until, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, lst, fetch="rowcount")
    print(f"[SEEDER] Seeded {len(listings)} realistic UMaT marketplace listings.")

    # 5. Seed Services (6 Services)
    services_data = [
        (1, 1, 'AutoCAD & ArcGIS Map Drafting', 'Professional engineering map digitization, contour plotting, and GIS spatial data analysis for UMaT project work.', 'CAD & GIS', 'Fixed', 80.00, 2),
        (2, 5, 'Laptop Thermal Paste & Dust Cleaning', 'Complete laptop teardown, dust blowout, fan cleaning, and arctic MX-4 thermal paste replacement for overheating laptops.', 'Laptop Maintenance', 'Fixed', 45.00, 1),
        (3, 10, 'Campus Event Photography & Headshots', 'Professional DSLR event coverage, matriculation/graduation portraits, and executive LinkedIn headshots.', 'Photography', 'Hourly', 60.00, 2),
        (4, 1, 'Python & C++ Programming Tutoring', 'One-on-one algorithmic tutoring, debugging assistance, and lab assignment preparation for computer engineering students.', 'Academic Tutoring', 'Hourly', 40.00, 1),
        (5, 13, 'Graphic Design & Presentation Decks', 'Custom PowerPoint presentation design, project poster layouts, and society flyer designs in high resolution.', 'Graphic Design', 'Fixed', 50.00, 2),
        (1, 5, 'Electronics & Arduino Prototyping Aid', 'Circuit schematic review, soldering assistance, and microcontroller sensor interfacing for final year projects.', 'Electronics Repair', 'Fixed', 70.00, 3)
    ]
    for s in services_data:
        db_engine.execute_query("""
        INSERT INTO services (provider_id, category_id, title, description, subcategory, pricing_model, price, delivery_time_days, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active');
        """, s, fetch="rowcount")
    print(f"[SEEDER] Seeded {len(services_data)} student services.")

    # 6. Seed Wallets & Dual-Sided Authoritative Ledger Transactions
    wallets_data = [
        (1, 81.00, 0.00, 0.00, 81.00, 0.00),   # Albert: GHS 81.00 earned
        (2, 0.00, 81.00, 0.00, 0.00, 0.00),    # Benedict: GHS 81.00 pending
        (3, 0.00, 0.00, 0.00, 0.00, 0.00),     # Grace
        (4, 0.00, 0.00, 0.00, 0.00, 0.00),     # Dr. Asante
        (5, 0.00, 0.00, 0.00, 0.00, 0.00),     # Abena
        (6, 9.00, 0.00, 0.00, 9.00, 0.00),     # Commission Vault 6
        (7, 0.00, 0.00, 0.00, 0.00, 0.00),     # System Escrow Vault 7
        (8, 0.00, 0.00, 0.00, 0.00, 0.00),     # MoMo Clearing Account 8
    ]
    for w in wallets_data:
        db_engine.execute_query("""
        INSERT INTO user_wallets (user_id, available_balance, pending_balance, locked_escrow, total_earned, total_withdrawn)
        VALUES (?, ?, ?, ?, ?, ?);
        """, w, fetch="rowcount")
    print(f"[SEEDER] Seeded {len(wallets_data)} user wallets.")

    # Authoritative Double-Entry Ledger Initial State (Dual Parity: GH₵ 90.00 DEBIT = GH₵ 90.00 CREDIT)
    db_engine.execute_query("""
    INSERT INTO wallet_transactions (wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (7, 7, 'DEBIT', 'DepositEscrowHold', 90.00, 'rental_transaction', 1, 'DEMO_RENTAL_ESCROW_RELEASE_TX_1_DEBIT', 'Completed', 'Escrow release for rental Tx #1'), fetch="rowcount")

    db_engine.execute_query("""
    INSERT INTO wallet_transactions (wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (1, 1, 'CREDIT', 'RentalIncome', 81.00, 'rental_transaction', 1, 'DEMO_RENTAL_EARNING_TX_1_CREDIT', 'Completed', 'Rental earnings for Estwing Rock Hammer'), fetch="rowcount")

    db_engine.execute_query("""
    INSERT INTO wallet_transactions (wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (6, 6, 'CREDIT', 'PlatformCommission', 9.00, 'rental_transaction', 1, 'DEMO_COMMISSION_TX_1_CREDIT', 'Completed', '10% Platform fee on Tx #1'), fetch="rowcount")

    print("[SEEDER] CampusLink Database Seeding Completed Successfully.")

if __name__ == "__main__":
    seed_database_engine()
