import os
from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QProgressBar, QComboBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QFont
from .assets_manager import get_logo_path
from .theme import CampusLinkTheme
import controllers

class SplashScreen(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.resize(520, 360)

        # Center on screen
        if self.screen():
            geo = self.screen().geometry()
            self.move((geo.width() - 520) // 2, (geo.height() - 360) // 2)

        self.setStyleSheet("""
            QDialog {
                background-color: #0A192F;
                border: 2px solid #38BDF8;
                border-radius: 16px;
            }
            QLabel {
                color: #FFFFFF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo
        logo_path = get_logo_path()
        if logo_path:
            pixmap = QPixmap(logo_path).scaled(90, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_logo = QLabel()
            lbl_logo.setPixmap(pixmap)
            lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl_logo)

        # Title & Tagline
        lbl_title = QLabel("CampusLink")
        lbl_title.setStyleSheet("font-size: 28px; font-weight: bold; color: #FFFFFF;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_tagline = QLabel("Rent. Borrow. Lend. Earn.")
        lbl_tagline.setStyleSheet("font-size: 13px; font-weight: bold; color: #D97706;")
        lbl_tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_tagline)

        lbl_umat = QLabel("University of Mines and Technology (UMaT)")
        lbl_umat.setStyleSheet("font-size: 11px; color: #94A3B8;")
        lbl_umat.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_umat)

        layout.addSpacing(15)

        lbl_load = QLabel("Initializing database & security services...")
        lbl_load.setStyleSheet("font-size: 11px; font-style: italic; color: #CBD5E1;")
        lbl_load.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_load)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0) # Indeterminate
        self.progress.setFixedWidth(320)
        self.progress.setFixedHeight(8)
        layout.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignCenter)

        # Auto close timer
        QTimer.singleShot(2500, self.accept)

class LoginView(QWidget):
    login_success = Signal(dict)
    switch_to_register = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Centered Card Frame
        card = QFrame()
        card.setObjectName("CardFrame")
        card.setFixedWidth(460)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(35, 30, 35, 30)

        # Logo
        logo_path = get_logo_path()
        if logo_path:
            pixmap = QPixmap(logo_path).scaled(75, 75, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_logo = QLabel()
            lbl_logo.setPixmap(pixmap)
            lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(lbl_logo)

        # Header Titles
        lbl_title = QLabel("CampusLink")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #4A5DDE;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(lbl_title)

        lbl_tagline = QLabel("Rent. Borrow. Lend. Earn.")
        lbl_tagline.setStyleSheet("font-size: 11px; font-weight: bold; color: #D97706;")
        lbl_tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(lbl_tagline)

        lbl_umat = QLabel("University of Mines and Technology (UMaT)")
        lbl_umat.setStyleSheet("font-size: 10px; color: #64748B;")
        lbl_umat.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(lbl_umat)

        lbl_dept = QLabel("Department of Computer Science & Engineering")
        lbl_dept.setStyleSheet("font-size: 10px; font-weight: bold; color: #4A5DDE;")
        lbl_dept.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(lbl_dept)

        card_layout.addSpacing(15)

        # Email Field
        lbl_e = QLabel("Institutional / Personal Email:")
        lbl_e.setStyleSheet("font-weight: bold;")
        card_layout.addWidget(lbl_e)
        self.ent_email = QLineEdit()
        self.ent_email.setPlaceholderText("e.g. ce-aavoryi8125@st.umat.edu.gh")
        self.ent_email.setText("ce-aavoryi8125@st.umat.edu.gh")
        card_layout.addWidget(self.ent_email)

        # Password Field
        lbl_p = QLabel("Password:")
        lbl_p.setStyleSheet("font-weight: bold;")
        card_layout.addWidget(lbl_p)
        self.ent_password = QLineEdit()
        self.ent_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.ent_password.setText("Student123")
        card_layout.addWidget(self.ent_password)

        # Forgot Password Link
        lbl_forgot = QLabel("<a href='#'>Forgot Password?</a>")
        lbl_forgot.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_forgot.setCursor(Qt.CursorShape.PointingHandCursor)
        lbl_forgot.linkActivated.connect(self.handle_forgot_password)
        card_layout.addWidget(lbl_forgot)

        card_layout.addSpacing(10)

        # Sign In Button
        btn_login = QPushButton("Sign In to CampusLink")
        btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_login.clicked.connect(self.handle_login)
        card_layout.addWidget(btn_login)

        card_layout.addSpacing(15)

        # Quick Presets Box
        preset_frame = QFrame()
        preset_frame.setStyleSheet("background-color: rgba(241, 245, 249, 0.1); border: 1px solid #334155; border-radius: 8px; padding: 8px;")
        p_layout = QVBoxLayout(preset_frame)
        lbl_p_title = QLabel("Quick Demo Credentials:")
        lbl_p_title.setStyleSheet("font-size: 11px; font-weight: bold;")
        p_layout.addWidget(lbl_p_title)

        p_buttons = QHBoxLayout()
        btn_albert = QPushButton("Albert (Student)")
        btn_albert.setObjectName("SecondaryButton")
        btn_albert.clicked.connect(lambda: self.set_preset("ce-aavoryi8125@st.umat.edu.gh", "Student123"))

        btn_benedict = QPushButton("Benedict (Student)")
        btn_benedict.setObjectName("SecondaryButton")
        btn_benedict.clicked.connect(lambda: self.set_preset("benedict@st.umat.edu.gh", "Student123"))

        btn_admin = QPushButton("Admin")
        btn_admin.setObjectName("SecondaryButton")
        btn_admin.clicked.connect(lambda: self.set_preset("admin@umat.edu.gh", "Admin123"))

        p_buttons.addWidget(btn_albert)
        p_buttons.addWidget(btn_benedict)
        p_buttons.addWidget(btn_admin)
        p_layout.addLayout(p_buttons)
        card_layout.addWidget(preset_frame)

        # Register Link Footer
        footer = QHBoxLayout()
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_no_acct = QLabel("Don't have an account?")
        lbl_no_acct.setStyleSheet("color: #64748B;")
        lbl_reg = QLabel("<a href='#'>Register Now</a>")
        lbl_reg.setCursor(Qt.CursorShape.PointingHandCursor)
        lbl_reg.linkActivated.connect(lambda _: self.switch_to_register.emit())

        footer.addWidget(lbl_no_acct)
        footer.addWidget(lbl_reg)
        card_layout.addLayout(footer)

        main_layout.addWidget(card)

        # Keypress triggers login
        self.ent_password.returnPressed.connect(self.handle_login)

    def set_preset(self, email, passw):
        self.ent_email.setText(email)
        self.ent_password.setText(passw)

    def handle_forgot_password(self, _=None):
        QMessageBox.information(
            self,
            "Password Reset Assistance",
            "Forgot your password?\n\nPlease contact the CampusLink Administrator (admin@umat.edu.gh) or the UMaT ICT Directorate to verify your identity and reset your credentials."
        )

    def handle_login(self):
        email = self.ent_email.text().strip()
        password = self.ent_password.text().strip()

        if not email or not password:
            QMessageBox.warning(self, "Login Error", "Please enter both Email and Password.")
            return

        res = controllers.authenticate_user(email, password)
        if res == -1:
            QMessageBox.critical(self, "Access Denied", "Invalid Email or Password. Please try again.")
        elif res == -2:
            QMessageBox.critical(self, "Account Suspended", "Your account has been suspended by an Administrator.")
        elif isinstance(res, dict):
            self.login_success.emit(res)

class RegisterView(QWidget):
    switch_to_login = Signal()
    register_success = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("CardFrame")
        card.setFixedWidth(540)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(35, 25, 35, 25)

        lbl_title = QLabel("Create Your CampusLink Account")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #4A5DDE;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(lbl_title)

        # Form Fields
        self.ent_name = QLineEdit()
        self.ent_name.setPlaceholderText("e.g. Kwame Boateng")
        card_layout.addWidget(QLabel("Full Name:"))
        card_layout.addWidget(self.ent_name)

        self.ent_email = QLineEdit()
        self.ent_email.setPlaceholderText("e.g. ce-aavoryi8125@st.umat.edu.gh")
        card_layout.addWidget(QLabel("Email Address:"))
        card_layout.addWidget(self.ent_email)

        self.ent_pass = QLineEdit()
        self.ent_pass.setEchoMode(QLineEdit.EchoMode.Password)
        card_layout.addWidget(QLabel("Password:"))
        card_layout.addWidget(self.ent_pass)

        self.ent_confirm = QLineEdit()
        self.ent_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        card_layout.addWidget(QLabel("Confirm Password:"))
        card_layout.addWidget(self.ent_confirm)

        self.ent_id = QLineEdit()
        self.ent_id.setPlaceholderText("e.g. FCM.41.008.043.25")
        card_layout.addWidget(QLabel("Index / Staff ID:"))
        card_layout.addWidget(self.ent_id)

        self.ent_phone = QLineEdit()
        self.ent_phone.setPlaceholderText("e.g. +233240001122")
        card_layout.addWidget(QLabel("Phone Number:"))
        card_layout.addWidget(self.ent_phone)

        self.cmb_dept = QComboBox()
        self.cmb_dept.addItems([
            "Geomatic Engineering", "Mining Engineering", "Petroleum Engineering",
            "Electrical & Electronic Engineering", "Geological Engineering",
            "Computer Science & Engineering", "Mechanical Engineering",
            "Environmental & Safety Engineering", "Mathematical Sciences"
        ])
        card_layout.addWidget(QLabel("Department:"))
        card_layout.addWidget(self.cmb_dept)

        self.ent_hostel = QLineEdit()
        self.ent_hostel.setPlaceholderText("e.g. Chamber of Mines Hall")
        card_layout.addWidget(QLabel("Hostel / Residence (Optional):"))
        card_layout.addWidget(self.ent_hostel)

        card_layout.addSpacing(15)

        # Buttons
        btn_reg = QPushButton("Create Account")
        btn_reg.clicked.connect(self.handle_register)
        card_layout.addWidget(btn_reg)

        btn_back = QPushButton("Back to Login")
        btn_back.setObjectName("SecondaryButton")
        btn_back.clicked.connect(lambda: self.switch_to_login.emit())
        card_layout.addWidget(btn_back)

        main_layout.addWidget(card)

    def handle_register(self):
        name = self.ent_name.text().strip()
        email = self.ent_email.text().strip()
        password = self.ent_pass.text().strip()
        confirm = self.ent_confirm.text().strip()
        student_id = self.ent_id.text().strip()
        phone = self.ent_phone.text().strip()
        dept = self.cmb_dept.currentText()
        hostel = self.ent_hostel.text().strip()

        if not name or not email or not password or not phone or not dept:
            QMessageBox.warning(self, "Validation Error", "Please fill in all required fields.")
            return

        if password != confirm:
            QMessageBox.warning(self, "Validation Error", "Passwords do not match. Please check and try again.")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters long.")
            return

        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid email address.")
            return

        res = controllers.register_user(name, email, password, student_id, phone, dept, hostel)
        if res == -1:
            QMessageBox.critical(self, "Registration Error", "Registration failed. Email or Student ID may already be registered.")
        else:
            QMessageBox.information(self, "Registration Successful", "Registration successful! You may now sign in to CampusLink.")
            self.register_success.emit()
