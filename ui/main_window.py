import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QStatusBar,
    QSpacerItem, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, QTime
from PySide6.QtGui import QPixmap, QIcon

from .assets_manager import get_logo_path
from .theme import CampusLinkTheme, ToggleSwitch
from .auth_views import LoginView, RegisterView
from .dashboard_view import DashboardView
from .marketplace_view import MarketplaceView
from .listings_view import MyListingsView
from .borrowed_view import MyBorrowedView
from .maintenance_view import MaintenanceView
from .reports_view import ReportsView
from .admin_view import AdminView
import controllers

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CampusLink - UMaT Peer-to-Peer Resource Sharing Platform")
        self.resize(1280, 820)
        self.setMinimumSize(1024, 700)

        # Session State
        self.active_user_id = None
        self.active_user_name = ""
        self.active_user_email = ""
        self.active_user_role = ""
        self.active_user_level = ""
        self.is_logged_in = False
        self.dark_mode = True

        self.setup_ui()
        self.apply_theme()
        self.show_login()

    def apply_theme(self):
        self.setStyleSheet(CampusLinkTheme.get_stylesheet(self.dark_mode))

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Header Bar
        self.header = QFrame()
        self.header.setStyleSheet("background-color: #070F1E; border-bottom: 1px solid #1E293B;")
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(15, 10, 15, 10)

        logo_path = get_logo_path()
        if logo_path:
            lbl_logo = QLabel()
            lbl_logo.setPixmap(QPixmap(logo_path).scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            h_layout.addWidget(lbl_logo)

        lbl_brand = QLabel("CampusLink")
        lbl_brand.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        h_layout.addWidget(lbl_brand)

        h_layout.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Header Right Session User Profile Info
        self.lbl_profile = QLabel("")
        self.lbl_profile.setStyleSheet("font-size: 13px; font-weight: bold; color: #F8FAFC;")
        self.lbl_trust = QLabel("")
        self.lbl_trust.setStyleSheet("background-color: #D97706; color: #FFFFFF; font-weight: bold; padding: 3px 8px; border-radius: 4px;")

        self.theme_switch = ToggleSwitch()
        self.theme_switch.setChecked(self.dark_mode)
        self.theme_switch.stateChanged.connect(self.toggle_theme)

        self.btn_logout = QPushButton("🚪 Logout")
        self.btn_logout.setObjectName("SecondaryButton")
        self.btn_logout.clicked.connect(self.handle_logout)

        h_layout.addWidget(self.lbl_profile)
        h_layout.addWidget(self.lbl_trust)
        h_layout.addWidget(self.theme_switch)
        h_layout.addWidget(self.btn_logout)

        root_layout.addWidget(self.header)

        # 2. Main Body (Sidebar + Stacked Viewport)
        body = QWidget()
        b_layout = QHBoxLayout(body)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(0)

        # Sidebar navigation panel
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(220)
        self.sidebar.setStyleSheet("background-color: #070F1E; border-right: 1px solid #1E293B;")
        s_layout = QVBoxLayout(self.sidebar)
        s_layout.setContentsMargins(10, 20, 10, 20)
        s_layout.setSpacing(8)

        self.nav_buttons = {}
        nav_items = [
            ("Dashboard", "📊 Dashboard"),
            ("Marketplace", "🔍 Search Marketplace"),
            ("My Listings", "📦 My Listings & Requests"),
            ("Borrowed", "🤝 Borrowed Items"),
            ("Maintenance", "🔧 Maintenance Tickets"),
            ("Reports", "📈 Intelligence Reports"),
            ("Admin", "⚙️ Admin Control Panel")
        ]

        for key, label in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("SecondaryButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self.navigate_to(k))
            self.nav_buttons[key] = btn
            s_layout.addWidget(btn)

        s_layout.addStretch()

        b_layout.addWidget(self.sidebar)

        # Stacked Viewport
        self.stack = QStackedWidget()

        # Auth Views
        self.view_login = LoginView()
        self.view_login.login_success.connect(self.handle_login_success)
        self.view_login.switch_to_register.connect(self.show_register)
        self.stack.addWidget(self.view_login)

        self.view_register = RegisterView()
        self.view_register.switch_to_login.connect(self.show_login)
        self.view_register.register_success.connect(self.show_login)
        self.stack.addWidget(self.view_register)

        # Main Application Views
        self.view_dashboard = DashboardView()
        self.view_dashboard.navigate_requested.connect(self.navigate_to)
        self.stack.addWidget(self.view_dashboard)

        self.view_marketplace = MarketplaceView()
        self.stack.addWidget(self.view_marketplace)

        self.view_listings = MyListingsView()
        self.stack.addWidget(self.view_listings)

        self.view_borrowed = MyBorrowedView()
        self.stack.addWidget(self.view_borrowed)

        self.view_maintenance = MaintenanceView()
        self.stack.addWidget(self.view_maintenance)

        self.view_reports = ReportsView()
        self.stack.addWidget(self.view_reports)

        self.view_admin = AdminView()
        self.stack.addWidget(self.view_admin)

        b_layout.addWidget(self.stack)
        root_layout.addWidget(body)

        # 3. Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background-color: #070F1E; color: #94A3B8; font-size: 11px;")
        self.setStatusBar(self.status_bar)

        self.lbl_clock = QLabel()
        self.lbl_clock.setStyleSheet("color: #38BDF8; font-weight: bold; margin-right: 15px;")
        self.status_bar.addPermanentWidget(self.lbl_clock)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()

    def update_clock(self):
        now = QTime.currentTime().toString("hh:mm:ss AP")
        self.lbl_clock.setText(f"🕒 UMaT Tarkwa: {now}")

    def show_login(self):
        self.is_logged_in = False
        self.header.hide()
        self.sidebar.hide()
        self.stack.setCurrentWidget(self.view_login)
        self.status_bar.showMessage("Ready. Please sign in to CampusLink.")

    def show_register(self):
        self.header.hide()
        self.sidebar.hide()
        self.stack.setCurrentWidget(self.view_register)
        self.status_bar.showMessage("Account Registration mode.")

    def handle_login_success(self, user_dict):
        self.active_user_id = user_dict["user_id"]
        self.active_user_name = user_dict["name"]
        self.active_user_email = user_dict["email"]
        self.active_user_role = user_dict["role"]
        self.active_user_level = user_dict["verification_level"]
        self.is_logged_in = True

        # Update Header User Info
        self.lbl_profile.setText(f"👤 {self.active_user_name} ({self.active_user_role})")
        trust = controllers.calculate_trust_score(self.active_user_id)
        score = trust.get("score", 90) if isinstance(trust, dict) else 90
        self.lbl_trust.setText(f"⭐ Trust: {score}/100")

        # Admin button visibility
        if self.active_user_role == "Admin":
            self.nav_buttons["Admin"].show()
        else:
            self.nav_buttons["Admin"].hide()

        self.header.show()
        self.sidebar.show()

        # Pass active user id to views
        self.view_marketplace.set_active_user(self.active_user_id)
        self.view_listings.set_active_user(self.active_user_id)
        self.view_borrowed.set_active_user(self.active_user_id)

        self.navigate_to("Dashboard")
        self.status_bar.showMessage(f"Signed in as {self.active_user_name} ({self.active_user_email}).")

    def handle_logout(self):
        reply = QMessageBox.question(
            self,
            "Confirm Logout",
            "Are you sure you want to sign out of CampusLink?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.active_user_id = None
            self.show_login()

    def navigate_to(self, target):
        if not self.is_logged_in:
            return

        # Highlight navigation buttons
        for key, btn in self.nav_buttons.items():
            if key == target:
                btn.setStyleSheet("background-color: #4A5DDE; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 10px 15px;")
            else:
                btn.setStyleSheet("background-color: transparent; color: #94A3B8; border: none; padding: 10px 15px; text-align: left;")

        if target == "Dashboard":
            self.view_dashboard.refresh_data(self.active_user_id)
            self.stack.setCurrentWidget(self.view_dashboard)
        elif target == "Marketplace":
            self.view_marketplace.refresh_data()
            self.stack.setCurrentWidget(self.view_marketplace)
        elif target == "My Listings":
            self.view_listings.refresh_data(self.active_user_id)
            self.stack.setCurrentWidget(self.view_listings)
        elif target == "Borrowed":
            self.view_borrowed.refresh_data(self.active_user_id)
            self.stack.setCurrentWidget(self.view_borrowed)
        elif target == "Maintenance":
            self.view_maintenance.refresh_data()
            self.stack.setCurrentWidget(self.view_maintenance)
        elif target == "Reports":
            self.view_reports.refresh_data()
            self.stack.setCurrentWidget(self.view_reports)
        elif target == "Admin":
            self.view_admin.refresh_data()
            self.stack.setCurrentWidget(self.view_admin)