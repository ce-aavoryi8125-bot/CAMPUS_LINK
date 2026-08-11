import os
from PySide6.QtWidgets import (
QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
QPushButton, QFrame, QStackedWidget, QStatusBar,
QSpacerItem, QSizePolicy
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