from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from .theme import CampusLinkTheme
import controllers

class MetricCard(QFrame):
    def __init__(self, title, value, subtext, accent_color, parent=None):
        super().__init__(parent)
        self.setObjectName("MetricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 12px; font-weight: bold; color: #94A3B8;")

        lbl_v = QLabel(str(value))
        lbl_v.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {accent_color};")

        lbl_sub = QLabel(subtext)
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748B;")

        layout.addWidget(lbl_t)
        layout.addWidget(lbl_v)
        layout.addWidget(lbl_sub)

class DashboardView(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_user_id = None
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(20)

        # Header Title
        lbl_head = QLabel("Dashboard Overview")
        lbl_head.setObjectName("HeaderTitle")
        self.main_layout.addWidget(lbl_head)

        # Metrics Row
        self.metrics_layout = QHBoxLayout()
        self.metrics_layout.setSpacing(15)

        self.card_listings = MetricCard("Active Listings", "0", "Items posted by you", "#38BDF8")
        self.card_borrowed = MetricCard("Active Borrowed", "0", "Items currently rented", "#818CF8")
        self.card_earnings = MetricCard("Net Earnings", "GH₵ 0.00", "Owner net payout (90%)", "#10B981")
        self.card_trust = MetricCard("Trust Score", "90/100", "Reputation rating", "#F59E0B")

        self.metrics_layout.addWidget(self.card_listings)
        self.metrics_layout.addWidget(self.card_borrowed)
        self.metrics_layout.addWidget(self.card_earnings)
        self.metrics_layout.addWidget(self.card_trust)
        self.main_layout.addLayout(self.metrics_layout)

        # Quick Actions Row
        qa_frame = QFrame()
        qa_frame.setObjectName("CardFrame")
        qa_layout = QHBoxLayout(qa_frame)
        qa_layout.setContentsMargins(15, 12, 15, 12)

        lbl_qa = QLabel("Quick Actions:")
        lbl_qa.setStyleSheet("font-weight: bold; font-size: 13px;")

        btn_mkt = QPushButton("🔍 Browse Marketplace")
        btn_mkt.clicked.connect(lambda: self.navigate_requested.emit("Marketplace"))

        btn_post = QPushButton("➕ Post New Listing")
        btn_post.clicked.connect(lambda: self.navigate_requested.emit("My Listings"))

        btn_rep = QPushButton("📊 Intelligence Reports")
        btn_rep.setObjectName("SecondaryButton")
        btn_rep.clicked.connect(lambda: self.navigate_requested.emit("Reports"))

        qa_layout.addWidget(lbl_qa)
        qa_layout.addWidget(btn_mkt)
        qa_layout.addWidget(btn_post)
        qa_layout.addWidget(btn_rep)
        qa_layout.addStretch()

        self.main_layout.addWidget(qa_frame)

        # Recent Activity Table
        lbl_table_title = QLabel("Recent Rental Transactions")
        lbl_table_title.setObjectName("SectionTitle")
        self.main_layout.addWidget(lbl_table_title)

        self.tbl_activity = QTableWidget()
        self.tbl_activity.setColumnCount(6)
        self.tbl_activity.setHorizontalHeaderLabels([
            "TX ID", "Item Title", "Borrower / Lender", "Duration", "Amount", "Status"
        ])
        self.tbl_activity.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_activity.setAlternatingRowColors(True)

        self.main_layout.addWidget(self.tbl_activity)

    def refresh_data(self, user_id=None):
        self.refresh(user_id or self.active_user_id)

    def refresh(self, user_id):
        self.active_user_id = user_id
        if not user_id:
            return

        # Fetch trust score
        trust = controllers.calculate_trust_score(user_id)
        if isinstance(trust, dict):
            score = trust.get("score", 90)
            self.card_trust.layout().itemAt(1).widget().setText(f"{score}/100")

        # Fetch listings count
        my_listings = controllers.get_filtered_listings(owner_id=user_id)
        count_listings = len(my_listings) if my_listings else 0
        self.card_listings.layout().itemAt(1).widget().setText(str(count_listings))

        # Fetch recent transactions
        report_data = controllers.get_intelligence_report(1) # Platform summary
        if report_data and "data" in report_data:
            rows = report_data["data"][:8]
            self.tbl_activity.setRowCount(len(rows))
            for i, r in enumerate(rows):
                for j in range(min(6, len(r))):
                    item = QTableWidgetItem(str(r[j]))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if j in [0, 3, 4, 5] else Qt.AlignmentFlag.AlignLeft)
                    self.tbl_activity.setItem(i, j, item)

