from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt
import controllers

class MaintenanceView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_user_id = None
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)

        lbl_head = QLabel("Equipment Maintenance & Repair Tickets Log")
        lbl_head.setObjectName("HeaderTitle")
        main_layout.addWidget(lbl_head)

        lbl_sub = QLabel("Track damage reports, repair tickets, calibration costs, and equipment restoration lifecycle.")
        lbl_sub.setObjectName("SubtitleLabel")
        main_layout.addWidget(lbl_sub)

        self.tbl_maint = QTableWidget()
        self.tbl_maint.setColumnCount(8)
        self.tbl_maint.setHorizontalHeaderLabels([
            "Maint ID", "Listing ID", "Item Title", "Reported By", "Issue Description", "Repair Cost", "Status", "Action"
        ])
        self.tbl_maint.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_maint.setAlternatingRowColors(True)
        main_layout.addWidget(self.tbl_maint)

    def refresh_data(self, user_id=None):
        self.refresh(user_id or self.active_user_id)

    def refresh(self, user_id):
        self.active_user_id = user_id
        self.tbl_maint.setRowCount(0)
        records = controllers.get_all_maintenance_records()
        if records:
            self.tbl_maint.setRowCount(len(records))
            for i, r in enumerate(records):
                # maintenance_id, listing_id, title, reporter_name, issue_description, cost, status
                m_id = r[0]
                l_id = r[1]
                title = r[2]
                reporter = r[3]
                issue = r[4]
                cost = r[5]
                status = r[6]

                self.tbl_maint.setItem(i, 0, QTableWidgetItem(str(m_id)))
                self.tbl_maint.setItem(i, 1, QTableWidgetItem(str(l_id)))
                self.tbl_maint.setItem(i, 2, QTableWidgetItem(str(title)))
                self.tbl_maint.setItem(i, 3, QTableWidgetItem(str(reporter)))
                self.tbl_maint.setItem(i, 4, QTableWidgetItem(str(issue)))
                self.tbl_maint.setItem(i, 5, QTableWidgetItem(f"GH₵ {cost:.2f}"))
                self.tbl_maint.setItem(i, 6, QTableWidgetItem(str(status)))

                if status != "Completed":
                    btn_comp = QPushButton("✓ Mark Completed")
                    btn_comp.setStyleSheet("background-color: #10B981; font-size: 11px; padding: 4px;")
                    btn_comp.clicked.connect(lambda _, mid=m_id, lid=l_id: self.complete_repair(mid, lid))
                    self.tbl_maint.setCellWidget(i, 7, btn_comp)
                else:
                    self.tbl_maint.setItem(i, 7, QTableWidgetItem("Completed"))

    def complete_repair(self, maint_id, listing_id):
        res = controllers.update_maintenance_status(maint_id, "Completed", listing_id)
        if res == 1:
            QMessageBox.information(self, "Completed", "Maintenance ticket marked as Completed! Listing status restored to Available.")
            self.refresh(self.active_user_id)
        else:
            QMessageBox.critical(self, "Error", "Failed to update maintenance status.")
