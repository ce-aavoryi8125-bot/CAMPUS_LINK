import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QComboBox, QScrollArea, QGridLayout,
    QDialog, QDateEdit, QTextEdit, QMessageBox, QDoubleSpinBox,
    QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QDate, QSize
from PySide6.QtGui import QPixmap, QColor, QFont, QIcon

from .assets_manager import get_item_image_path, get_cached_item_pixmap
from .theme import CampusLinkTheme
import controllers

class MarketplaceCard(QFrame):
    quick_view_requested = Signal(dict)
    rent_requested = Signal(dict)
    wishlist_toggled = Signal(dict)

    def __init__(self, listing_data, current_user_id, parent=None):
        super().__init__(parent)
        self.listing = listing_data
        self.user_id = current_user_id
        
        self.setFixedSize(310, 450)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setObjectName("CardFrame")
        self.setStyleSheet("""
            QFrame#CardFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            QFrame#CardFrame:hover {
                border: 1px solid #4A5DDE;
            }
        """)

        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 12)
        main_layout.setSpacing(6)

        # Image container — dark background so padding around image looks clean
        img_container = QFrame()
        img_container.setFixedSize(310, 200)
        img_container.setStyleSheet(
            "border-top-left-radius: 12px; border-top-right-radius: 12px;"
            "background-color: #0F172A;"
        )

        img_layout = QVBoxLayout(img_container)
        img_layout.setContentsMargins(0, 0, 0, 0)
        img_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Product Image — KeepAspectRatio: entire product visible, no cropping
        pixmap = get_cached_item_pixmap(
            self.listing.get('thumbnail_path'),
            self.listing.get('category_id', 1),
            self.listing.get('listing_id'),
            width=310, height=200
        )
        lbl_img = QLabel()
        lbl_img.setFixedSize(310, 200)
        lbl_img.setPixmap(pixmap)
        lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_img.setStyleSheet("background-color: transparent;")
        img_layout.addWidget(lbl_img)

        # Overlay Badges Layout
        overlay_widget = QWidget(img_container)
        overlay_layout = QHBoxLayout(overlay_widget)
        overlay_layout.setContentsMargins(10, 10, 10, 10)

        # Category Badge (Top-Left)
        cat_badge = QLabel(self.listing.get('category_name', 'General')[:20])
        cat_badge.setStyleSheet("background-color: rgba(15, 23, 42, 0.88); color: #38BDF8; font-size: 10px; font-weight: bold; padding: 3px 8px; border-radius: 6px; border: 1px solid #38BDF8;")
        
        # Availability Badge (Top-Right)
        status = self.listing.get('status', 'Available')
        status_color = "#10B981" if status == "Available" else "#EF4444"
        status_badge = QLabel(status)
        status_badge.setStyleSheet(f"background-color: {status_color}; color: #FFFFFF; font-size: 10px; font-weight: bold; padding: 3px 8px; border-radius: 6px;")

        overlay_layout.addWidget(cat_badge, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        overlay_layout.addStretch()
        overlay_layout.addWidget(status_badge, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        
        overlay_widget.setGeometry(0, 0, 310, 50)
        main_layout.addWidget(img_container)

        # 2. Content Padding Container
        content_widget = QWidget()
        c_layout = QVBoxLayout(content_widget)
        c_layout.setContentsMargins(12, 4, 12, 0)
        c_layout.setSpacing(4)

        # Product Title
        title = self.listing.get('title', 'Item Title')
        lbl_title = QLabel(title[:30] + ("..." if len(title) > 30 else ""))
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F8FAFC;")
        c_layout.addWidget(lbl_title)

        # Owner & Department
        owner = self.listing.get('owner_name', 'Owner')
        dept = self.listing.get('department', 'UMaT')
        lbl_owner = QLabel(f"👤 {owner} • {dept[:16]}")
        lbl_owner.setStyleSheet("font-size: 11px; color: #94A3B8;")
        c_layout.addWidget(lbl_owner)

        # Condition & Rating Row
        cond_row = QHBoxLayout()
        cond = self.listing.get('condition', 'Good')
        lbl_cond = QLabel(f"Condition: {cond}")
        lbl_cond.setStyleSheet("font-size: 10px; color: #CBD5E1;")

        lbl_stars = QLabel("★★★★★ 5.0")
        lbl_stars.setStyleSheet("font-size: 10px; font-weight: bold; color: #F59E0B;")

        cond_row.addWidget(lbl_cond)
        cond_row.addStretch()
        cond_row.addWidget(lbl_stars)
        c_layout.addLayout(cond_row)

        # Price & Deposit Row
        price_row = QHBoxLayout()
        rate = self.listing.get('rental_rate_per_day', 0.0)
        deposit = self.listing.get('deposit_amount', 0.0)

        lbl_rate = QLabel(f"GH₵ {rate:.2f} / day")
        lbl_rate.setStyleSheet("font-size: 16px; font-weight: bold; color: #10B981;")

        lbl_dep = QLabel(f"GH₵ {deposit:.2f} dep")
        lbl_dep.setStyleSheet("font-size: 11px; font-weight: bold; color: #F59E0B;")

        price_row.addWidget(lbl_rate)
        price_row.addStretch()
        price_row.addWidget(lbl_dep)
        c_layout.addLayout(price_row)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        # Wishlist button (compact heart icon)
        btn_wish = QPushButton("♥")
        btn_wish.setFixedWidth(34)
        btn_wish.setFixedHeight(34)
        btn_wish.setToolTip("Save to Wishlist")
        btn_wish.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #475569;
                border-radius: 6px;
                color: #EF4444;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(239,68,68,0.15);
                border-color: #EF4444;
            }
        """)
        btn_wish.clicked.connect(lambda: self.wishlist_toggled.emit(self.listing))

        # View Details button — outlined blue secondary
        btn_view = QPushButton("👁 View Details")
        btn_view.setFixedHeight(34)
        btn_view.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1.5px solid #3B82F6;
                border-radius: 6px;
                color: #93C5FD;
                font-size: 11px;
                font-weight: bold;
                padding: 0 8px;
            }
            QPushButton:hover {
                background-color: rgba(59,130,246,0.18);
                border-color: #60A5FA;
                color: #BFDBFE;
            }
            QPushButton:pressed {
                background-color: rgba(59,130,246,0.30);
            }
        """)
        btn_view.clicked.connect(lambda: self.quick_view_requested.emit(self.listing))

        # Rent Now button — filled emerald green primary
        is_rentable = (status == "Available" and self.listing.get('owner_id') != self.user_id)
        btn_rent = QPushButton("📦 Rent Now")
        btn_rent.setFixedHeight(34)
        btn_rent.setEnabled(is_rentable)
        if is_rentable:
            btn_rent.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #10B981, stop:1 #059669);
                    border: none;
                    border-radius: 6px;
                    color: #FFFFFF;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 0 8px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #34D399, stop:1 #10B981);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #059669, stop:1 #047857);
                }
            """)
        else:
            btn_rent.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    color: #475569;
                    font-size: 11px;
                    padding: 0 8px;
                }
            """)
        btn_rent.clicked.connect(lambda: self.rent_requested.emit(self.listing))

        btn_row.addWidget(btn_wish)
        btn_row.addWidget(btn_view)
        btn_row.addWidget(btn_rent)
        c_layout.addLayout(btn_row)

        main_layout.addWidget(content_widget)

class QuickViewDialog(QDialog):
    def __init__(self, listing, parent=None):
        super().__init__(parent)
        self.listing = listing
        self.setWindowTitle(f"Item Details - {listing.get('title')}")
        self.resize(540, 560)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)

        # Product Image Banner
        pixmap = get_cached_item_pixmap(
            self.listing.get('thumbnail_path'),
            self.listing.get('category_id', 1),
            self.listing.get('listing_id'),
            width=490, height=220
        )
        lbl_img = QLabel()
        lbl_img.setPixmap(pixmap)
        lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_img.setStyleSheet("border-radius: 12px; background-color: #0F172A;")
        layout.addWidget(lbl_img)

        # Title & Category Row
        lbl_t = QLabel(self.listing.get('title'))
        lbl_t.setStyleSheet("font-size: 20px; font-weight: bold; color: #4A5DDE;")
        layout.addWidget(lbl_t)

        lbl_c = QLabel(f"Category: {self.listing.get('category_name')} • Brand: {self.listing.get('brand')} • Model: {self.listing.get('model')}")
        lbl_c.setStyleSheet("font-size: 12px; color: #94A3B8;")
        layout.addWidget(lbl_c)

        # Owner Profile Box
        owner_frame = QFrame()
        owner_frame.setObjectName("CardFrame")
        o_layout = QHBoxLayout(owner_frame)
        o_layout.setContentsMargins(15, 10, 15, 10)

        owner_name = self.listing.get('owner_name', 'Owner')
        dept = self.listing.get('department', 'UMaT')
        trust = controllers.calculate_trust_score(self.listing.get('owner_id', 1))
        score = trust.get('score', 90) if isinstance(trust, dict) else 90

        lbl_owner_info = QLabel(f"<b>Owner:</b> {owner_name} ({dept})<br><span style='color:#10B981;'>★★★★★ 5.0 Rating</span>")
        lbl_trust_badge = QLabel(f"Trust Score: {score}/100")
        lbl_trust_badge.setStyleSheet("background-color: #D97706; color: #FFFFFF; font-weight: bold; padding: 6px 12px; border-radius: 6px;")

        o_layout.addWidget(lbl_owner_info)
        o_layout.addStretch()
        o_layout.addWidget(lbl_trust_badge)
        layout.addWidget(owner_frame)

        # Description Box
        layout.addWidget(QLabel("Item Description:"))
        txt_desc = QTextEdit()
        txt_desc.setReadOnly(True)
        txt_desc.setFixedHeight(70)
        txt_desc.setText(self.listing.get('description', 'Clean tested unit available for peer rental.'))
        layout.addWidget(txt_desc)

        # Pricing Box
        rate = self.listing.get('rental_rate_per_day', 0.0)
        deposit = self.listing.get('deposit_amount', 0.0)
        loc = self.listing.get('pickup_location', 'Campus')
        
        lbl_price = QLabel(f"Daily Rate: GH₵ {rate:.2f} / day | Security Deposit: GH₵ {deposit:.2f} | Pickup: {loc}")
        lbl_price.setStyleSheet("font-weight: bold; color: #10B981; font-size: 13px;")
        layout.addWidget(lbl_price)

        btn_close = QPushButton("Close Details")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

class RentRequestDialog(QDialog):
    def __init__(self, listing, borrower_id, parent=None):
        super().__init__(parent)
        self.listing = listing
        self.borrower_id = borrower_id
        self.setWindowTitle(f"Request Rental - {listing.get('title')}")
        self.resize(480, 480)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)

        lbl_t = QLabel(f"Rental Booking: {self.listing.get('title')}")
        lbl_t.setStyleSheet("font-size: 18px; font-weight: bold; color: #4A5DDE;")
        layout.addWidget(lbl_t)

        layout.addWidget(QLabel("Rental Purpose:"))
        self.cmb_purpose = QComboBox()
        self.cmb_purpose.addItems([
            "Field Trip", "Final Year Project", "Laboratory Session",
            "Research", "Presentation", "Personal Use"
        ])
        layout.addWidget(self.cmb_purpose)

        today = QDate.currentDate()
        layout.addWidget(QLabel("Start Date:"))
        self.date_start = QDateEdit(today.addDays(1))
        self.date_start.setCalendarPopup(True)
        layout.addWidget(self.date_start)

        layout.addWidget(QLabel("End Date:"))
        self.date_end = QDateEdit(today.addDays(6))
        self.date_end.setCalendarPopup(True)
        layout.addWidget(self.date_end)

        layout.addWidget(QLabel("Pickup & Return Instructions / Notes:"))
        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("e.g. Will pick up from Chamber of Mines Hostel at 9am.")
        layout.addWidget(self.txt_notes)

        cost_frame = QFrame()
        cost_frame.setObjectName("CardFrame")
        cost_layout = QVBoxLayout(cost_frame)
        self.lbl_cost = QLabel("Estimated Duration: 5 Days\nGross Rental: GH₵ 0.00\nDeposit: GH₵ 0.00")
        self.lbl_cost.setStyleSheet("font-weight: bold; color: #10B981;")
        cost_layout.addWidget(self.lbl_cost)
        layout.addWidget(cost_frame)

        self.date_start.dateChanged.connect(self.update_cost)
        self.date_end.dateChanged.connect(self.update_cost)
        self.update_cost()

        btn_box = QHBoxLayout()
        btn_sub = QPushButton("Submit Rental Request")
        btn_sub.clicked.connect(self.handle_submit)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("SecondaryButton")
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_sub)
        layout.addLayout(btn_box)

    def update_cost(self):
        s_date = self.date_start.date().toPython()
        e_date = self.date_end.date().toPython()
        days = (e_date - s_date).days + 1
        if days <= 0:
            days = 1
        rate = self.listing.get('rental_rate_per_day', 0.0)
        deposit = self.listing.get('deposit_amount', 0.0)
        gross = rate * days
        self.lbl_cost.setText(f"Duration: {days} Days | Gross Rental: GH₵ {gross:.2f} | Held Deposit: GH₵ {deposit:.2f}")

    def handle_submit(self):
        s_date = self.date_start.date().toString("yyyy-MM-dd")
        e_date = self.date_end.date().toString("yyyy-MM-dd")
        purpose = self.cmb_purpose.currentText()
        notes = self.txt_notes.toPlainText().strip()

        # Validate dates
        if self.date_end.date() < self.date_start.date():
            QMessageBox.warning(self, "Invalid Dates",
                "End date cannot be earlier than start date.\nPlease correct your rental period.")
            return

        if self.date_start.date() < self.date_start.date().currentDate():
            QMessageBox.warning(self, "Invalid Dates",
                "Start date cannot be in the past.\nPlease select a future date.")
            return

        # Check listing is still available before submitting
        current_status = self.listing.get('status', 'Available')
        if current_status != 'Available':
            QMessageBox.warning(self, "Item Unavailable",
                f"This item is currently '{current_status}' and cannot be rented.\n"
                "Please check the Marketplace for available items.")
            return

        try:
            res = controllers.submit_rental_request(
                self.listing['listing_id'],
                self.borrower_id,
                s_date,
                e_date,
                purpose,
                notes
            )
            if res and res != -1:
                QMessageBox.information(
                    self, "Request Submitted ✓",
                    "Rental request submitted successfully!\n\n"
                    "Waiting for owner approval.\n"
                    "You will see the approved rental in 'My Borrowed Assets' once the owner accepts."
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self, "Submission Failed",
                    "Failed to submit rental request. The item may no longer be available.\n"
                    "Please refresh the Marketplace and try again."
                )
        except Exception as e:
            QMessageBox.critical(
                self, "Unexpected Error",
                f"An unexpected error occurred while submitting your request:\n{str(e)}\n\n"
                "Please restart the application and try again."
            )

class MarketplaceView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_user_id = None
        self.listings_data = []
        self.filtered_listings = []
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header Title
        lbl_head = QLabel("UMaT Peer Resource Marketplace")
        lbl_head.setObjectName("HeaderTitle")
        main_layout.addWidget(lbl_head)

        # Search & Multi-Filter Bar
        filter_frame = QFrame()
        filter_frame.setObjectName("CardFrame")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(15, 12, 15, 12)
        filter_layout.setSpacing(10)

        # Real-time search bar with styling
        self.txt_search = QLineEdit()
        self.txt_search.setObjectName("SearchBar")
        self.txt_search.setPlaceholderText("🔍 Search Calculators, Laptops, GPS, Total Stations…")
        self.txt_search.setFixedHeight(36)
        self.txt_search.textChanged.connect(self.apply_filters)

        # Category Filter
        # Category filter combo with consistent styling
        self.cmb_cat = QComboBox()
        self.cmb_cat.setObjectName("FilterCombo")
        self.cmb_cat.setFixedHeight(32)
        self.cmb_cat.setMinimumWidth(150)
        self.cmb_cat.addItem("All Categories", 0)
        cats = controllers.get_categories()
        if cats:
            for c in cats:
                self.cmb_cat.addItem(c[1], c[0])
        self.cmb_cat.currentIndexChanged.connect(self.apply_filters)

        # Condition Filter
        # Condition filter combo
        self.cmb_cond = QComboBox()
        self.cmb_cond.setObjectName("FilterCombo")
        self.cmb_cond.setFixedHeight(32)
        self.cmb_cond.setMinimumWidth(150)
        self.cmb_cond.addItems(["All Conditions", "New", "Good", "Fair"])
        self.cmb_cond.currentIndexChanged.connect(self.apply_filters)

        # Department Filter
        # Department filter combo
        self.cmb_dept = QComboBox()
        self.cmb_dept.setObjectName("FilterCombo")
        self.cmb_dept.setFixedHeight(32)
        self.cmb_dept.setMinimumWidth(150)
        self.cmb_dept.addItems([
            "All Departments", "Geomatic Engineering", "Mining Engineering",
            "Petroleum Engineering", "Electrical & Electronic Engineering",
            "Geological Engineering", "Computer Science & Engineering"
        ])
        self.cmb_dept.currentIndexChanged.connect(self.apply_filters)

        # Availability Filter
        # Availability filter combo
        self.cmb_avail = QComboBox()
        self.cmb_avail.setObjectName("FilterCombo")
        self.cmb_avail.setFixedHeight(32)
        self.cmb_avail.setMinimumWidth(150)
        self.cmb_avail.addItems(["All Items", "Available Only", "Rented / Reserved"])
        self.cmb_avail.currentIndexChanged.connect(self.apply_filters)

        filter_layout.addWidget(self.txt_search, 3)
        filter_layout.addWidget(self.cmb_cat, 1)
        filter_layout.addWidget(self.cmb_cond, 1)
        filter_layout.addWidget(self.cmb_dept, 1)
        filter_layout.addWidget(self.cmb_avail, 1)
        main_layout.addWidget(filter_frame)

        # Scroll Area for Marketplace Cards Grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: transparent;")

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(18)

        self.scroll.setWidget(self.grid_widget)
        main_layout.addWidget(self.scroll)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.relayout_grid()

    def refresh(self, user_id):
        self.active_user_id = user_id
        self.load_listings()

    def load_listings(self):
        raw_listings = controllers.get_filtered_listings()
        self.listings_data = []

        if raw_listings:
            for r in raw_listings:
                self.listings_data.append({
                    'listing_id': r[0],
                    'title': r[1],
                    'description': r[2],
                    'subcategory': r[3],
                    'brand': r[4],
                    'model': r[5],
                    'rental_rate_per_day': r[6],
                    'deposit_amount': r[7],
                    'condition': r[8],
                    'status': r[9],
                    'pickup_location': r[10],
                    'owner_name': r[11],
                    'category_name': r[12],
                    'available_from': r[13],
                    'available_until': r[14],
                    'owner_id': r[15],
                    'category_id': r[16] if len(r) > 16 else 1,
                    'thumbnail_path': r[17] if len(r) > 17 else None,
                    'department': r[18] if len(r) > 18 else 'UMaT'
                })
        self.apply_filters()

    def apply_filters(self):
        query = self.txt_search.text().strip().lower()
        selected_cat_id = self.cmb_cat.currentData()
        cond_mode = self.cmb_cond.currentText()
        dept_mode = self.cmb_dept.currentText()
        avail_mode = self.cmb_avail.currentText()

        self.filtered_listings = []
        for item in self.listings_data:
            if query and not (query in item['title'].lower() or query in item['description'].lower() or query in item['brand'].lower() or query in item['subcategory'].lower()):
                continue
            if selected_cat_id and selected_cat_id != 0 and item['category_id'] != selected_cat_id:
                continue
            if cond_mode != "All Conditions" and item['condition'] != cond_mode:
                continue
            if dept_mode != "All Departments" and dept_mode.lower() not in item['department'].lower():
                continue
            if avail_mode == "Available Only" and item['status'] != "Available":
                continue
            elif avail_mode == "Rented / Reserved" and item['status'] == "Available":
                continue

            self.filtered_listings.append(item)

        self.relayout_grid()

    def relayout_grid(self):
        # Clear grid
        for i in reversed(range(self.grid_layout.count())):
            w = self.grid_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        if not self.filtered_listings:
            lbl_empty = QLabel("No marketplace items match your search filter criteria.")
            lbl_empty.setStyleSheet("font-size: 14px; font-style: italic; color: #94A3B8;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(lbl_empty, 0, 0)
            return

        # Calculate dynamic columns based on window width
        width = self.scroll.width()
        if width >= 1250:
            cols = 4
        elif width >= 900:
            cols = 3
        else:
            cols = 2

        for idx, item in enumerate(self.filtered_listings):
            card = MarketplaceCard(item, self.active_user_id)
            card.quick_view_requested.connect(self.show_quick_view)
            card.rent_requested.connect(self.show_rent_request)
            card.wishlist_toggled.connect(self.handle_wishlist)
            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    def show_quick_view(self, listing):
        dlg = QuickViewDialog(listing, self)
        dlg.exec()

    def show_rent_request(self, listing):
        dlg = RentRequestDialog(listing, self.active_user_id, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_listings()

    def handle_wishlist(self, listing):
        res = controllers.save_listing(self.active_user_id, listing['listing_id'])
        if res == 1:
            QMessageBox.information(self, "Saved", f"'{listing['title']}' saved to your wishlist!")
        else:
            QMessageBox.information(self, "Saved", f"'{listing['title']}' is already in your wishlist.")
