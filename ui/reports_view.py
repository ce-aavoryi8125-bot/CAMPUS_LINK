from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
import controllers
import csv

REPORT_NAMES = [
    "Report 01: Platform Revenue & Commission Summary",
    "Report 02: Top Earning Lenders Breakdown",
    "Report 03: Most Frequent Borrowers",
    "Report 04: Category Rental Utilization & Revenue",
    "Report 05: Active Ongoing Rentals Tracking",
    "Report 06: Completed Rentals History",
    "Report 07: Overdue Rental Inspections Alert",
    "Report 08: Equipment Maintenance & Repair Costs",
    "Report 09: Rental Purpose Distribution",
    "Report 10: Departmental Sharing Activity",
    "Report 11: Top Rated Lenders (Reputation Score)",
    "Report 12: Top Rated Borrowers (Reputation Score)",
    "Report 13: Hostel Resource Sharing Density",
    "Report 14: Monthly Revenue Trend",
    "Report 15: Security Deposit Refund & Deductions Log"
]

class ReportsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_report_id = 1
        self.current_report_data = None
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)

        # Header Row
        head_row = QHBoxLayout()
        lbl_head = QLabel("Campus Intelligence & Analytical Reports")
        lbl_head.setObjectName("HeaderTitle")

        btn_export = QPushButton("📥 Export Report to CSV")
        btn_export.clicked.connect(self.export_csv)

        head_row.addWidget(lbl_head)
        head_row.addStretch()
        head_row.addWidget(btn_export)
        main_layout.addLayout(head_row)

        # Report Selector Bar
        sel_frame = QFrame()
        sel_frame.setObjectName("CardFrame")
        sel_layout = QHBoxLayout(sel_frame)
        sel_layout.setContentsMargins(15, 12, 15, 12)

        lbl_select = QLabel("Select Report:")
        lbl_select.setStyleSheet("font-weight: bold;")

        self.cmb_reports = QComboBox()
        for idx, name in enumerate(REPORT_NAMES, start=1):
            self.cmb_reports.addItem(name, idx)
        self.cmb_reports.currentIndexChanged.connect(self.load_report)

        sel_layout.addWidget(lbl_select)
        sel_layout.addWidget(self.cmb_reports, 1)
        main_layout.addWidget(sel_frame)

        # Summary Metric Cards Row
        self.summary_row = QHBoxLayout()
        self.lbl_metric_1 = QLabel("Report Records: 0")
        self.lbl_metric_1.setStyleSheet("background-color: #1E293B; color: #38BDF8; font-weight: bold; padding: 10px; border-radius: 8px;")
        self.lbl_metric_2 = QLabel("Status: Ready")
        self.lbl_metric_2.setStyleSheet("background-color: #1E293B; color: #10B981; font-weight: bold; padding: 10px; border-radius: 8px;")

        self.summary_row.addWidget(self.lbl_metric_1)
        self.summary_row.addWidget(self.lbl_metric_2)
        self.summary_row.addStretch()
        main_layout.addLayout(self.summary_row)

        # Main Table View
        self.tbl_report = QTableWidget()
        self.tbl_report.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_report.setAlternatingRowColors(True)
        main_layout.addWidget(self.tbl_report)

    def refresh_data(self, _=None):
        self.load_report()

    def refresh(self, _=None):
        self.load_report()

    def load_report(self):
        report_id = self.cmb_reports.currentData()
        if not report_id:
            report_id = 1
        self.current_report_id = report_id

        res = controllers.get_intelligence_report(report_id)
        self.current_report_data = res

        if res and isinstance(res, dict) and "headers" in res and "data" in res:
            headers = res["headers"]
            data = res["data"]

            self.tbl_report.clear()
            self.tbl_report.setColumnCount(len(headers))
            self.tbl_report.setHorizontalHeaderLabels(headers)
            self.tbl_report.setRowCount(len(data))

            for i, row in enumerate(data):
                for j, val in enumerate(row):
                    item = QTableWidgetItem(str(val) if val is not None else "")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if j == 0 else Qt.AlignmentFlag.AlignLeft)
                    self.tbl_report.setItem(i, j, item)

            self.lbl_metric_1.setText(f"Total Rows: {len(data)}")
            self.lbl_metric_2.setText(f"Query Execution: Success")
        else:
            self.tbl_report.clear()
            self.tbl_report.setRowCount(0)
            self.tbl_report.setColumnCount(0)
            self.lbl_metric_1.setText("Total Rows: 0")

    def export_csv(self):
        if not self.current_report_data or "data" not in self.current_report_data or not self.current_report_data["data"]:
            QMessageBox.warning(self, "Export Error", "No data available to export.")
            return

        report_name = REPORT_NAMES[self.current_report_id - 1].split(":")[0].replace(" ", "_")
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Report CSV", f"CampusLink_{report_name}.csv", "CSV Files (*.csv)")

        if filePath:
            try:
                headers = self.current_report_data["headers"]
                data = self.current_report_data["data"]

                with open(filePath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    writer.writerows(data)

                QMessageBox.information(self, "Export Successful", f"Report exported successfully to:\n{filePath}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Could not export CSV file: {e}")
