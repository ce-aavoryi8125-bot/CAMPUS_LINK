from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QTextEdit, QSpinBox, QDoubleSpinBox, QMessageBox,
    QComboBox
)
from PySide6.QtCore import Qt, Signal, QDate
import controllers
from datetime import datetime

class ReturnInspectionDialog(QDialog):
    def __init__(self, tx_data, parent=None):
        super().__init__(parent)
        self.tx = tx_data
        self.setWindowTitle(f"Return Inspection - {tx_data.get('title')}")
        self.resize(460, 420)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)

        lbl_t = QLabel(f"Process Item Return: {self.tx.get('title')}")
        lbl_t.setStyleSheet("font-size: 18px; font-weight: bold; color: #4A5DDE;")
        layout.addWidget(lbl_t)

        layout.addWidget(QLabel("Return Condition / Inspection Result:"))
        self.cmb_cond = QComboBox()
        self.cmb_cond.addItems(["Good / Intact", "Minor Damage (Claim Deposit)", "Severe Damage"])
        layout.addWidget(self.cmb_cond)

        layout.addWidget(QLabel("Damage Repair Cost / Deduction (GH₵ 0.00 if intact):"))
        self.spn_cost = QDoubleSpinBox()
        self.spn_cost.setRange(0.0, 1000.0)
        self.spn_cost.setValue(0.0)
        layout.addWidget(self.spn_cost)

        layout.addWidget(QLabel("Return Inspection Notes:"))
        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Describe return state, cleanliness, and any minor wear...")
        layout.addWidget(self.txt_notes)

        btn_box = QHBoxLayout()
        btn_sub = QPushButton("Confirm Return")
        btn_sub.clicked.connect(self.handle_return)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("SecondaryButton")
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_sub)
        layout.addLayout(btn_box)

    def handle_return(self):
        cond_text = self.cmb_cond.currentText()
        is_damaged = "Damage" in cond_text
        cost = self.spn_cost.value() if is_damaged else 0.0
        notes = self.txt_notes.toPlainText().strip()
        ret_date = datetime.now().date().strftime("%Y-%m-%d")

        res = controllers.process_item_return(
            self.tx['transaction_id'], ret_date, is_damaged, cost,
            f"Returned - {cond_text}. {notes}"
        )

        if res == 1:
            QMessageBox.information(self, "Return Confirmed", "Item return processed successfully! Listing status updated.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to process item return.")

class ReviewDialog(QDialog):
    def __init__(self, tx_id, reviewer_id, reviewee_id, reviewee_name, reviewee_role, parent=None):
        super().__init__(parent)
        self.tx_id = tx_id
        self.reviewer_id = reviewer_id
        self.reviewee_id = reviewee_id
        self.reviewee_role = reviewee_role
        self.setWindowTitle(f"Submit Peer Rating for {reviewee_name}")
        self.resize(420, 320)
        self.setup_ui(reviewee_name)

    def setup_ui(self, reviewee_name):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)

        lbl_t = QLabel(f"Rating for {reviewee_name} ({self.reviewee_role})")
        lbl_t.setStyleSheet("font-size: 16px; font-weight: bold; color: #4A5DDE;")
        layout.addWidget(lbl_t)

        layout.addWidget(QLabel("Rating Score (1 to 5 Stars):"))
        self.spn_rating = QSpinBox()
        self.spn_rating.setRange(1, 5)
        self.spn_rating.setValue(5)
        layout.addWidget(self.spn_rating)

        layout.addWidget(QLabel("Feedback Comment:"))
        self.txt_comment = QTextEdit()
        self.txt_comment.setPlaceholderText("Punctuality, equipment care, communication...")
        layout.addWidget(self.txt_comment)

        btn_box = QHBoxLayout()
        btn_sub = QPushButton("Submit Review")
        btn_sub.clicked.connect(self.handle_submit)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("SecondaryButton")
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_sub)
        layout.addLayout(btn_box)

    def handle_submit(self):
        rating = self.spn_rating.value()
        comment = self.txt_comment.toPlainText().strip()

        res = controllers.submit_review(
            self.tx_id, self.reviewer_id, self.reviewee_id,
            self.reviewee_role, rating, comment
        )

        if res == 1:
            QMessageBox.information(self, "Review Submitted", "Thank you! Peer review submitted successfully.")
            self.accept()
        elif res == -2:
            QMessageBox.warning(self, "Duplicate Review", "You have already submitted a review for this transaction.")
        else:
            QMessageBox.critical(self, "Error", "Failed to submit review.")

class MyBorrowedView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_user_id = None
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)

        lbl_head = QLabel("My Borrowed Assets & Active Rentals")
        lbl_head.setObjectName("HeaderTitle")
        main_layout.addWidget(lbl_head)

        self.tbl_borrowed = QTableWidget()
        self.tbl_borrowed.setColumnCount(8)
        self.tbl_borrowed.setHorizontalHeaderLabels([
            "TX ID", "Item Title", "Owner", "Start Date", "End Date", "Total Cost", "Status", "Action"
        ])
        self.tbl_borrowed.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_borrowed.setAlternatingRowColors(True)
        main_layout.addWidget(self.tbl_borrowed)

    def refresh_data(self, user_id=None):
        self.refresh(user_id or self.active_user_id)

    def refresh(self, user_id):
        self.active_user_id = user_id
        self.tbl_borrowed.setRowCount(0)
        if not user_id:
            return

        txs = controllers.get_borrower_transactions(user_id)
        if txs:
            self.tbl_borrowed.setRowCount(len(txs))
            for i, t in enumerate(txs):
                # tx_id, listing_id, title, owner_name, start_date, end_date, gross, status, owner_id
                tx_id = t[0]
                title = t[2]
                owner_name = t[3]
                start_date = t[4]
                end_date = t[5]
                gross = t[6]
                status = t[7]
                owner_id = t[8]

                self.tbl_borrowed.setItem(i, 0, QTableWidgetItem(str(tx_id)))
                self.tbl_borrowed.setItem(i, 1, QTableWidgetItem(str(title)))
                self.tbl_borrowed.setItem(i, 2, QTableWidgetItem(str(owner_name)))
                self.tbl_borrowed.setItem(i, 3, QTableWidgetItem(str(start_date)))
                self.tbl_borrowed.setItem(i, 4, QTableWidgetItem(str(end_date)))
                self.tbl_borrowed.setItem(i, 5, QTableWidgetItem(f"GH₵ {gross:.2f}"))
                self.tbl_borrowed.setItem(i, 6, QTableWidgetItem(str(status)))

                tx_data = {
                    'transaction_id': tx_id,
                    'title': title,
                    'owner_name': owner_name,
                    'owner_id': owner_id
                }

                if status == "Active":
                    btn_ret = QPushButton("🔄 Return Item")
                    btn_ret.setStyleSheet("background-color: #4A5DDE; font-size: 11px; padding: 4px;")
                    btn_ret.clicked.connect(lambda _, d=tx_data: self.show_return_modal(d))
                    self.tbl_borrowed.setCellWidget(i, 7, btn_ret)
                elif status == "Returned":
                    btn_rate = QPushButton("★ Rate Lender")
                    btn_rate.setStyleSheet("background-color: #D97706; font-size: 11px; padding: 4px;")
                    btn_rate.clicked.connect(lambda _, t_id=tx_id, o_id=owner_id, o_name=owner_name: self.show_review_modal(t_id, o_id, o_name))
                    self.tbl_borrowed.setCellWidget(i, 7, btn_rate)
                else:
                    self.tbl_borrowed.setItem(i, 7, QTableWidgetItem(status))

    def show_return_modal(self, tx_data):
        dlg = ReturnInspectionDialog(tx_data, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh(self.active_user_id)

    def show_review_modal(self, tx_id, owner_id, owner_name):
        dlg = ReviewDialog(tx_id, self.active_user_id, owner_id, owner_name, "Lender", self)
        dlg.exec()
