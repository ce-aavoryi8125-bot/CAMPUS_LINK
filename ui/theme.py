from PySide6.QtWidgets import QCheckBox

class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ThemeToggle")
        self.setFixedSize(60, 28)
        self.setStyleSheet("""
QCheckBox#ThemeToggle {
    spacing: 5px;
}
QCheckBox#ThemeToggle::indicator {
    width: 50px;
    height: 28px;
}
QCheckBox#ThemeToggle::indicator:unchecked {
    image: url('assets/icons/dark_mode.svg');
}
QCheckBox#ThemeToggle::indicator:checked {
    image: url('assets/icons/light_mode.svg');
}
""")
        self.stateChanged.connect(self.update_icon)
        self.update_icon()

    def update_icon(self):
        if self.isChecked():
            self.setText('☀ Light')
        else:
            self.setText('🌙 Dark')

class CampusLinkTheme:
    DARK_MODE = True

    # Color Tokens
    DARK_BG = "#0A192F"
    DARK_CARD = "#1E293B"
    DARK_SIDEBAR = "#070F1E"
    DARK_TEXT_PRIMARY = "#F8FAFC"
    DARK_TEXT_MUTED = "#94A3B8"
    DARK_BORDER = "#334155"

    LIGHT_BG = "#F8FAFC"
    LIGHT_CARD = "#FFFFFF"
    LIGHT_SIDEBAR = "#0A192F"
    LIGHT_TEXT_PRIMARY = "#0F172A"
    LIGHT_TEXT_MUTED = "#64748B"
    LIGHT_BORDER = "#E2E8F0"

    PRIMARY = "#4A5DDE"
    PRIMARY_HOVER = "#3B4CB8"
    GOLD = "#D97706"
    GREEN = "#10B981"
    RED = "#EF4444"

    @classmethod
    def get_stylesheet(cls, dark=True):
        cls.DARK_MODE = dark
        bg = cls.DARK_BG if dark else cls.LIGHT_BG
        card = cls.DARK_CARD if dark else cls.LIGHT_CARD
        text = cls.DARK_TEXT_PRIMARY if dark else cls.LIGHT_TEXT_PRIMARY
        muted = cls.DARK_TEXT_MUTED if dark else cls.LIGHT_TEXT_MUTED
        border = cls.DARK_BORDER if dark else cls.LIGHT_BORDER

        return f"""
QMainWindow, QDialog {{
background-color: {bg};
color: {text};
font-family: 'Segoe UI', Arial, sans-serif;
}}
QWidget {{
color: {text};
font-family: 'Segoe UI', Arial, sans-serif;
}}
QFrame#CardFrame, QFrame#MetricCard {{
background-color: {card};
border: 1px solid {border};
border-radius: 12px;
}}
QLabel {{
color: {text};
background: transparent;
}}
QLabel#MutedLabel {{
color: {muted};
font-size: 11px;
}}
QLabel#HeaderTitle {{
font-size: 20px;
font-weight: bold;
color: {text};
}}
QLabel#SectionTitle {{
font-size: 16px;
font-weight: bold;
color: {text};
}}
QLineEdit#SearchBar {{
height: 36px; border: 2px solid #4F46E5; border-radius: 6px; padding-left: 30px; background-color: {card}; color: {text};
}}
QLineEdit#SearchBar:focus {{
border-color: #6366F1;
}}
QComboBox#FilterCombo {{
min-height: 32px; min-width: 150px; border: 1px solid #374151; border-radius: 4px; background-color: {card}; color: {text};
}}
QComboBox#FilterCombo:hover {{
border-color: #6366F1;
}}
QComboBox#FilterCombo::drop-down {{
subcontrol-origin: padding; subcontrol-position: top right; width: 20px; image: url('assets/icons/down_arrow.svg');
}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
border: 2px solid {cls.PRIMARY};
}}
QPushButton {{
background-color: {cls.PRIMARY};
color: #FFFFFF;
font-weight: bold;
border: none;
border-radius: 6px;
padding: 9px 18px;
font-size: 13px;
}}
QPushButton:hover {{
background-color: {cls.PRIMARY_HOVER};
}}
QPushButton:disabled {{
background-color: {border};
color: {muted};
}}
QPushButton#SecondaryButton {{
background-color: transparent;
color: {text};
border: 1px solid {border};
}}
QPushButton#SecondaryButton:hover {{
background-color: {border};
}}
QPushButton#DangerButton {{
background-color: {cls.RED};
color: #FFFFFF;
}}

QPushButton#PrimaryButton {{
background-color: #10B981; color: #FFFFFF; font-weight: bold; border: none; border-radius: 6px; padding: 9px 18px; font-size: 13px;
}}
QPushButton#PrimaryButton:hover {{
background-color: #059669;
}}
QPushButton#SecondaryButton {{
background-color: transparent; color: #3B82F6; border: 2px solid #3B82F6; border-radius: 6px; padding: 9px 18px; font-size: 13px;
}}
QPushButton#SecondaryButton:hover {{
background-color: rgba(59,130,246,0.1);
}}

QTableWidget, QTreeView {{
background-color: {card};
color: {text};
gridline-color: {border};
border: 1px solid {border};
border-radius: 8px;
alternate-background-color: {"#162032" if dark else "#F1F5F9"};
}}
QHeaderView::section {{
background-color: {"#0F172A" if dark else "#E2E8F0"};
color: {text};
font-weight: bold;
padding: 8px;
border: none;
}}
QScrollBar:vertical {{
border: none;
background: {bg};
width: 8px;
border-radius: 4px;
}}
QScrollBar::handle:vertical {{
background: {border};
border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
background: {cls.PRIMARY};
}}
QProgressBar {{
border: 1px solid {border};
border-radius: 5px;
text-align: center;
background-color: {card};
}}
QProgressBar::chunk {{
background-color: {cls.PRIMARY};
border-radius: 5px;
}}
"""
