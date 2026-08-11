from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt
import controllers

class AdminView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_user_id = None
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)

        lbl_head = QLabel("Administrator System Management")
        lbl_head.setObjectName("HeaderTitle")
        main_layout.addWidget(lbl_head)

        lbl_sub = QLabel("Manage UMaT user accounts, update verification levels, and control access permissions.")
        lbl_sub.setObjectName("SubtitleLabel")
        main_layout.addWidget(lbl_sub)

        self.tbl_users = QTableWidget()
        self.tbl_users.setColumnCount(8)
        self.tbl_users.setHorizontalHeaderLabels([
            "User ID", "Name", "Institutional Email", "Student ID", "Verification Level", "Status", "Department", "Action"
        ])
        self.tbl_users.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_users.setAlternatingRowColors(True)
        main_layout.addWidget(self.tbl_users)

    def refresh_data(self, user_id=None):
        self.refresh(user_id or self.active_user_id)

    def refresh(self, user_id):
        self.active_user_id = user_id
        self.tbl_users.setRowCount(0)
        users = controllers.get_all_users()
        if users:
            self.tbl_users.setRowCount(len(users))
            for i, u in enumerate(users):
                # user_id, name, email, student_id, phone, verification_level, department, hostel, account_status
                uid = u[0]
                name = u[1]
                email = u[2]
                sid = u[3] if u[3] else "Staff/N/A"
                v_level = u[5]
                dept = u[6]
                status = u[8] if len(u) > 8 else "Active"

                self.tbl_users.setItem(i, 0, QTableWidgetItem(str(uid)))
                self.tbl_users.setItem(i, 1, QTableWidgetItem(str(name)))
                self.tbl_users.setItem(i, 2, QTableWidgetItem(str(email)))
                self.tbl_users.setItem(i, 3, QTableWidgetItem(str(sid)))
                self.tbl_users.setItem(i, 4, QTableWidgetItem(str(v_level)))
                self.tbl_users.setItem(i, 5, QTableWidgetItem(str(status)))
                self.tbl_users.setItem(i, 6, QTableWidgetItem(str(dept)))

                # Action Column Logic: Show Button ONLY for Unverified users; Show Badges for Verified/Admin users
                if v_level == "Unverified":
                    btn_verify = QPushButton("🟢 Verify Student")
                    btn_verify.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_verify.setStyleSheet("""
                        QPushButton {
                            background-color: #10B981;
                            color: #FFFFFF;
                            font-weight: bold;
                            font-size: 11px;
                            padding: 6px 12px;
                            border-radius: 4px;
                            border: none;
                        }
                        QPushButton:hover {
                            background-color: #059669;
                        }
                    """)
                    btn_verify.clicked.connect(lambda _, u_id=uid, u_name=name, u_email=email: self.confirm_and_upgrade(u_id, u_name, u_email))
                    self.tbl_users.setCellWidget(i, 7, btn_verify)
                elif v_level == "Verified Student":
                    lbl_badge = QLabel("✔ Verified Student")
                    lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lbl_badge.setStyleSheet("""
                        background-color: rgba(16, 185, 129, 0.15);
                        color: #10B981;
                        font-size: 11px;
                        font-weight: bold;
                        border: 1px solid #10B981;
                        border-radius: 4px;
                        padding: 4px 8px;
                    """)
                    self.tbl_users.setCellWidget(i, 7, lbl_badge)
                elif v_level == "Verified Staff":
                    lbl_badge = QLabel("🛡 Verified Staff")
                    lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lbl_badge.setStyleSheet("""
                        background-color: rgba(14, 165, 233, 0.15);
                        color: #0EA5E9;
                        font-size: 11px;
                        font-weight: bold;
                        border: 1px solid #0EA5E9;
                        border-radius: 4px;
                        padding: 4px 8px;
                    """)
                    self.tbl_users.setCellWidget(i, 7, lbl_badge)
                elif v_level == "Admin":
                    lbl_badge = QLabel("👑 Admin")
                    lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lbl_badge.setStyleSheet("""
                        background-color: rgba(245, 158, 11, 0.15);
                        color: #F59E0B;
                        font-size: 11px;
                        font-weight: bold;
                        border: 1px solid #F59E0B;
                        border-radius: 4px;
                        padding: 4px 8px;
                    """)
                    self.tbl_users.setCellWidget(i, 7, lbl_badge)
                else:
                    lbl_badge = QLabel("✔ Verified")
                    lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lbl_badge.setStyleSheet("""
                        background-color: rgba(100, 116, 139, 0.15);
                        color: #94A3B8;
                        font-size: 11px;
                        font-weight: bold;
                        border: 1px solid #64748B;
                        border-radius: 4px;
                        padding: 4px 8px;
                    """)
                    self.tbl_users.setCellWidget(i, 7, lbl_badge)

    def confirm_and_upgrade(self, target_user_id, user_name, user_email):
        reply = QMessageBox.question(
            self,
            "Confirm Verification",
            f"Are you sure you want to verify user '{user_name}' ({user_email}) as a Verified Student?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.upgrade_user(target_user_id, "Verified Student")

    def upgrade_user(self, target_user_id, level):
        res = controllers.update_user_verification(target_user_id, level)
        if res == 1:
            QMessageBox.information(self, "Verification Successful", f"User verification status successfully updated to '{level}'.")
            self.refresh(self.active_user_id)
        else:
            QMessageBox.critical(self, "Error", "Failed to update user verification level in database.")
