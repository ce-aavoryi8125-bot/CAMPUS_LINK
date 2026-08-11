import sys
import os

# Check for PySide6 framework
PYSIDE6_AVAILABLE = False
try:
    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow
    from ui.auth_views import SplashScreen
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False

def run_pyside6_app():
    app = QApplication(sys.argv)
    
    # Show Splash Screen first
    splash = SplashScreen()
    splash.exec()
    
    # Show Main Window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

def main():
    if PYSIDE6_AVAILABLE:
        print("Launching CampusLink PySide6 Modern Interface...")
        run_pyside6_app()
    else:
        print("PySide6 not detected. Falling back to Tkinter interface...")
        # Fallback to Tkinter implementation
        import main_tkinter
        app = main_tkinter.CampusLinkApp()
        app.mainloop()

if __name__ == "__main__":
    main()
