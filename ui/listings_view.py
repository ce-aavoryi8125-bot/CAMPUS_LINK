from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QTextEdit, QSpinBox, QDoubleSpinBox, QMessageBox,
    QFileDialog
)
from PySide6.QtCore import Qt, Signal
import controllers
import os
from datetime import datetime, timedelta

class AddListingDialog(QDialog):
    def __init__(self, owner_id, parent=None):
        super().__init__(parent)
        self.owner_id = owner_id
        self.selected_img_path = ""
        self.setWindowTitle("Post New Resource Listing")
        self.resize(500, 560)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)

        lbl_t = QLabel("Create Resource Listing")
        lbl_t.setStyleSheet("font-size: 18px; font-weight: bold; color: #4A5DDE;")
        layout.addWidget(lbl_t)

        self.cmb_cat = QComboBox()
        cats = controllers.get_categories()
        if cats:
            for c in cats:
                self.cmb_cat.addItem(c[1], c[0])
        layout.addWidget(QLabel("Category:"))
        layout.addWidget(self.cmb_cat)

        self.ent_title = QLineEdit()
        self.ent_title.setPlaceholderText("e.g. Leica Total Station TS07")
        layout.addWidget(QLabel("Item Title:"))
        layout.addWidget(self.ent_title)

        self.ent_subcat = QLineEdit()
        self.ent_subcat.setPlaceholderText("e.g. Total Station")
        layout.addWidget(QLabel("Subcategory:"))
        layout.addWidget(self.ent_subcat)

        self.ent_brand = QLineEdit()
        self.ent_brand.setPlaceholderText("e.g. Leica")
        layout.addWidget(QLabel("Brand:"))
        layout.addWidget(self.ent_brand)

        self.ent_model = QLineEdit()
        self.ent_model.setPlaceholderText("e.g. FlexLine TS07")
        layout.addWidget(QLabel("Model:"))
        layout.addWidget(self.ent_model)

        rates_layout = QHBoxLayout()
        self.spn_rate = QDoubleSpinBox()
        self.spn_rate.setRange(1.0, 1000.0)
        self.spn_rate.setValue(25.0)

        self.spn_dep = QDoubleSpinBox()
        self.spn_dep.setRange(5.0, 2000.0)
        self.spn_dep.setValue(100.0)

        rates_layout.addWidget(QLabel("Daily Rate (GH₵):"))
        rates_layout.addWidget(self.spn_rate)
        rates_layout.addWidget(QLabel("Deposit (GH₵):"))
        rates_layout.addWidget(self.spn_dep)
        layout.addLayout(rates_layout)

        self.cmb_cond = QComboBox()
        self.cmb_cond.addItems(["New", "Good", "Fair"])
        layout.addWidget(QLabel("Item Condition:"))
        layout.addWidget(self.cmb_cond)

        self.ent_loc = QLineEdit()
        self.ent_loc.setPlaceholderText("e.g. Chamber of Mines Hostel Room 12B")
        layout.addWidget(QLabel("Pickup Location:"))
        layout.addWidget(self.ent_loc)

        self.txt_desc = QTextEdit()
        self.txt_desc.setPlaceholderText("Provide details, accessories included, and usage instructions...")
        layout.addWidget(QLabel("Description:"))
        layout.addWidget(self.txt_desc)

        # Image picker
        img_row = QHBoxLayout()
        self.lbl_img_status = QLabel("No image selected")
        self.lbl_img_status.setStyleSheet("font-size: 11px; color: #94A3B8;")
        btn_pick_img = QPushButton("🖼 Upload Image")
        btn_pick_img.setObjectName("SecondaryButton")
        btn_pick_img.clicked.connect(self.pick_image)

        img_row.addWidget(self.lbl_img_status)
        img_row.addWidget(btn_pick_img)
        layout.addLayout(img_row)

        btn_box = QHBoxLayout()
        btn_sub = QPushButton("Publish Listing")
        btn_sub.clicked.connect(self.handle_publish)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("SecondaryButton")
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_sub)
        layout.addLayout(btn_box)

    def pick_image(self):
        filePath, _ = QFileDialog.getOpenFileName(self, "Select Product Image", "", "Images (*.png *.jpg *.jpeg)")
        if filePath:
            self.selected_img_path = filePath
            self.lbl_img_status.setText(os.path.basename(filePath))

    def handle_publish(self):
        title = self.ent_title.text().strip()
        subcat = self.ent_subcat.text().strip()
        brand = self.ent_brand.text().strip()
        model = self.ent_model.text().strip()
        cat_id = self.cmb_cat.currentData()
        rate = self.spn_rate.value()
        deposit = self.spn_dep.value()
        cond = self.cmb_cond.currentText()
        loc = self.ent_loc.text().strip()
        desc = self.txt_desc.toPlainText().strip()

        if not title or not subcat or not brand or not model or not loc:
            QMessageBox.warning(self, "Validation Error", "Please fill in all required fields.")
            return

        today = datetime.now().date()
        s_date = today.strftime("%Y-%m-%d")
        e_date = (today + timedelta(days=90)).strftime("%Y-%m-%d")

        res = controllers.create_listing(
            self.owner_id, cat_id, title, desc, subcat, brand, model,
            2023, rate, deposit, cond, loc, s_date, e_date
        )

        if res == -1:
            QMessageBox.critical(self, "Error", "Failed to create listing.")
        else:
            QMessageBox.information(self, "Success", f"Listing '{title}' published successfully!")
            self.accept()

class MyListingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_user_id = None
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)

        # Header Row
        head_row = QHBoxLayout()
        lbl_head = QLabel("My Posted Listings & Requests")
        lbl_head.setObjectName("HeaderTitle")

        btn_add = QPushButton("➕ Post New Listing")
        btn_add.clicked.connect(self.show_add_modal)

        head_row.addWidget(lbl_head)
        head_row.addStretch()
        head_row.addWidget(btn_add)
        main_layout.addLayout(head_row)

        # Listings Table
        lbl_l = QLabel("Your Active Listings:")
        lbl_l.setObjectName("SectionTitle")
        main_layout.addWidget(lbl_l)

        self.tbl_listings = QTableWidget()
        self.tbl_listings.setColumnCount(7)
        self.tbl_listings.setHorizontalHeaderLabels([
            "ID", "Title", "Category", "Daily Rate", "Deposit", "Status", "Pickup Location"
        ])
        self.tbl_listings.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_listings.setAlternatingRowColors(True)
        main_layout.addWidget(self.tbl_listings)

        # Incoming Requests Table
        lbl_r = QLabel("Incoming Rental Requests on Your Items:")
        lbl_r.setObjectName("SectionTitle")
        main_layout.addWidget(lbl_r)

        self.tbl_requests = QTableWidget()
        self.tbl_requests.setColumnCount(7)
        self.tbl_requests.setHorizontalHeaderLabels([
            "Req ID", "Item Title", "Borrower Name", "Start Date", "End Date", "Status", "Action"
        ])
        self.tbl_requests.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_requests.setAlternatingRowColors(True)
        main_layout.addWidget(self.tbl_requests)

    def refresh_data(self, user_id=None):
        self.refresh(user_id or self.active_user_id)

    def refresh(self, user_id):
        self.active_user_id = user_id
        self.tbl_listings.setRowCount(0)
        self.tbl_requests.setRowCount(0)
        if not user_id:
            return

        # Load listings
        my_listings = controllers.get_filtered_listings(owner_id=user_id)
        if my_listings:
            self.tbl_listings.setRowCount(len(my_listings))
            for i, r in enumerate(my_listings):
                self.tbl_listings.setItem(i, 0, QTableWidgetItem(str(r[0])))
                self.tbl_listings.setItem(i, 1, QTableWidgetItem(str(r[1])))
                self.tbl_listings.setItem(i, 2, QTableWidgetItem(str(r[12])))
                self.tbl_listings.setItem(i, 3, QTableWidgetItem(f"GH₵ {float(r[6]):.2f}"))
                self.tbl_listings.setItem(i, 4, QTableWidgetItem(f"GH₵ {float(r[7]):.2f}"))
                self.tbl_listings.setItem(i, 5, QTableWidgetItem(str(r[9])))
                self.tbl_listings.setItem(i, 6, QTableWidgetItem(str(r[10])))

        # Load incoming requests
        reqs = controllers.get_incoming_requests(user_id)
        if reqs:
            self.tbl_requests.setRowCount(len(reqs))
            for i, rq in enumerate(reqs):
                # get_incoming_requests returns:
                # (request_id, title, borrower_name, start_date, end_date, purpose, status, notes, listing_id, borrower_id)
                req_id = rq[0]
                item_title = rq[1]
                borrower_name = rq[2]
                start_date = rq[3]
                end_date = rq[4]
                status = rq[6]   # index 6 = status (was wrongly rq[7] = notes)

                self.tbl_requests.setItem(i, 0, QTableWidgetItem(str(req_id)))
                self.tbl_requests.setItem(i, 1, QTableWidgetItem(str(item_title)))
                self.tbl_requests.setItem(i, 2, QTableWidgetItem(str(borrower_name)))
                self.tbl_requests.setItem(i, 3, QTableWidgetItem(str(start_date)))
                self.tbl_requests.setItem(i, 4, QTableWidgetItem(str(end_date)))
                self.tbl_requests.setItem(i, 5, QTableWidgetItem(str(status)))

                if status == "Pending":
                    btn_approve = QPushButton("✅ Approve")
                    btn_approve.setStyleSheet("background-color: #10B981; font-size: 11px; padding: 4px; color: white; border-radius: 4px;")
                    btn_approve.clicked.connect(lambda _, r_id=req_id: self.approve_req(r_id))
                    self.tbl_requests.setCellWidget(i, 6, btn_approve)
                else:
                    self.tbl_requests.setItem(i, 6, QTableWidgetItem(status))

    def approve_req(self, req_id):
        res = controllers.approve_rental_request(req_id)
        if res == 1:
            QMessageBox.information(self, "Approved", "Rental request approved! Transaction created and listing status updated to Reserved.")
            self.refresh(self.active_user_id)
        else:
            QMessageBox.critical(self, "Error", "Failed to approve request.")

    def show_add_modal(self):
        dlg = AddListingDialog(self.active_user_id, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh(self.active_user_id)
