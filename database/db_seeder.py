import sqlite3
import os
import sys
import hashlib
import random
from datetime import datetime, timedelta

# Handle imports whether run directly or as a module
try:
    from . import database_schema as db_schema
except ImportError:
    import database_schema as db_schema

def hash_password(password, salt="umat_campuslink_2026"):
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"pbkdf2_sha256$100000${salt}${key.hex()}"

def seed_database():
    # Make sure all 15 tables exist
    db_schema.create_tables()
    
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()
    
    print("Seeding CampusLink 2.0 database...")
    
    # 1. Clear existing data in reverse relational dependency order
    cursor.execute("DELETE FROM wallet_transactions;")
    cursor.execute("DELETE FROM user_wallets;")
    cursor.execute("DELETE FROM service_reviews;")
    cursor.execute("DELETE FROM service_orders;")
    cursor.execute("DELETE FROM services;")
    cursor.execute("DELETE FROM saved_listings;")
    cursor.execute("DELETE FROM wishlist;")
    cursor.execute("DELETE FROM reviews;")
    cursor.execute("DELETE FROM maintenance;")
    cursor.execute("DELETE FROM rental_transactions;")
    cursor.execute("DELETE FROM rental_requests;")
    cursor.execute("DELETE FROM notifications;")
    cursor.execute("DELETE FROM listings;")
    cursor.execute("DELETE FROM categories;")
    cursor.execute("DELETE FROM users;")
    try:
        cursor.execute("DELETE FROM sqlite_sequence;")
    except Exception:
        pass
    
    # 2. Seed Categories (13 Categories covering Equipment & Services)
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
    cursor.executemany("INSERT INTO categories (name, description) VALUES (?, ?);", categories)
    print(f"Seeded {len(categories)} categories.")

    # 3. Seed Users with PBKDF2 Password Hashes
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
    cursor.executemany("""
    INSERT INTO users (name, email, password_hash, student_id, phone, verification_level, account_status, department, hostel)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, users)
    print(f"Seeded {len(users)} users.")

    # 4. Seed 61 Realistic UMaT Equipment Listings
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
            ('Binatone 1.7L Stainless Electric Kettle', 'Kettle', 'Binatone', 'CEK-1704', 2023, 6.0, 25.0, 'New', 'Available', 'K.T. Hall', 'assets/products/binatone_kettle.png', 'Fast boil 1850W stainless steel electric kettle with auto shut-off.'),
            ('Rechargeable 16-inch Standing Fan with LED Light', 'Fan', 'Lontor', 'CTL-CF160', 2023, 10.0, 50.0, 'New', 'Available', 'Gold Refinery Hostel', 'assets/products/standing_fan_16in.png', 'Oscillating rechargeable fan for hot nights and power outages.'),
            ('Philips 1000W Dry Iron', 'Iron', 'Philips', 'GC160/02', 2022, 5.0, 20.0, 'Good', 'Available', 'Dr. M.T. Kofi Hall', 'assets/products/philips_dry_iron.png', 'Non-stick soleplate dry iron for smooth clothes ironing.')
        ],
        9: [
            ('Stiga Carbon Table Tennis Racket Set + Balls', 'Table Tennis Set', 'Stiga', 'Pro Carbon', 2022, 8.0, 30.0, 'Good', 'Available', 'Gold Refinery Hostel', 'assets/products/stiga_table_tennis_set.png', 'Professional 7-ply table tennis bats plus 6 3-star tournament balls.'),
            ('Adidas FIFA World Cup Match Football (Size 5)', 'Football', 'Adidas', 'Al Rihla Pro', 2022, 10.0, 40.0, 'New', 'Available', 'Chamber of Mines Hostel', 'assets/products/adidas_match_football.png', 'Official size 5 match football for hostel tournaments.'),
            ('Adjustable Rubber Dumbbells Set (20kg Total)', 'Gym Dumbbells', 'Decathlon', 'Core 20kg', 2021, 15.0, 70.0, 'Good', 'Available', 'K.T. Hall', 'assets/products/dumbbells_20kg_set.png', 'Adjustable chrome dumbbell set with spinlock collars for hostel gym.')
        ],
        10: [
            ('Canon EOS 80D DSLR Camera + 18-135mm Kit', 'Camera', 'Canon', 'EOS 80D', 2021, 75.0, 350.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/canon_eos_80d.png', 'Great camera kit for events, field documentation, and media projects.'),
            ('Rode VideoMic Pro+ Shotgun Microphone', 'Microphone', 'Rode', 'VMP+', 2022, 25.0, 100.0, 'New', 'Available', 'Staff Quarters', 'assets/products/rode_videomic_pro.png', 'Broadcast grade camera-mount shotgun mic for high quality audio recording.'),
            ('Neewer 18-inch LED Ring Light & Tripod Stand', 'Ring Light', 'Neewer', 'RL-18', 2023, 20.0, 70.0, 'New', 'Available', 'Gold Refinery Hostel', 'assets/products/neewer_ring_light.png', 'Dimmable bi-color LED ring light with phone holder for content creation.')
        ],
        11: [
            ('Yamaha PSR-E373 61-Key Touch Keyboard', 'Keyboard', 'Yamaha', 'PSR-E373', 2022, 30.0, 150.0, 'Good', 'Available', 'Staff Quarters', 'assets/products/yamaha_psr_keyboard.png', 'Portable touch-sensitive keyboard with power adapter.'),
            ('Yamaha F310 Acoustic Guitar & Gig Bag', 'Acoustic Guitar', 'Yamaha', 'F310 Natural', 2021, 20.0, 80.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/yamaha_f310_guitar.png', 'Full size acoustic guitar with warm tone, tuner, and padded bag.')
        ],
        12: [
            ('Decathlon Rockrider ST100 Mountain Bike', 'Bicycle', 'Decathlon', 'ST100 27.5"', 2022, 20.0, 100.0, 'Good', 'Available', 'Gold Refinery Hostel', 'assets/products/decathlon_mountain_bike.png', 'Sturdy 21-speed mountain bike for quick campus commutes.'),
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

    cursor.executemany("""
    INSERT INTO listings (owner_id, category_id, title, subcategory, brand, model, purchase_year, rental_rate_per_day, deposit_amount, condition, status, pickup_location, thumbnail_path, available_from, available_until, description)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, listings)
    print(f"Seeded {len(listings)} realistic UMaT marketplace listings.")

    # 5. Seed Equipment Rental Transactions, Requests, Reviews, Wishlist, Saved Listings
    r_start_1 = (today - timedelta(days=15)).strftime("%Y-%m-%d")
    r_end_1 = (today - timedelta(days=10)).strftime("%Y-%m-%d")
    
    cursor.execute("""
    INSERT INTO rental_requests (listing_id, borrower_id, rent_start_date, rent_end_date, rental_purpose, status, notes)
    VALUES (4, 1, ?, ?, 'Field Trip', 'Approved', 'Need rock hammer for Tarkwa geological mapping project.');
    """, (r_start_1, r_end_1))
    req_1 = cursor.lastrowid

    cursor.execute("""
    INSERT INTO rental_transactions (request_id, listing_id, borrower_id, rent_start_date, rent_end_date, actual_return_date, total_days, gross_amount, commission_amount, owner_earnings, deposit_held, payment_status, rental_status, return_notes)
    VALUES (?, 4, 1, ?, ?, ?, 6, 90.00, 9.00, 81.00, 60.00, 'Paid', 'Returned', 'Returned in clean condition.');
    """, (req_1, r_start_1, r_end_1, r_end_1))
    tx_1 = cursor.lastrowid

    # Active ongoing rental
    r_start_2 = (today - timedelta(days=2)).strftime("%Y-%m-%d")
    r_end_2 = (today + timedelta(days=3)).strftime("%Y-%m-%d")

    cursor.execute("""
    INSERT INTO rental_requests (listing_id, borrower_id, rent_start_date, rent_end_date, rental_purpose, status, notes)
    VALUES (9, 1, ?, ?, 'Personal Use', 'Approved', 'For hostel room during exams.');
    """, (r_start_2, r_end_2))
    req_2 = cursor.lastrowid

    cursor.execute("""
    INSERT INTO rental_transactions (request_id, listing_id, borrower_id, rent_start_date, rent_end_date, total_days, gross_amount, commission_amount, owner_earnings, deposit_held, payment_status, rental_status)
    VALUES (?, 9, 1, ?, ?, 6, 90.00, 9.00, 81.00, 200.00, 'Paid', 'Active');
    """, (req_2, r_start_2, r_end_2))
    tx_2 = cursor.lastrowid

    # Reviews
    cursor.execute("INSERT INTO reviews (transaction_id, reviewer_id, reviewee_id, reviewee_type, rating, comment) VALUES (?, 1, 2, 'Lender', 5, 'Great equipment, works perfectly!');", (tx_1,))
    cursor.execute("INSERT INTO reviews (transaction_id, reviewer_id, reviewee_id, reviewee_type, rating, comment) VALUES (?, 2, 1, 'Borrower', 5, 'Very responsible student. Took great care of the rock hammer.');", (tx_1,))

    # Wishlist & Saved Listings
    cursor.execute("INSERT INTO wishlist (user_id, category_id, keyword) VALUES (1, 5, 'Oscilloscope');")
    cursor.execute("INSERT INTO wishlist (user_id, category_id, keyword) VALUES (2, 2, 'Total Station');")
    cursor.execute("INSERT INTO saved_listings (user_id, listing_id) VALUES (1, 5);")
    cursor.execute("INSERT INTO saved_listings (user_id, listing_id) VALUES (2, 1);")

    # Maintenance Ticket
    m_start = (today - timedelta(days=20)).strftime("%Y-%m-%d")
    m_end = (today - timedelta(days=18)).strftime("%Y-%m-%d")
    cursor.execute("""
    INSERT INTO maintenance (listing_id, reported_by, issue_description, cost, status, start_date, end_date)
    VALUES (1, 1, 'Laser plummet lens cleaning and re-calibration.', 150.00, 'Completed', ?, ?);
    """, (m_start, m_end))

    # =========================================================================
    # 6. SEED SERVICES & SKILLS MARKETPLACE (PHASE 1 EXPANSION)
    # =========================================================================
    services_data = [
        # (provider_id, category_id, title, description, subcategory, pricing_model, price, delivery_time_days)
        (1, 1, 'AutoCAD & ArcGIS Map Drafting', 'Professional engineering map digitization, contour plotting, and GIS spatial data analysis for UMaT project work.', 'CAD & GIS', 'Fixed', 80.00, 2),
        (2, 5, 'Laptop Thermal Paste & Dust Cleaning', 'Complete laptop teardown, dust blowout, fan cleaning, and arctic MX-4 thermal paste replacement for overheating laptops.', 'Laptop Maintenance', 'Fixed', 45.00, 1),
        (3, 10, 'Campus Event Photography & Headshots', 'Professional DSLR event coverage, matriculation/graduation portraits, and executive LinkedIn headshots.', 'Photography', 'Hourly', 60.00, 2),
        (4, 1, 'Python & C++ Programming Tutoring', 'One-on-one algorithmic tutoring, debugging assistance, and lab assignment preparation for computer engineering students.', 'Academic Tutoring', 'Hourly', 40.00, 1),
        (5, 13, 'Graphic Design & Presentation Decks', 'Custom PowerPoint presentation design, project poster layouts, and society flyer designs in high resolution.', 'Graphic Design', 'Fixed', 50.00, 2),
        (1, 5, 'Electronics & Arduino Prototyping Aid', 'Circuit schematic review, soldering assistance, and microcontroller sensor interfacing for final year projects.', 'Electronics Repair', 'Fixed', 70.00, 3)
    ]
    cursor.executemany("""
    INSERT INTO services (provider_id, category_id, title, description, subcategory, pricing_model, price, delivery_time_days, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active');
    """, services_data)
    print(f"Seeded {len(services_data)} student services across UMaT departments.")

    # =========================================================================
    # 7. SEED USER WALLETS & AUTHORITATIVE FINANCIAL LEDGER
    # =========================================================================
    # 7. SEED USER WALLETS & AUTHORITATIVE FINANCIAL LEDGER
    # =========================================================================
    # Initialize one wallet per user (including dedicated system entities)
    wallets_data = [
        # (user_id, available_balance, pending_balance, locked_escrow, total_earned, total_withdrawn)
        (1, 81.00, 0.00, 0.00, 81.00, 0.00),   # Albert: GHS 81.00 earned from Tx #1
        (2, 0.00, 81.00, 0.00, 0.00, 0.00),    # Benedict: GHS 81.00 pending from active Tx #2
        (3, 0.00, 0.00, 0.00, 0.00, 0.00),     # Grace
        (4, 0.00, 0.00, 0.00, 0.00, 0.00),     # Dr. Asante
        (5, 0.00, 0.00, 0.00, 0.00, 0.00),     # Abena
        (6, 9.00, 0.00, 0.00, 9.00, 0.00),     # Platform Commission Vault: GHS 9.00 earned fee on Tx #1
        (7, 0.00, 0.00, 0.00, 0.00, 0.00),     # System Escrow Custody Vault: GHS 0.00 net after Tx #1 release
        (8, 0.00, 0.00, 0.00, 0.00, 0.00),     # MoMo Gateway Clearing Account: GHS 0.00 net float
    ]
    cursor.executemany("""
    INSERT INTO user_wallets (user_id, available_balance, pending_balance, locked_escrow, total_earned, total_withdrawn)
    VALUES (?, ?, ?, ?, ?, ?);
    """, wallets_data)
    print(f"Seeded {len(wallets_data)} user wallets.")

    # Seed Initial Authoritative Ledger Transactions (matching wallet balances with dual-sided parity)
    # Tx #1: Estwing Rock Hammer (GH₵ 90.00 gross -> GH₵ 81.00 Albert, GH₵ 9.00 Admin)
    # Side A: System Escrow Release DEBIT (Wallet 7)
    cursor.execute("""
    INSERT INTO wallet_transactions (wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes)
    VALUES (7, 7, 'DEBIT', 'DepositEscrowHold', 90.00, 'rental_transaction', 1, 'DEMO_RENTAL_ESCROW_RELEASE_TX_1_DEBIT', 'Completed', 'Escrow release for rental Tx #1');
    """)

    # Side B1: Wallet 1 (Albert Boateng) Owner Earnings CREDIT
    cursor.execute("""
    INSERT INTO wallet_transactions (wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes)
    VALUES (1, 1, 'CREDIT', 'RentalIncome', 81.00, 'rental_transaction', 1, 'DEMO_RENTAL_EARNING_TX_1_CREDIT', 'Completed', 'Rental earnings for Estwing Rock Hammer');
    """)

    # Side B2: Wallet 6 (Platform Commission Vault) CREDIT
    cursor.execute("""
    INSERT INTO wallet_transactions (wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes)
    VALUES (6, 6, 'CREDIT', 'PlatformCommission', 9.00, 'rental_transaction', 1, 'DEMO_COMMISSION_TX_1_CREDIT', 'Completed', '10% Platform fee on Tx #1');
    """)

    conn.commit()
    conn.close()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_database()
