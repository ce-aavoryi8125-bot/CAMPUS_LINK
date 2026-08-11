import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import csv
from datetime import datetime, timedelta
from PIL import Image, ImageTk
import controllers
import db_schema

# Theme Colors (Modern Dark/Light Palette)
BG_MAIN = "#F3F4F6"         # Light Gray Window Background
BG_SIDEBAR = "#0A192F"      # Deep Navy Sidebar Background
COLOR_PRIMARY = "#4A5DDE"   # Slate Blue Accent
COLOR_SECONDARY = "#FFFFFF" # White Card Background
TEXT_PRIMARY = "#1F2937"    # Dark Charcoal Text
TEXT_SECONDARY = "#4B5563"  # Muted Gray Text
COLOR_GOLD = "#D97706"      # Warm Amber for trust / warnings
COLOR_GREEN = "#10B981"     # Emerald Green for Success
COLOR_RED = "#EF4444"       # Rose Red for Danger
COLOR_BORDER = "#E5E7EB"    # Very light border gray

class CampusLinkApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("CampusLink - UMaT Peer-to-Peer Resource Sharing Platform")
        self.geometry("1280x820")
        self.minsize(1024, 700)
        self.configure(bg=BG_MAIN)
        
        # Session State
        self.active_user_id = None
        self.active_user_name = ""
        self.active_user_email = ""
        self.active_user_role = ""
        self.active_user_level = ""
        self.current_screen = None
        self.is_logged_in = False
        
        # UI Setup
        self.setup_styles()
        self.build_structure()
        
        # Show Splash Screen first on launch
        self.withdraw() # Hide main window while splash displays
        self.show_splash_screen()

    
    def show_splash_screen(self):
        splash = tk.Toplevel(self)
        splash.title("CampusLink")
        splash.geometry("520x360")
        splash.overrideredirect(True) # Borderless splash window
        splash.configure(bg="#0A192F")
        
        # Center splash on screen
        splash.update_idletasks()
        sw = splash.winfo_screenwidth()
        sh = splash.winfo_screenheight()
        x = (sw - 520) // 2
        y = (sh - 360) // 2
        splash.geometry(f"520x360+{x}+{y}")
        
        container = tk.Frame(splash, bg="#0A192F", padx=30, pady=30)
        container.pack(fill="both", expand=True)
        
        # Logo Image
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.jpg")
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path).resize((90, 90), Image.Resampling.LANCZOS)
                splash.logo_img = ImageTk.PhotoImage(img)
                lbl_logo = tk.Label(container, image=splash.logo_img, bg="#0A192F")
                lbl_logo.pack(pady=(10, 5))
            except Exception:
                pass
                
        tk.Label(container, text="CampusLink", font=("Segoe UI", 26, "bold"), fg="#FFFFFF", bg="#0A192F").pack()
        tk.Label(container, text="Rent. Borrow. Lend. Earn.", font=("Segoe UI", 11, "bold"), fg="#D97706", bg="#0A192F").pack(pady=(2, 0))
        tk.Label(container, text="University of Mines and Technology (UMaT)", font=("Segoe UI", 9), fg="#94A3B8", bg="#0A192F").pack(pady=(2, 15))
        
        # Progress Bar / Loading indicator
        lbl_load = tk.Label(container, text="Initializing database & security services...", font=("Segoe UI", 9, "italic"), fg="#CBD5E1", bg="#0A192F")
        lbl_load.pack(pady=(0, 10))
        
        progress = ttk.Progressbar(container, mode="indeterminate", length=300)
        progress.pack()
        progress.start(15)
        
        def close_splash():
            progress.stop()
            splash.destroy()
            self.deiconify() # Reveal main app window
            self.show_login_screen()
            
        self.after(2500, close_splash)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure fonts
        self.font_header = ("Segoe UI", 16, "bold")
        self.font_title = ("Segoe UI", 12, "bold")
        self.font_body = ("Segoe UI", 10)
        self.font_muted = ("Segoe UI", 9, "italic")
        self.font_bold = ("Segoe UI", 10, "bold")
        
        # TTK Widget Custom Styles
        style.configure("TFrame", background=BG_MAIN)
        style.configure("Sidebar.TFrame", background=BG_SIDEBAR)
        
        # Label Styles
        style.configure("TLabel", background=BG_MAIN, foreground=TEXT_PRIMARY, font=self.font_body)
        style.configure("Header.TLabel", font=self.font_header, foreground=TEXT_PRIMARY)
        style.configure("Subtitle.TLabel", font=self.font_muted, foreground=TEXT_SECONDARY)
        style.configure("SidebarTitle.TLabel", background=BG_SIDEBAR, foreground="#FFFFFF", font=("Segoe UI", 18, "bold"))
        style.configure("SidebarTagline.TLabel", background=BG_SIDEBAR, foreground=COLOR_PRIMARY, font=("Segoe UI", 8, "bold"))
        style.configure("SidebarButton.TLabel", background=BG_SIDEBAR, foreground="#E2E8F0", font=self.font_bold)
        
        # Button Styles
        style.configure("TButton", font=self.font_bold, borderwidth=1, relief="flat", background=COLOR_PRIMARY, foreground="#FFFFFF")
        style.map("TButton", 
                  background=[('active', '#3B4CB8'), ('disabled', '#D1D5DB')],
                  foreground=[('disabled', '#9CA3AF')])
        
        style.configure("Secondary.TButton", background="#E5E7EB", foreground=TEXT_PRIMARY)
        style.map("Secondary.TButton", background=[('active', '#D1D5DB')])
        
        # Treeview styling (Reports and grids)
        style.configure("Treeview", font=self.font_body, rowheight=26, borderwidth=0, background=COLOR_SECONDARY, foreground=TEXT_PRIMARY)
        style.configure("Treeview.Heading", font=self.font_bold, background="#E5E7EB", foreground=TEXT_PRIMARY, relief="flat")
        style.map("Treeview", background=[('selected', COLOR_PRIMARY)], foreground=[('selected', '#FFFFFF')])

    def build_structure(self):
        # 1. Main Grid layout
        self.grid_columnconfigure(0, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=1) # Main Viewport
        self.grid_rowconfigure(0, weight=0)    # Header
        self.grid_rowconfigure(1, weight=1)    # Main Body
        self.grid_rowconfigure(2, weight=0)    # Status Bar
        
        # 2. Header Frame
        self.header_frame = tk.Frame(self, bg=COLOR_SECONDARY, height=70, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.header_frame.grid_propagate(False)
        self.build_header()
        
        # 3. Sidebar Frame
        self.sidebar_frame = tk.Frame(self, bg=BG_SIDEBAR, width=230)
        self.sidebar_frame.grid(row=1, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        self.build_sidebar()
        
        # 4. Main Viewport Container
        self.viewport_container = tk.Frame(self, bg=BG_MAIN)
        self.viewport_container.grid(row=1, column=1, sticky="nsew")
        
        # 5. Status Bar
        self.status_bar = tk.Frame(self, bg=COLOR_SECONDARY, height=25, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER)
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self.build_status_bar()

    def build_header(self):
        # Clear header children
        for child in self.header_frame.winfo_children():
            child.destroy()
            
        # Logo Image + Text
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.jpg")
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path).resize((44, 44), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(img)
                lbl_img = tk.Label(self.header_frame, image=self.logo_img, bg=COLOR_SECONDARY)
                lbl_img.pack(side="left", padx=(15, 5), pady=10)
            except Exception:
                pass

        logo_label = tk.Label(self.header_frame, text="CampusLink", font=("Segoe UI", 20, "bold"), fg=COLOR_PRIMARY, bg=COLOR_SECONDARY)
        logo_label.pack(side="left", padx=(5, 10), pady=10)
        
        tagline = tk.Label(self.header_frame, text="| Connecting Students Through Shared Resources", font=("Segoe UI", 10, "italic"), fg=TEXT_SECONDARY, bg=COLOR_SECONDARY)
        tagline.pack(side="left", pady=15)
        
        # User Session Badge / Logout Frame
        self.session_frame = tk.Frame(self.header_frame, bg=COLOR_SECONDARY)
        self.session_frame.pack(side="right", padx=20, pady=10)
        
        if self.is_logged_in:
            lbl_user_icon = tk.Label(self.session_frame, text=f"👤 {self.active_user_name}", font=self.font_bold, fg=TEXT_PRIMARY, bg=COLOR_SECONDARY)
            lbl_user_icon.pack(side="left", padx=5)
            
            lbl_user_role = tk.Label(self.session_frame, text=f"({self.active_user_level})", font=self.font_muted, fg=TEXT_SECONDARY, bg=COLOR_SECONDARY)
            lbl_user_role.pack(side="left", padx=(0, 10))
            
            # Trust Score badge
            trust_info = controllers.calculate_trust_score(self.active_user_id)
            lbl_trust = tk.Label(self.session_frame, text=f"Trust Score: {trust_info['score']}/100", font=self.font_bold, fg=COLOR_GOLD, bg=COLOR_SECONDARY, bd=1, relief="solid", padx=8, pady=2)
            lbl_trust.pack(side="left", padx=10)
            
            # Logout Button
            btn_logout = ttk.Button(self.session_frame, text="Logout 🚪", style="Secondary.TButton", command=self.logout_user)
            btn_logout.pack(side="left", padx=5)
        else:
            lbl_logged_out = tk.Label(self.session_frame, text="University of Mines and Technology (UMaT)", font=self.font_bold, fg=TEXT_SECONDARY, bg=COLOR_SECONDARY)
            lbl_logged_out.pack(side="left", padx=10)

    def build_sidebar(self):
        # Clear sidebar children
        for child in self.sidebar_frame.winfo_children():
            child.destroy()
            
        if not self.is_logged_in:
            return
            
        # Brand Space
        brand_frame = tk.Frame(self.sidebar_frame, bg=BG_SIDEBAR, height=80)
        brand_frame.pack(fill="x", pady=(20, 10))
        
        lbl_title = tk.Label(brand_frame, text="CAMPUSLINK", font=("Segoe UI", 18, "bold"), fg="#FFFFFF", bg=BG_SIDEBAR)
        lbl_title.pack()
        lbl_tagline = tk.Label(brand_frame, text="RENT. BORROW. LEND. EARN.", font=("Segoe UI", 8, "bold"), fg=COLOR_PRIMARY, bg=BG_SIDEBAR)
        lbl_tagline.pack()
        
        separator = tk.Frame(self.sidebar_frame, bg="#1E293B", height=1)
        separator.pack(fill="x", padx=15, pady=10)
        
        # Navigation Items based on role
        self.nav_items = [
            ("🏠  Dashboard", "Dashboard"),
            ("🔍  Search Marketplace", "Marketplace"),
            ("📦  My Listings & Requests", "MyListings"),
            ("🎒  My Borrowed Assets", "MyRentals"),
            ("🔖  Saved & Wishlists", "Saves"),
            ("🔧  Maintenance Log", "Maintenance"),
            ("📊  Intelligence Reports", "Reports")
        ]
        
        if self.active_user_level == "Admin":
            self.nav_items.append(("⚙️  Admin Dashboard", "Admin"))
            
        self.sidebar_buttons = {}
        for text, screen in self.nav_items:
            btn = tk.Button(
                self.sidebar_frame, text=f"  {text}", font=self.font_bold,
                fg="#CBD5E1", bg=BG_SIDEBAR, activeforeground="#FFFFFF", activebackground="#1E293B",
                relief="flat", anchor="w", bd=0, padx=15, pady=10,
                command=lambda s=screen: self.switch_screen(s)
            )
            btn.pack(fill="x", padx=10, pady=2)
            
            # Hover animations
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#1E293B", fg="#FFFFFF"))
            btn.bind("<Leave>", lambda e, b=btn: self.style_nav_button(b))
            self.sidebar_buttons[screen] = btn

    def style_nav_button(self, btn):
        if not self.is_logged_in or not hasattr(self, 'nav_items'):
            return
        screen_name = [s for t, s in self.nav_items if f"  {t}" == btn.cget("text") or t == btn.cget("text").strip()]
        if screen_name and screen_name[0] == self.current_screen:
            btn.config(bg=COLOR_PRIMARY, fg="#FFFFFF")
        else:
            btn.config(bg=BG_SIDEBAR, fg="#CBD5E1")

    def build_status_bar(self):
        self.lbl_status_db = tk.Label(self.status_bar, text=f" Database: {db_schema.DB_NAME} (Active)", font=self.font_muted, bg=COLOR_SECONDARY, fg=TEXT_SECONDARY)
        self.lbl_status_db.pack(side="left", padx=10)
        
        self.lbl_status_user = tk.Label(self.status_bar, text="Status: Logged Out", font=self.font_bold, bg=COLOR_SECONDARY, fg=TEXT_SECONDARY)
        self.lbl_status_user.pack(side="right", padx=20)
        
        self.lbl_status_action = tk.Label(self.status_bar, text="Ready", font=self.font_muted, bg=COLOR_SECONDARY, fg=COLOR_GREEN)
        self.lbl_status_action.pack(side="right", padx=20)

        self.lbl_clock = tk.Label(self.status_bar, text="", font=self.font_bold, bg=COLOR_SECONDARY, fg=TEXT_SECONDARY)
        self.lbl_clock.pack(side="right", padx=10)
        self.update_clock()

    def update_clock(self):
        now_str = datetime.now().strftime("%H:%M:%S")
        self.lbl_clock.config(text=f"🕒 {now_str}")
        self.after(1000, self.update_clock)

    def show_toast(self, message, level="success"):
        bg_color = COLOR_GREEN if level == "success" else (COLOR_RED if level == "error" else COLOR_GOLD)
        icon = "✓ " if level == "success" else ("⚠️ " if level == "warning" else "❌ ")
        toast = tk.Label(self, text=f" {icon}{message} ", font=self.font_bold, fg="#FFFFFF", bg=bg_color, padx=16, pady=8, bd=1, relief="ridge")
        toast.place(relx=0.98, rely=0.94, anchor="se")
        self.after(3200, toast.destroy)

    def set_status(self, msg, is_error=False):
        color = COLOR_RED if is_error else COLOR_GREEN
        self.lbl_status_action.config(text=msg, fg=color)

    # =========================================================================
    # AUTHENTICATION & LOGIN FLOW
    # =========================================================================

    def show_login_screen(self):
        self.is_logged_in = False
        self.active_user_id = None
        self.current_screen = "Login"
        self.build_header()
        self.build_sidebar()
        self.lbl_status_user.config(text="Status: Logged Out")
        
        # Clear viewport
        for child in self.viewport_container.winfo_children():
            child.destroy()
            
        frame = tk.Frame(self.viewport_container, bg=BG_MAIN)
        frame.pack(fill="both", expand=True)
        
        # Center Login Box
        center_card = tk.Frame(frame, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=40, pady=30)
        center_card.place(relx=0.5, rely=0.5, anchor="center", width=460)
        
        # Logo Image inside login card
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.jpg")
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path).resize((70, 70), Image.Resampling.LANCZOS)
                self.login_logo_img = ImageTk.PhotoImage(img)
                lbl_l_img = tk.Label(center_card, image=self.login_logo_img, bg=COLOR_SECONDARY)
                lbl_l_img.pack(pady=(0, 5))
            except Exception:
                pass
                
        tk.Label(center_card, text="CampusLink", font=("Segoe UI", 24, "bold"), fg=COLOR_PRIMARY, bg=COLOR_SECONDARY).pack()
        tk.Label(center_card, text="Rent. Borrow. Lend. Earn.", font=("Segoe UI", 10, "bold"), fg=COLOR_GOLD, bg=COLOR_SECONDARY).pack()
        tk.Label(center_card, text="University of Mines and Technology (UMaT)", font=self.font_muted, fg=TEXT_SECONDARY, bg=COLOR_SECONDARY).pack(pady=(2, 0))
        tk.Label(center_card, text="Department of Computer Science & Engineering", font=("Segoe UI", 8, "bold"), fg=COLOR_PRIMARY, bg=COLOR_SECONDARY).pack(pady=(1, 15))
        
        # Form Fields
        tk.Label(center_card, text="UMaT Institutional Email:", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(5, 2))
        ent_email = ttk.Entry(center_card, font=self.font_body)
        ent_email.insert(0, "albert@student.umat.edu.gh")
        ent_email.pack(fill="x", pady=(0, 15))
        
        tk.Label(center_card, text="Password:", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(5, 2))
        ent_password = ttk.Entry(center_card, font=self.font_body, show="*")
        ent_password.insert(0, "Student123")
        ent_password.pack(fill="x", pady=(0, 4))
        
        # Forgot password button / link
        def handle_forgot_password(e=None):
            messagebox.showinfo(
                "Password Reset Assistance",
                "Forgot your password?\n\nPlease contact the CampusLink Administrator (admin@umat.edu.gh) or the UMaT ICT Directorate to verify your identity and request a password reset."
            )
            
        lbl_forgot = tk.Label(center_card, text="Forgot Password?", font=("Segoe UI", 8, "underline"), fg=COLOR_PRIMARY, bg=COLOR_SECONDARY, cursor="hand2")
        lbl_forgot.pack(anchor="e", pady=(0, 15))
        lbl_forgot.bind("<Button-1>", handle_forgot_password)
        
        def handle_login(event=None):
            email = ent_email.get().strip()
            password = ent_password.get().strip()
            
            if not email or not password:
                messagebox.showerror("Login Error", "Please enter both Email and Password.")
                return
                
            res = controllers.authenticate_user(email, password)
            if res == -1:
                messagebox.showerror("Access Denied", "Invalid Email or Password. Please try again.")
            elif res == -2:
                messagebox.showerror("Account Suspended", "Your account has been suspended by an Administrator.")
            elif isinstance(res, dict):
                # Login Success!
                self.active_user_id = res['user_id']
                self.active_user_name = res['name']
                self.active_user_email = res['email']
                self.active_user_level = res['verification_level']
                self.active_user_role = "Admin" if res['verification_level'] == "Admin" else "User"
                self.is_logged_in = True
                
                self.build_header()
                self.build_sidebar()
                self.lbl_status_user.config(text=f"Logged in as: {self.active_user_name} ({self.active_user_level})")
                self.show_toast(f"Welcome back, {self.active_user_name}!", level="success")
                self.switch_screen("Dashboard")
        
        ent_password.bind("<Return>", handle_login)
        ent_email.bind("<Return>", handle_login)
        
        btn_login = ttk.Button(center_card, text="Sign In to CampusLink", command=handle_login)
        btn_login.pack(fill="x", pady=(0, 15))
        
        # Footer link to Register
        footer_frame = tk.Frame(center_card, bg=COLOR_SECONDARY)
        footer_frame.pack()
        tk.Label(footer_frame, text="Don't have an account?", font=self.font_body, fg=TEXT_SECONDARY, bg=COLOR_SECONDARY).pack(side="left")
        btn_reg_link = tk.Button(footer_frame, text="Register Now", font=self.font_bold, fg=COLOR_PRIMARY, bg=COLOR_SECONDARY, bd=0, relief="flat", cursor="hand2", command=self.show_register_screen)
        btn_reg_link.pack(side="left", padx=5)

    def show_register_screen(self):
        self.is_logged_in = False
        self.current_screen = "Register"
        self.build_header()
        self.build_sidebar()
        
        for child in self.viewport_container.winfo_children():
            child.destroy()
            
        frame = tk.Frame(self.viewport_container, bg=BG_MAIN)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        card = tk.Frame(frame, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=35, pady=25)
        card.place(relx=0.5, rely=0.5, anchor="center", width=550)
        
        tk.Label(card, text="Create Your CampusLink Account", font=self.font_header, fg=COLOR_PRIMARY, bg=COLOR_SECONDARY).pack(pady=(0, 15))
        
        # Form scroll
        form_frame = tk.Frame(card, bg=COLOR_SECONDARY)
        form_frame.pack(fill="both", expand=True)
        
        # Full Name
        tk.Label(form_frame, text="Full Name:", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(4, 2))
        ent_name = ttk.Entry(form_frame)
        ent_name.pack(fill="x")
        
        # Email
        tk.Label(form_frame, text="Email Address (e.g. ce-aavoryi8125@st.umat.edu.gh):", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(8, 2))
        ent_email = ttk.Entry(form_frame)
        ent_email.insert(0, "ce-aavoryi8125@st.umat.edu.gh")
        ent_email.pack(fill="x")
        
        # Password Row
        pass_row = tk.Frame(form_frame, bg=COLOR_SECONDARY)
        pass_row.pack(fill="x", pady=8)
        
        tk.Label(pass_row, text="Password:", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=0, sticky="w")
        ent_pass1 = ttk.Entry(pass_row, show="*", width=22)
        ent_pass1.grid(row=1, column=0, sticky="w", padx=(0, 10))
        
        tk.Label(pass_row, text="Confirm Password:", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=1, sticky="w")
        ent_pass2 = ttk.Entry(pass_row, show="*", width=22)
        ent_pass2.grid(row=1, column=1, sticky="w")
        
        # ID & Phone Row
        id_row = tk.Frame(form_frame, bg=COLOR_SECONDARY)
        id_row.pack(fill="x", pady=4)
        
        tk.Label(id_row, text="Index / Staff ID (e.g. FCM.41.008.043.25):", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=0, sticky="w")
        ent_id = ttk.Entry(id_row, width=24)
        ent_id.insert(0, "FCM.41.008.043.25")
        ent_id.grid(row=1, column=0, sticky="w", padx=(0, 10))
        
        tk.Label(id_row, text="Phone Number:", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=1, sticky="w")
        ent_phone = ttk.Entry(id_row, width=22)
        ent_phone.insert(0, "+233")
        ent_phone.grid(row=1, column=1, sticky="w")
        
        # Dept & Hostel Row
        dh_row = tk.Frame(form_frame, bg=COLOR_SECONDARY)
        dh_row.pack(fill="x", pady=8)
        
        tk.Label(dh_row, text="Department:", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=0, sticky="w")
        cmb_dept = ttk.Combobox(dh_row, values=[
            'Mining Engineering', 'Petroleum Engineering', 'Geomatic Engineering', 
            'Electrical & Electronic Engineering', 'Geological Engineering', 
            'Computer Science & Engineering', 'Mathematical Sciences'
        ], state="readonly", width=20)
        cmb_dept.grid(row=1, column=0, sticky="w", padx=(0, 10))
        cmb_dept.current(0)
        
        tk.Label(dh_row, text="Hostel (Optional):", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=1, sticky="w")
        cmb_hostel = ttk.Combobox(dh_row, values=[
            'Chamber of Mines Hostel', 'Gold Refinery Hostel', 'K.T. Hall', 
            'Dr. M.T. Kofi Hall', 'Squatter Camp', 'Staff Quarters', 'Private Hostel'
        ], state="readonly", width=20)
        cmb_hostel.grid(row=1, column=1, sticky="w")
        cmb_hostel.current(0)
        
        def handle_register():
            name = ent_name.get().strip()
            email = ent_email.get().strip()
            p1 = ent_pass1.get().strip()
            p2 = ent_pass2.get().strip()
            sid = ent_id.get().strip()
            phone = ent_phone.get().strip()
            dept = cmb_dept.get()
            hostel = cmb_hostel.get()
            
            if not (name and email and p1 and phone):
                messagebox.showerror("Error", "Please populate Name, Email, Password, and Phone Number.")
                return
                
            if p1 != p2:
                messagebox.showerror("Password Error", "Passwords do not match. Please verify your entry.")
                return
                
            if len(p1) < 6:
                messagebox.showerror("Password Error", "Password must be at least 6 characters long.")
                return
                
            if "@" not in email or "." not in email:
                messagebox.showerror("Email Error", "Please enter a valid email address.")
                return
                
            if not (email.endswith("@umat.edu.gh") or email.endswith("@st.umat.edu.gh")):
                messagebox.showerror("Domain Error", "Email must be a valid UMaT email ending in @umat.edu.gh or @st.umat.edu.gh.")
                return
                
            res = controllers.register_user(name, email, p1, sid, phone, dept, hostel, 'Unverified')
            if res > 0:
                messagebox.showinfo("Registration Successful", "Your account has been created successfully!\nPlease login with your email and password.")
                self.show_login_screen()
            else:
                messagebox.showerror("Registration Error", "Failed to create account. Email or Student ID may already be registered.")
                
        btn_submit = ttk.Button(card, text="Complete Registration", command=handle_register)
        btn_submit.pack(fill="x", pady=(15, 10))
        
        btn_back = ttk.Button(card, text="Back to Login", style="Secondary.TButton", command=self.show_login_screen)
        btn_back.pack(fill="x")

    def logout_user(self):
        if messagebox.askyesno("Confirm Logout", "Are you sure you want to sign out of CampusLink?"):
            self.is_logged_in = False
            self.active_user_id = None
            self.show_toast("Logged out successfully.", level="warning")
            self.show_login_screen()

    def switch_screen(self, screen_name):
        if not self.is_logged_in:
            self.show_login_screen()
            return
            
        self.current_screen = screen_name
        self.set_status(f"Switched to {screen_name}")
        
        # Highlight active sidebar button
        for s, btn in self.sidebar_buttons.items():
            if s == screen_name:
                btn.config(bg=COLOR_PRIMARY, fg="#FFFFFF")
            else:
                btn.config(bg=BG_SIDEBAR, fg="#CBD5E1")
                
        # Clear main viewport
        for child in self.viewport_container.winfo_children():
            child.destroy()
            
        # Draw new screen
        if screen_name == "Dashboard":
            self.draw_dashboard()
        elif screen_name == "Marketplace":
            self.draw_marketplace()
        elif screen_name == "MyListings":
            self.draw_my_listings()
        elif screen_name == "MyRentals":
            self.draw_my_rentals()
        elif screen_name == "Saves":
            self.draw_saves_wishlist()
        elif screen_name == "Maintenance":
            self.draw_maintenance()
        elif screen_name == "Reports":
            self.draw_reports()
        elif screen_name == "Admin":
            self.draw_admin()

    # =========================================================================
    # SCREEN DRAWING FUNCTIONS
    # =========================================================================

    def draw_dashboard(self):
        # Setup Grid
        frame = tk.Frame(self.viewport_container, bg=BG_MAIN)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        lbl_welcome = tk.Label(frame, text=f"Welcome back, {self.active_user_name}!", font=self.font_header, bg=BG_MAIN, fg=TEXT_PRIMARY)
        lbl_welcome.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 20))
        
        # Fetch stats from db
        total_users = controllers.execute_query("SELECT COUNT(*) FROM users;", fetchone=True)[0]
        active_listings = controllers.execute_query("SELECT COUNT(*) FROM listings WHERE status = 'Available';", fetchone=True)[0]
        active_rentals = controllers.execute_query("SELECT COUNT(*) FROM rental_transactions WHERE rental_status = 'Active';", fetchone=True)[0]
        total_revenue = controllers.execute_query("SELECT SUM(commission_amount) FROM rental_transactions WHERE payment_status = 'Paid';", fetchone=True)[0]
        total_revenue = f"GH₵{total_revenue:,.2f}" if total_revenue is not None else "GH₵0.00"
        
        # Metrics Cards
        metrics = [
            ("Total Users", str(total_users), COLOR_PRIMARY),
            ("Active Listings", str(active_listings), COLOR_GREEN),
            ("Active Rentals", str(active_rentals), COLOR_GOLD),
            ("Platform Revenue", total_revenue, "#8B5CF6") # Purple
        ]
        
        for idx, (title, val, color) in enumerate(metrics):
            card = tk.Frame(frame, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER)
            card.grid(row=1, column=idx, padx=10, pady=10, sticky="nsew")
            frame.grid_columnconfigure(idx, weight=1)
            
            indicator = tk.Frame(card, bg=color, width=6)
            indicator.pack(side="left", fill="y")
            
            info_frame = tk.Frame(card, bg=COLOR_SECONDARY, padx=15, pady=15)
            info_frame.pack(side="left", fill="both", expand=True)
            
            lbl_title = tk.Label(info_frame, text=title, font=self.font_bold, fg=TEXT_SECONDARY, bg=COLOR_SECONDARY)
            lbl_title.pack(anchor="w")
            
            lbl_val = tk.Label(info_frame, text=val, font=("Segoe UI", 18, "bold"), fg=TEXT_PRIMARY, bg=COLOR_SECONDARY)
            lbl_val.pack(anchor="w", pady=(5, 0))

        # Lower Panels
        lower_frame = tk.Frame(frame, bg=BG_MAIN)
        lower_frame.grid(row=2, column=0, columnspan=4, pady=20, sticky="nsew")
        frame.grid_rowconfigure(2, weight=1)
        
        lower_frame.grid_columnconfigure(0, weight=3) # Activities
        lower_frame.grid_columnconfigure(1, weight=2) # Personal Stats card
        
        # Left Panel: Recent Transactions
        act_card = tk.Frame(lower_frame, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER)
        act_card.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        lbl_act_title = tk.Label(act_card, text="Recent Marketplace Activity", font=self.font_title, fg=TEXT_PRIMARY, bg=COLOR_SECONDARY, padx=15, pady=10)
        lbl_act_title.pack(anchor="w")
        
        columns = ("listing", "borrower", "dates", "amount", "status")
        tree = ttk.Treeview(act_card, columns=columns, show="headings", height=8)
        tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        tree.heading("listing", text="Item")
        tree.heading("borrower", text="Borrower")
        tree.heading("dates", text="Duration")
        tree.heading("amount", text="Total Paid")
        tree.heading("status", text="Rental Status")
        
        tree.column("listing", width=150)
        tree.column("borrower", width=100)
        tree.column("dates", width=150)
        tree.column("amount", width=80, anchor="center")
        tree.column("status", width=90, anchor="center")
        
        recent_tx = controllers.execute_query("""
            SELECT l.title, u.name, t.rent_start_date, t.rent_end_date, t.gross_amount, t.rental_status
            FROM rental_transactions t
            INNER JOIN listings l ON t.listing_id = l.listing_id
            INNER JOIN users u ON t.borrower_id = u.user_id
            ORDER BY t.created_at DESC LIMIT 5;
        """, fetch=True)
        
        for idx, r in enumerate(recent_tx or []):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            dates = f"{r[2]} to {r[3]}"
            amt = f"GH₵{r[4]:.2f}"
            tree.insert("", "end", values=(r[0], r[1], dates, amt, r[5]), tags=(tag,))
            
        tree.tag_configure("evenrow", background="#F8FAFC")
        tree.tag_configure("oddrow", background="#FFFFFF")
            
        # Right Panel: Personal Trust and Ratings Card
        trust_card = tk.Frame(lower_frame, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER)
        trust_card.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        lbl_trust_title = tk.Label(trust_card, text="Your Reputation & Account Profile", font=self.font_title, fg=TEXT_PRIMARY, bg=COLOR_SECONDARY, padx=15, pady=10)
        lbl_trust_title.pack(anchor="w")
        
        t_info = controllers.calculate_trust_score(self.active_user_id)
        
        trust_score_frame = tk.Frame(trust_card, bg=COLOR_SECONDARY, padx=15, pady=10)
        trust_score_frame.pack(fill="x")
        
        lbl_score_num = tk.Label(trust_score_frame, text=str(t_info["score"]), font=("Segoe UI", 44, "bold"), fg=COLOR_GOLD, bg=COLOR_SECONDARY)
        lbl_score_num.pack(side="left")
        
        lbl_score_desc = tk.Label(trust_score_frame, text="/100 Trust Rating\nCalculated from returns & reviews", font=self.font_bold, fg=TEXT_SECONDARY, bg=COLOR_SECONDARY, justify="left", padx=10)
        lbl_score_desc.pack(side="left")
        
        details_frame = tk.Frame(trust_card, bg=COLOR_SECONDARY, padx=15)
        details_frame.pack(fill="both", expand=True, pady=10)
        
        details = [
            ("Average Rating Received:", f"⭐ {t_info['avg_rating']} ({t_info['rating_count']} reviews)"),
            ("Completed Rentals:", f"{t_info['total_rentals']} total exchanges"),
            ("Late Return Incidents:", f"{t_info['late_returns']} count"),
            ("Verification Level:", self.active_user_level)
        ]
        
        for k, v in details:
            row = tk.Frame(details_frame, bg=COLOR_SECONDARY, pady=4)
            row.pack(fill="x")
            lbl_k = tk.Label(row, text=k, font=self.font_bold, fg=TEXT_SECONDARY, bg=COLOR_SECONDARY)
            lbl_k.pack(side="left")
            lbl_v = tk.Label(row, text=v, font=self.font_body, fg=TEXT_PRIMARY, bg=COLOR_SECONDARY)
            lbl_v.pack(side="right")

    def draw_marketplace(self):
        frame = tk.Frame(self.viewport_container, bg=BG_MAIN)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        frame.grid_columnconfigure(0, weight=0) # Filters
        frame.grid_columnconfigure(1, weight=1) # Listings cards
        frame.grid_rowconfigure(0, weight=1)
        
        # 1. Filters Sidebar
        filter_card = tk.Frame(frame, bg=COLOR_SECONDARY, width=280, highlightthickness=1, highlightbackground=COLOR_BORDER)
        filter_card.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        filter_card.grid_propagate(False)
        
        lbl_filter_title = tk.Label(filter_card, text="Search Filters", font=self.font_title, fg=TEXT_PRIMARY, bg=COLOR_SECONDARY, padx=15, pady=15)
        lbl_filter_title.pack(anchor="w")
        
        filter_scroll = tk.Frame(filter_card, bg=COLOR_SECONDARY, padx=15)
        filter_scroll.pack(fill="both", expand=True)
        
        tk.Label(filter_scroll, text="Keyword Search:", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(5, 2))
        ent_keyword = ttk.Entry(filter_scroll)
        ent_keyword.pack(fill="x", pady=(0, 10))
        
        tk.Label(filter_scroll, text="Category:", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(5, 2))
        self.cat_list = controllers.get_categories()
        cat_names = ["All Categories"] + [c[1] for c in self.cat_list]
        cmb_category = ttk.Combobox(filter_scroll, values=cat_names, state="readonly")
        cmb_category.current(0)
        cmb_category.pack(fill="x", pady=(0, 10))
        
        tk.Label(filter_scroll, text="Max Price per Day (GH₵):", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(5, 2))
        ent_price = ttk.Entry(filter_scroll)
        ent_price.pack(fill="x", pady=(0, 10))
        
        tk.Label(filter_scroll, text="Minimum Condition:", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(5, 2))
        cmb_condition = ttk.Combobox(filter_scroll, values=["Any", "New", "Good", "Fair", "Poor"], state="readonly")
        cmb_condition.current(0)
        cmb_condition.pack(fill="x", pady=(0, 10))
        
        tk.Label(filter_scroll, text="Pickup Location (Hostel/Dept):", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(5, 2))
        ent_location = ttk.Entry(filter_scroll)
        ent_location.pack(fill="x", pady=(0, 10))
        
        tk.Label(filter_scroll, text="Required Start Date (YYYY-MM-DD):", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(5, 2))
        ent_start = ttk.Entry(filter_scroll)
        ent_start.insert(0, datetime.now().strftime("%Y-%m-%d"))
        ent_start.pack(fill="x", pady=(0, 10))
        
        tk.Label(filter_scroll, text="Required End Date (YYYY-MM-DD):", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(5, 2))
        ent_end = ttk.Entry(filter_scroll)
        ent_end.insert(0, (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"))
        ent_end.pack(fill="x", pady=(0, 10))
        
        btn_search = ttk.Button(filter_scroll, text="Apply Search", command=lambda: execute_search())
        btn_search.pack(fill="x", pady=(10, 5))
        
        btn_wishlist = ttk.Button(filter_scroll, text="Watch This Item (Wishlist)", style="Secondary.TButton",
                                  command=lambda: add_wishlist_alert())
        btn_wishlist.pack(fill="x", pady=(5, 5))
        
        # 2. Right Side: Listings display grid
        list_container = tk.Frame(frame, bg=BG_MAIN)
        list_container.grid(row=0, column=1, sticky="nsew")
        
        lbl_list_title = tk.Label(list_container, text="Available Campus Resources", font=self.font_header, bg=BG_MAIN, fg=TEXT_PRIMARY)
        lbl_list_title.pack(anchor="w", pady=(0, 10))
        
        canvas = tk.Canvas(list_container, bg=BG_MAIN, bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        cards_frame = tk.Frame(canvas, bg=BG_MAIN)
        
        cards_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=cards_frame, anchor="nw")
        
        def configure_canvas_width(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", configure_canvas_width)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def execute_search():
            keyword = ent_keyword.get().strip()
            cat_idx = cmb_category.current()
            cat_id = self.cat_list[cat_idx-1][0] if cat_idx > 0 else None
            
            price_val = None
            if ent_price.get().strip():
                try:
                    price_val = float(ent_price.get().strip())
                except ValueError:
                    messagebox.showerror("Error", "Invalid max price value.")
                    return
            
            cond_val = cmb_condition.get()
            if cond_val == "Any":
                cond_val = None
                
            loc_val = ent_location.get().strip()
            if not loc_val:
                loc_val = None
                
            start_val = ent_start.get().strip()
            end_val = ent_end.get().strip()
            
            if start_val or end_val:
                try:
                    datetime.strptime(start_val, "%Y-%m-%d")
                    datetime.strptime(end_val, "%Y-%m-%d")
                except ValueError:
                    messagebox.showerror("Error", "Dates must be in YYYY-MM-DD format.")
                    return
            
            res = controllers.get_filtered_listings(
                keyword=keyword, category_id=cat_id, max_price=price_val, condition=cond_val,
                location=loc_val, exclude_owner_id=self.active_user_id, req_start=start_val, req_end=end_val
            )
            
            render_listing_cards(res, start_val, end_val)

        def add_wishlist_alert():
            cat_idx = cmb_category.current()
            cat_id = self.cat_list[cat_idx-1][0] if cat_idx > 0 else None
            keyword = ent_keyword.get().strip()
            
            if not cat_id and not keyword:
                messagebox.showwarning("Empty Watchlist", "Please select a Category or input a Keyword to add to your Wishlist.")
                return
                
            res = controllers.add_to_wishlist(self.active_user_id, cat_id, keyword)
            if res > 0:
                self.show_toast("Wishlist alert added!", level="success")
            else:
                messagebox.showwarning("Already Watching", "You are already watching this category/keyword alert.")

        def render_listing_cards(listings_list, default_start, default_end):
            for child in cards_frame.winfo_children():
                child.destroy()
                
            if not listings_list:
                tk.Label(cards_frame, text="No matching resources available right now.", font=self.font_bold, fg=TEXT_SECONDARY, bg=BG_MAIN).pack(pady=40)
                return
                
            cards_frame.grid_columnconfigure(0, weight=1)
            cards_frame.grid_columnconfigure(1, weight=1)
            
            for idx, r in enumerate(listings_list):
                c_row = idx // 2
                c_col = idx % 2
                
                card = tk.Frame(cards_frame, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=15, pady=15)
                card.grid(row=c_row, column=c_col, padx=10, pady=10, sticky="nsew")
                
                lbl_title = tk.Label(card, text=r[1], font=self.font_title, fg=COLOR_PRIMARY, bg=COLOR_SECONDARY)
                lbl_title.pack(anchor="w")
                
                lbl_meta = tk.Label(card, text=f"{r[4]} {r[5]} | {r[12]} ({r[3]})", font=self.font_bold, fg=TEXT_SECONDARY, bg=COLOR_SECONDARY)
                lbl_meta.pack(anchor="w", pady=2)
                
                lbl_desc = tk.Label(card, text=r[2], font=self.font_body, fg=TEXT_PRIMARY, bg=COLOR_SECONDARY, wraplength=350, justify="left")
                lbl_desc.pack(anchor="w", pady=(5, 10))
                
                specs_frame = tk.Frame(card, bg=COLOR_SECONDARY)
                specs_frame.pack(fill="x", pady=5)
                
                lbl_rate = tk.Label(specs_frame, text=f"Daily Rate: GH₵{r[6]:.2f}", font=self.font_bold, fg=COLOR_GREEN, bg=COLOR_SECONDARY)
                lbl_rate.grid(row=0, column=0, sticky="w", padx=(0, 20))
                
                lbl_dep = tk.Label(specs_frame, text=f"Deposit: GH₵{r[7]:.2f}", font=self.font_bold, fg=TEXT_PRIMARY, bg=COLOR_SECONDARY)
                lbl_dep.grid(row=0, column=1, sticky="w")
                
                lbl_cond = tk.Label(specs_frame, text=f"Condition: {r[8]}", font=self.font_body, fg=TEXT_SECONDARY, bg=COLOR_SECONDARY)
                lbl_cond.grid(row=1, column=0, sticky="w", pady=2)
                
                lbl_loc = tk.Label(specs_frame, text=f"Location: {r[10]}", font=self.font_body, fg=TEXT_SECONDARY, bg=COLOR_SECONDARY)
                lbl_loc.grid(row=1, column=1, sticky="w", pady=2)
                
                lbl_owner = tk.Label(card, text=f"Lender: {r[11]} | Calendar: {r[13]} to {r[14]}", font=self.font_muted, fg=TEXT_SECONDARY, bg=COLOR_SECONDARY)
                lbl_owner.pack(anchor="w", pady=(5, 10))
                
                btn_frame = tk.Frame(card, bg=COLOR_SECONDARY)
                btn_frame.pack(fill="x")
                
                btn_save = ttk.Button(btn_frame, text="Bookmark", style="Secondary.TButton", 
                                      command=lambda lid=r[0]: bookmark_item(lid))
                btn_save.pack(side="left", padx=(0, 10))
                
                btn_req = ttk.Button(btn_frame, text="Request Rental", 
                                     command=lambda lid=r[0], t=r[1], rate=r[6], dep=r[7]: open_request_modal(lid, t, rate, dep, default_start, default_end))
                btn_req.pack(side="left")
                
        def bookmark_item(listing_id):
            res = controllers.save_listing(self.active_user_id, listing_id)
            if res > 0:
                self.show_toast("Listing bookmarked!", level="success")
            else:
                messagebox.showwarning("Already Saved", "You have already bookmarked this listing.")
                
        def open_request_modal(listing_id, title, rate, deposit, start_d, end_d):
            if self.active_user_level == "Unverified":
                messagebox.showerror("Access Denied", "Unverified accounts cannot borrow resources. Please request verification from an Admin.")
                return
                
            modal = tk.Toplevel(self)
            modal.title(f"Request Rental: {title}")
            modal.geometry("450x450")
            modal.configure(bg=COLOR_SECONDARY)
            modal.transient(self)
            modal.grab_set()
            
            tk.Label(modal, text=f"Requesting: {title}", font=self.font_title, fg=COLOR_PRIMARY, bg=COLOR_SECONDARY, pady=10).pack()
            
            body = tk.Frame(modal, bg=COLOR_SECONDARY, padx=20)
            body.pack(fill="both", expand=True)
            
            tk.Label(body, text="Start Date (YYYY-MM-DD):", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(10, 2))
            ent_m_start = ttk.Entry(body)
            ent_m_start.insert(0, start_d)
            ent_m_start.pack(fill="x")
            
            tk.Label(body, text="End Date (YYYY-MM-DD):", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(10, 2))
            ent_m_end = ttk.Entry(body)
            ent_m_end.insert(0, end_d)
            ent_m_end.pack(fill="x")
            
            tk.Label(body, text="Purpose of Rental:", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(10, 2))
            cmb_purpose = ttk.Combobox(body, values=['Field Trip', 'Final Year Project', 'Laboratory Session', 'Research', 'Presentation', 'Personal Use'], state="readonly")
            cmb_purpose.current(0)
            cmb_purpose.pack(fill="x")
            
            tk.Label(body, text="Message to Lender (Optional):", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(10, 2))
            txt_notes = tk.Text(body, height=4, font=self.font_body, bd=1, relief="solid")
            txt_notes.pack(fill="x")
            
            lbl_calc = tk.Label(body, text="Estimated Cost: GHS --", font=self.font_bold, fg=COLOR_GREEN, bg=COLOR_SECONDARY, pady=10)
            lbl_calc.pack(anchor="w")
            
            def calculate_cost(event=None):
                try:
                    s = datetime.strptime(ent_m_start.get().strip(), "%Y-%m-%d")
                    e = datetime.strptime(ent_m_end.get().strip(), "%Y-%m-%d")
                    days = max((e - s).days + 1, 1)
                    gross = rate * days
                    lbl_calc.config(text=f"Estimated Cost: GH₵{gross:.2f} + Deposit: GH₵{deposit:.2f}")
                except ValueError:
                    lbl_calc.config(text="Estimated Cost: Invalid Date Format")
                    
            ent_m_start.bind("<KeyRelease>", calculate_cost)
            ent_m_end.bind("<KeyRelease>", calculate_cost)
            calculate_cost()
            
            btn_frame = tk.Frame(body, bg=COLOR_SECONDARY, pady=15)
            btn_frame.pack(fill="x")
            
            def send_request():
                s_str = ent_m_start.get().strip()
                e_str = ent_m_end.get().strip()
                purpose = cmb_purpose.get()
                notes = txt_notes.get("1.0", "end-1c").strip()
                
                try:
                    s_date = datetime.strptime(s_str, "%Y-%m-%d")
                    e_date = datetime.strptime(e_str, "%Y-%m-%d")
                    if e_date < s_date:
                        messagebox.showerror("Error", "End date cannot be before start date.")
                        return
                except ValueError:
                    messagebox.showerror("Error", "Invalid Date format (YYYY-MM-DD).")
                    return
                    
                res = controllers.submit_rental_request(listing_id, self.active_user_id, s_str, e_str, purpose, notes)
                if res > 0:
                    self.show_toast("Rental request submitted!", level="success")
                    modal.destroy()
                    self.switch_screen("Marketplace")
                else:
                    messagebox.showerror("Error", "Failed to submit request.")
            
            ttk.Button(btn_frame, text="Cancel", style="Secondary.TButton", command=modal.destroy).pack(side="right", padx=5)
            ttk.Button(btn_frame, text="Submit Request", command=send_request).pack(side="right", padx=5)
        
        execute_search()

    def draw_my_listings(self):
        frame = tk.Frame(self.viewport_container, bg=BG_MAIN)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        frame.grid_columnconfigure(0, weight=2)
        frame.grid_columnconfigure(1, weight=3)
        frame.grid_rowconfigure(0, weight=1)
        
        left_container = tk.Frame(frame, bg=BG_MAIN)
        left_container.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        
        form_card = tk.Frame(left_container, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=15, pady=15)
        form_card.pack(fill="both", expand=True, pady=(0, 15))
        
        lbl_form_t = tk.Label(form_card, text="Post a New Resource", font=self.font_title, fg=COLOR_PRIMARY, bg=COLOR_SECONDARY)
        lbl_form_t.pack(anchor="w", pady=(0, 10))
        
        canvas_f = tk.Canvas(form_card, bg=COLOR_SECONDARY, bd=0, highlightthickness=0)
        scroll_f = ttk.Scrollbar(form_card, orient="vertical", command=canvas_f.yview)
        fields_f = tk.Frame(canvas_f, bg=COLOR_SECONDARY)
        
        fields_f.bind("<Configure>", lambda e: canvas_f.configure(scrollregion=canvas_f.bbox("all")))
        canvas_f.create_window((0, 0), window=fields_f, anchor="nw")
        canvas_f.configure(yscrollcommand=scroll_f.set)
        canvas_f.pack(side="left", fill="both", expand=True)
        scroll_f.pack(side="right", fill="y")
        
        tk.Label(fields_f, text="Listing Title:", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(5, 2))
        ent_title = ttk.Entry(fields_f, width=40)
        ent_title.pack(fill="x")
        
        row_bm = tk.Frame(fields_f, bg=COLOR_SECONDARY)
        row_bm.pack(fill="x", pady=5)
        tk.Label(row_bm, text="Brand:", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=0, sticky="w")
        ent_brand = ttk.Entry(row_bm, width=18)
        ent_brand.grid(row=1, column=0, sticky="w", padx=(0, 10))
        
        tk.Label(row_bm, text="Model:", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=1, sticky="w")
        ent_model = ttk.Entry(row_bm, width=18)
        ent_model.grid(row=1, column=1, sticky="w")
        
        row_cat = tk.Frame(fields_f, bg=COLOR_SECONDARY)
        row_cat.pack(fill="x", pady=5)
        tk.Label(row_cat, text="Category:", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=0, sticky="w")
        self.cat_list = controllers.get_categories()
        cmb_cat = ttk.Combobox(row_cat, values=[c[1] for c in self.cat_list], state="readonly", width=16)
        cmb_cat.grid(row=1, column=0, sticky="w", padx=(0, 10))
        if self.cat_list:
            cmb_cat.current(0)
        
        tk.Label(row_cat, text="Subcategory (Type):", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=1, sticky="w")
        ent_sub = ttk.Entry(row_cat, width=18)
        ent_sub.grid(row=1, column=1, sticky="w")
        
        tk.Label(fields_f, text="Purchase Year (Optional):", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(5, 2))
        ent_year = ttk.Entry(fields_f)
        ent_year.pack(fill="x")
        
        row_rate = tk.Frame(fields_f, bg=COLOR_SECONDARY)
        row_rate.pack(fill="x", pady=5)
        tk.Label(row_rate, text="Daily Rate (GH₵):", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=0, sticky="w")
        ent_rate = ttk.Entry(row_rate, width=18)
        ent_rate.grid(row=1, column=0, sticky="w", padx=(0, 10))
        
        tk.Label(row_rate, text="Security Deposit (GH₵):", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=1, sticky="w")
        ent_deposit = ttk.Entry(row_rate, width=18)
        ent_deposit.grid(row=1, column=1, sticky="w")
        
        row_cond = tk.Frame(fields_f, bg=COLOR_SECONDARY)
        row_cond.pack(fill="x", pady=5)
        tk.Label(row_cond, text="Condition:", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=0, sticky="w")
        cmb_cond = ttk.Combobox(row_cond, values=["New", "Good", "Fair", "Poor"], state="readonly", width=16)
        cmb_cond.grid(row=1, column=0, sticky="w", padx=(0, 10))
        cmb_cond.current(1)
        
        tk.Label(row_cond, text="Pickup Location:", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=1, sticky="w")
        ent_pickup = ttk.Entry(row_cond, width=18)
        ent_pickup.grid(row=1, column=1, sticky="w")
        
        row_dates = tk.Frame(fields_f, bg=COLOR_SECONDARY)
        row_dates.pack(fill="x", pady=5)
        tk.Label(row_dates, text="Available From (YYYY-MM-DD):", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=0, sticky="w")
        ent_av_start = ttk.Entry(row_dates, width=18)
        ent_av_start.insert(0, datetime.now().strftime("%Y-%m-%d"))
        ent_av_start.grid(row=1, column=0, sticky="w", padx=(0, 10))
        
        tk.Label(row_dates, text="Available Until (YYYY-MM-DD):", font=self.font_bold, bg=COLOR_SECONDARY).grid(row=0, column=1, sticky="w")
        ent_av_end = ttk.Entry(row_dates, width=18)
        ent_av_end.insert(0, (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"))
        ent_av_end.grid(row=1, column=1, sticky="w")
        
        tk.Label(fields_f, text="Detailed Description:", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(5, 2))
        txt_desc = tk.Text(fields_f, height=3, width=40, font=self.font_body, bd=1, relief="solid")
        txt_desc.pack(fill="x", pady=(0, 10))
        
        def post_listing():
            if self.active_user_level == "Unverified":
                messagebox.showerror("Access Denied", "Unverified members cannot post resources. Please request verification from an Admin.")
                return
                
            title = ent_title.get().strip()
            brand = ent_brand.get().strip()
            model = ent_model.get().strip()
            cat_idx = cmb_cat.current()
            subcategory = ent_sub.get().strip()
            year_str = ent_year.get().strip()
            rate_str = ent_rate.get().strip()
            dep_str = ent_deposit.get().strip()
            condition = cmb_cond.get()
            location = ent_pickup.get().strip()
            start_str = ent_av_start.get().strip()
            end_str = ent_av_end.get().strip()
            desc = txt_desc.get("1.0", "end-1c").strip()
            
            if not (title and brand and model and cat_idx >= 0 and subcategory and rate_str and dep_str and location and start_str and end_str):
                messagebox.showerror("Missing Fields", "Please populate all mandatory fields.")
                return
                
            category_id = self.cat_list[cat_idx][0]
            
            try:
                rate = float(rate_str)
                deposit = float(dep_str)
                if rate < 0 or deposit < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Daily Rate and Deposit must be positive numeric values.")
                return
                
            year = None
            if year_str:
                try:
                    year = int(year_str)
                except ValueError:
                    messagebox.showerror("Error", "Invalid year format.")
                    return
            
            try:
                datetime.strptime(start_str, "%Y-%m-%d")
                datetime.strptime(end_str, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Error", "Dates must be YYYY-MM-DD.")
                return
                
            res = controllers.create_listing(
                self.active_user_id, category_id, title, desc, subcategory, brand, model, year,
                rate, deposit, condition, location, start_str, end_str
            )
            
            if res > 0:
                self.show_toast(f"Listing '{title}' posted successfully!", level="success")
                self.switch_screen("MyListings")
            else:
                messagebox.showerror("Error", "Failed to insert listing into database.")
                
        btn_post = ttk.Button(fields_f, text="Post Resource", command=post_listing)
        btn_post.pack(fill="x", pady=10)

        # RIGHT COLUMN
        right_container = tk.Frame(frame, bg=BG_MAIN)
        right_container.grid(row=0, column=1, sticky="nsew")
        
        # Section B: Incoming Requests
        req_card = tk.Frame(right_container, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=15, pady=15, height=220)
        req_card.pack(fill="x", pady=(0, 15))
        req_card.pack_propagate(False)
        
        lbl_req_t = tk.Label(req_card, text="Incoming Requests Awaiting My Approval", font=self.font_title, fg=TEXT_PRIMARY, bg=COLOR_SECONDARY)
        lbl_req_t.pack(anchor="w")
        
        req_tree = ttk.Treeview(req_card, columns=("item", "borrower", "dates", "purpose"), show="headings", height=4)
        req_tree.pack(fill="both", expand=True, pady=10)
        req_tree.heading("item", text="My Item")
        req_tree.heading("borrower", text="Renter")
        req_tree.heading("dates", text="Requested Dates")
        req_tree.heading("purpose", text="Purpose")
        
        req_tree.column("item", width=120)
        req_tree.column("borrower", width=100)
        req_tree.column("dates", width=150)
        req_tree.column("purpose", width=100)
        
        incoming = controllers.get_incoming_requests(self.active_user_id) or []
        for idx, r in enumerate(incoming):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            req_tree.insert("", "end", iid=str(r[0]), values=(r[1], r[2], f"{r[3]} to {r[4]}", r[5]), tags=(tag,))
            
        req_tree.tag_configure("evenrow", background="#F8FAFC")
        req_tree.tag_configure("oddrow", background="#FFFFFF")
            
        def handle_request(approve):
            sel = req_tree.selection()
            if not sel:
                messagebox.showwarning("Selection Required", "Please select a pending request from the table.")
                return
                
            req_id = int(sel[0])
            if approve:
                status_code = controllers.approve_request(req_id)
                if status_code == 1:
                    self.show_toast("Request approved!", level="success")
                    self.switch_screen("MyListings")
                elif status_code == -2:
                    messagebox.showerror("Error", "This item is no longer available.")
                else:
                    messagebox.showerror("Error", "Approval failed.")
            else:
                controllers.reject_request(req_id)
                self.show_toast("Request rejected.", level="warning")
                self.switch_screen("MyListings")
                
        btn_req_row = tk.Frame(req_card, bg=COLOR_SECONDARY)
        btn_req_row.pack(fill="x")
        ttk.Button(btn_req_row, text="Reject Request", style="Secondary.TButton", command=lambda: handle_request(False)).pack(side="right", padx=5)
        ttk.Button(btn_req_row, text="Approve & Lock Transaction", command=lambda: handle_request(True)).pack(side="right", padx=5)

        # Section C: Active Lent Resources
        lent_card = tk.Frame(right_container, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=15, pady=15, height=220)
        lent_card.pack(fill="x", pady=(0, 15))
        lent_card.pack_propagate(False)
        
        lbl_lent_t = tk.Label(lent_card, text="Active Rentals (My Resources Lent Out)", font=self.font_title, fg=TEXT_PRIMARY, bg=COLOR_SECONDARY)
        lbl_lent_t.pack(anchor="w")
        
        lent_tree = ttk.Treeview(lent_card, columns=("item", "borrower", "dates", "deposit", "status"), show="headings", height=4)
        lent_tree.pack(fill="both", expand=True, pady=10)
        lent_tree.heading("item", text="Item")
        lent_tree.heading("borrower", text="Renter")
        lent_tree.heading("dates", text="End Date")
        lent_tree.heading("deposit", text="Held Deposit")
        lent_tree.heading("status", text="Status")
        
        lent_tree.column("item", width=120)
        lent_tree.column("borrower", width=100)
        lent_tree.column("dates", width=100, anchor="center")
        lent_tree.column("deposit", width=100, anchor="center")
        lent_tree.column("status", width=95, anchor="center")
        
        lent_items = controllers.get_my_lent_items(self.active_user_id) or []
        for idx, r in enumerate(lent_items):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            lent_tree.insert("", "end", iid=str(r[0]), values=(r[1], r[2], r[4], f"GH₵{r[6]:.2f}", r[5]), tags=(tag,))
            
        lent_tree.tag_configure("evenrow", background="#F8FAFC")
        lent_tree.tag_configure("oddrow", background="#FFFFFF")
            
        def process_lent_return():
            sel = lent_tree.selection()
            if not sel:
                messagebox.showwarning("Selection Required", "Please select an active lent transaction to return.")
                return
                
            tx_id = int(sel[0])
            tx_record = [tx for tx in lent_items if tx[0] == tx_id][0]
            deposit_amt = tx_record[6]
            
            modal = tk.Toplevel(self)
            modal.title("Process Return & Inspect Resource")
            modal.geometry("450x380")
            modal.configure(bg=COLOR_SECONDARY)
            modal.transient(self)
            modal.grab_set()
            
            tk.Label(modal, text=f"Confirm Return of: {tx_record[1]}", font=self.font_title, fg=COLOR_PRIMARY, bg=COLOR_SECONDARY, pady=10).pack()
            
            m_body = tk.Frame(modal, bg=COLOR_SECONDARY, padx=20)
            m_body.pack(fill="both", expand=True)
            
            tk.Label(m_body, text="Inspected Condition:", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(10, 2))
            cmb_damage = ttk.Combobox(m_body, values=["Good (Refund Full Deposit)", "Minor Damage (Partial Claim)", "Severe Damage (Retain Deposit)"], state="readonly")
            cmb_damage.current(0)
            cmb_damage.pack(fill="x")
            
            lbl_claim = tk.Label(m_body, text=f"Claim Amount (GH₵) [Max GH₵{deposit_amt:.2f}]:", font=self.font_bold, bg=COLOR_SECONDARY)
            lbl_claim.pack(anchor="w", pady=(10, 2))
            ent_claim = ttk.Entry(m_body)
            ent_claim.insert(0, "0.00")
            ent_claim.pack(fill="x")
            
            def on_cond_change(event):
                sel_idx = cmb_damage.current()
                if sel_idx == 0:
                    ent_claim.delete(0, "end")
                    ent_claim.insert(0, "0.00")
                    ent_claim.config(state="disabled")
                elif sel_idx == 1:
                    ent_claim.config(state="normal")
                    ent_claim.delete(0, "end")
                    ent_claim.insert(0, "20.00")
                else:
                    ent_claim.config(state="normal")
                    ent_claim.delete(0, "end")
                    ent_claim.insert(0, f"{deposit_amt:.2f}")
            cmb_damage.bind("<<ComboboxSelected>>", on_cond_change)
            on_cond_change(None)
            
            tk.Label(m_body, text="Inspection Notes:", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(10, 2))
            txt_m_notes = tk.Text(m_body, height=3, font=self.font_body, bd=1, relief="solid")
            txt_m_notes.pack(fill="x")
            
            def confirm_refund():
                notes = txt_m_notes.get("1.0", "end-1c").strip()
                cond_idx = cmb_damage.current()
                claim_val = 0.0
                
                if cond_idx > 0:
                    try:
                        claim_val = float(ent_claim.get().strip())
                        if claim_val < 0 or claim_val > deposit_amt:
                            raise ValueError
                    except ValueError:
                        messagebox.showerror("Error", f"Claim amount must be between 0 and GH₵{deposit_amt:.2f}.")
                        return
                
                cond_map = ['Good', 'Minor', 'Severe']
                damage_condition = cond_map[cond_idx]
                
                res = controllers.process_return(tx_id, notes, damage_condition, claim_val)
                if res > 0:
                    self.show_toast("Return processed successfully!", level="success")
                    modal.destroy()
                    self.switch_screen("MyListings")
                else:
                    messagebox.showerror("Error", "Return processing failed.")
            
            btn_box = tk.Frame(m_body, bg=COLOR_SECONDARY, pady=15)
            btn_box.pack(fill="x")
            ttk.Button(btn_box, text="Cancel", style="Secondary.TButton", command=modal.destroy).pack(side="right", padx=5)
            ttk.Button(btn_box, text="Process Handover", command=confirm_refund).pack(side="right", padx=5)
            
        btn_return = ttk.Button(lent_card, text="Confirm Return & Process Deposit", command=process_lent_return)
        btn_return.pack(anchor="e")

        # Section D: My Active Listings
        active_list_card = tk.Frame(right_container, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=15, pady=15)
        active_list_card.pack(fill="both", expand=True)
        
        lbl_list_t = tk.Label(active_list_card, text="My Active Listings", font=self.font_title, fg=TEXT_PRIMARY, bg=COLOR_SECONDARY)
        lbl_list_t.pack(anchor="w")
        
        my_tree = ttk.Treeview(active_list_card, columns=("title", "category", "rate", "deposit", "status"), show="headings", height=5)
        my_tree.pack(fill="both", expand=True, pady=10)
        my_tree.heading("title", text="Title")
        my_tree.heading("category", text="Category")
        my_tree.heading("rate", text="Rate/Day")
        my_tree.heading("deposit", text="Deposit")
        my_tree.heading("status", text="Status")
        
        my_tree.column("title", width=120)
        my_tree.column("category", width=100)
        my_tree.column("rate", width=80, anchor="center")
        my_tree.column("deposit", width=80, anchor="center")
        my_tree.column("status", width=95, anchor="center")
        
        my_list = controllers.get_my_listings(self.active_user_id) or []
        for idx, r in enumerate(my_list):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            my_tree.insert("", "end", iid=str(r[0]), values=(r[1], r[3], f"GH₵{r[7]:.2f}", f"GH₵{r[8]:.2f}", r[10]), tags=(tag,))
            
        my_tree.tag_configure("evenrow", background="#F8FAFC")
        my_tree.tag_configure("oddrow", background="#FFFFFF")
            
        def delist_item():
            sel = my_tree.selection()
            if not sel:
                messagebox.showwarning("Selection Required", "Please select a listing to delist.")
                return
                
            lid = int(sel[0])
            confirm = messagebox.askyesno("Delist Confirmation", "Are you sure you want to permanently delist this resource?")
            if confirm:
                res = controllers.execute_query("UPDATE listings SET status = 'Delisted' WHERE listing_id = ?;", (lid,))
                if res > 0:
                    self.show_toast("Listing delisted.", level="warning")
                    self.switch_screen("MyListings")
                else:
                    messagebox.showerror("Error", "Delisting failed.")
                    
        btn_delist = ttk.Button(active_list_card, text="Delist / Suspend Listing", style="Secondary.TButton", command=delist_item)
        btn_delist.pack(anchor="e")

    def draw_my_rentals(self):
        frame = tk.Frame(self.viewport_container, bg=BG_MAIN)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        out_card = tk.Frame(frame, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=15, pady=15)
        out_card.grid(row=0, column=0, sticky="nsew", pady=(0, 15))
        
        lbl_out_t = tk.Label(out_card, text="My Booking Requests", font=self.font_title, fg=TEXT_PRIMARY, bg=COLOR_SECONDARY)
        lbl_out_t.pack(anchor="w")
        
        out_tree = ttk.Treeview(out_card, columns=("item", "owner", "dates", "purpose", "status"), show="headings", height=5)
        out_tree.pack(fill="both", expand=True, pady=10)
        out_tree.heading("item", text="Resource")
        out_tree.heading("owner", text="Lender")
        out_tree.heading("dates", text="Booking Dates")
        out_tree.heading("purpose", text="Purpose")
        out_tree.heading("status", text="Request Status")
        
        out_tree.column("item", width=120)
        out_tree.column("owner", width=100)
        out_tree.column("dates", width=150)
        out_tree.column("purpose", width=100)
        out_tree.column("status", width=95, anchor="center")
        
        my_reqs = controllers.get_my_requests(self.active_user_id) or []
        for idx, r in enumerate(my_reqs):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            out_tree.insert("", "end", iid=str(r[0]), values=(r[1], r[2], f"{r[3]} to {r[4]}", r[5], r[6]), tags=(tag,))
            
        out_tree.tag_configure("evenrow", background="#F8FAFC")
        out_tree.tag_configure("oddrow", background="#FFFFFF")
            
        def cancel_booking():
            sel = out_tree.selection()
            if not sel:
                messagebox.showwarning("Selection Required", "Please select a request to cancel.")
                return
                
            rid = int(sel[0])
            confirm = messagebox.askyesno("Cancel Booking", "Are you sure you want to cancel this booking request?")
            if confirm:
                controllers.cancel_request(rid)
                self.show_toast("Booking cancelled.", level="warning")
                self.switch_screen("MyRentals")
                
        btn_cancel = ttk.Button(out_card, text="Cancel Booking Request", style="Secondary.TButton", command=cancel_booking)
        btn_cancel.pack(anchor="e")

        borrow_card = tk.Frame(frame, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=15, pady=15)
        borrow_card.grid(row=1, column=0, sticky="nsew")
        
        lbl_borrow_t = tk.Label(borrow_card, text="Ongoing Borrowed Resources (Items in my possession)", font=self.font_title, fg=TEXT_PRIMARY, bg=COLOR_SECONDARY)
        lbl_borrow_t.pack(anchor="w")
        
        borrow_tree = ttk.Treeview(borrow_card, columns=("item", "owner", "dates", "amount", "status"), show="headings", height=5)
        borrow_tree.pack(fill="both", expand=True, pady=10)
        borrow_tree.heading("item", text="Resource")
        borrow_tree.heading("owner", text="Lender")
        borrow_tree.heading("dates", text="Due Return Date")
        borrow_tree.heading("amount", text="Total Paid")
        borrow_tree.heading("status", text="Rental Status")
        
        borrow_tree.column("item", width=120)
        borrow_tree.column("owner", width=100)
        borrow_tree.column("dates", width=120, anchor="center")
        borrow_tree.column("amount", width=80, anchor="center")
        borrow_tree.column("status", width=95, anchor="center")
        
        borrowed = controllers.get_my_borrowed_items(self.active_user_id) or []
        for idx, r in enumerate(borrowed):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            borrow_tree.insert("", "end", iid=str(r[0]), values=(r[1], r[2], r[4], f"GH₵{r[7]:.2f}", r[5]), tags=(tag,))
            
        borrow_tree.tag_configure("evenrow", background="#F8FAFC")
        borrow_tree.tag_configure("oddrow", background="#FFFFFF")
            
        def leave_review():
            history = controllers.execute_query("""
                SELECT t.transaction_id, l.title, u.name, l.owner_id
                FROM rental_transactions t
                INNER JOIN listings l ON t.listing_id = l.listing_id
                INNER JOIN users u ON l.owner_id = u.user_id
                WHERE t.borrower_id = ? AND t.rental_status = 'Returned';
            """, (self.active_user_id,), fetch=True) or []
            
            if not history:
                messagebox.showinfo("No History", "You do not have any returned rentals to review yet.")
                return
                
            modal = tk.Toplevel(self)
            modal.title("Review Lender")
            modal.geometry("450x330")
            modal.configure(bg=COLOR_SECONDARY)
            modal.transient(self)
            modal.grab_set()
            
            tk.Label(modal, text="Leave Feedback for Lender", font=self.font_title, fg=COLOR_PRIMARY, bg=COLOR_SECONDARY, pady=10).pack()
            
            m_body = tk.Frame(modal, bg=COLOR_SECONDARY, padx=20)
            m_body.pack(fill="both", expand=True)
            
            tk.Label(m_body, text="Select Transaction:", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(10, 2))
            tx_opts = [f"Tx {h[0]}: {h[1]} (Lender: {h[2]})" for h in history]
            cmb_tx = ttk.Combobox(m_body, values=tx_opts, state="readonly")
            cmb_tx.current(0)
            cmb_tx.pack(fill="x")
            
            tk.Label(m_body, text="Rating (1-5 Stars):", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(10, 2))
            cmb_rating = ttk.Combobox(m_body, values=["5 - Excellent", "4 - Good", "3 - Average", "2 - Poor", "1 - Terrible"], state="readonly")
            cmb_rating.current(0)
            cmb_rating.pack(fill="x")
            
            tk.Label(m_body, text="Review Comment:", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(10, 2))
            txt_comment = tk.Text(m_body, height=4, font=self.font_body, bd=1, relief="solid")
            txt_comment.pack(fill="x")
            
            def submit_rating():
                tx_idx = cmb_tx.current()
                rating_val = 5 - cmb_rating.current()
                comment = txt_comment.get("1.0", "end-1c").strip()
                
                tx_id = history[tx_idx][0]
                owner_id = history[tx_idx][3]
                
                res = controllers.submit_review(tx_id, self.active_user_id, owner_id, 'Lender', rating_val, comment)
                if res > 0:
                    self.show_toast("Review submitted successfully!", level="success")
                    modal.destroy()
                    self.switch_screen("MyRentals")
                else:
                    messagebox.showwarning("Duplicate Review", "You have already left feedback for this transaction.")
            
            btn_box = tk.Frame(m_body, bg=COLOR_SECONDARY, pady=15)
            btn_box.pack(fill="x")
            ttk.Button(btn_box, text="Cancel", style="Secondary.TButton", command=modal.destroy).pack(side="right", padx=5)
            ttk.Button(btn_box, text="Submit Review", command=submit_rating).pack(side="right", padx=5)
            
        btn_row = tk.Frame(borrow_card, bg=COLOR_SECONDARY)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Leave Feedback / Review Lender", command=leave_review).pack(side="right")

    def draw_saves_wishlist(self):
        frame = tk.Frame(self.viewport_container, bg=BG_MAIN)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        
        save_card = tk.Frame(frame, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=15, pady=15)
        save_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        lbl_s_t = tk.Label(save_card, text="Bookmarked Listings (Saves)", font=self.font_title, fg=COLOR_PRIMARY, bg=COLOR_SECONDARY)
        lbl_s_t.pack(anchor="w")
        
        s_tree = ttk.Treeview(save_card, columns=("title", "owner", "rate", "status"), show="headings", height=10)
        s_tree.pack(fill="both", expand=True, pady=10)
        s_tree.heading("title", text="Listing Title")
        s_tree.heading("owner", text="Owner")
        s_tree.heading("rate", text="Price")
        s_tree.heading("status", text="Status")
        
        s_tree.column("title", width=150)
        s_tree.column("owner", width=100)
        s_tree.column("rate", width=80, anchor="center")
        s_tree.column("status", width=95, anchor="center")
        
        saves_list = controllers.get_my_saved_listings(self.active_user_id) or []
        for idx, r in enumerate(saves_list):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            s_tree.insert("", "end", iid=str(r[0]), values=(r[2], r[7], f"GH₵{r[3]:.2f}", r[6]), tags=(tag,))
            
        s_tree.tag_configure("evenrow", background="#F8FAFC")
        s_tree.tag_configure("oddrow", background="#FFFFFF")
            
        def remove_save():
            sel = s_tree.selection()
            if not sel:
                messagebox.showwarning("Selection Required", "Please select a bookmark to delete.")
                return
            sid = int(sel[0])
            controllers.unsave_listing(sid)
            self.show_toast("Bookmark removed.", level="warning")
            self.switch_screen("Saves")
            
        btn_rem_save = ttk.Button(save_card, text="Remove Bookmark", style="Secondary.TButton", command=remove_save)
        btn_rem_save.pack(anchor="e")

        wish_card = tk.Frame(frame, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=15, pady=15)
        wish_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        lbl_w_t = tk.Label(wish_card, text="Wishlist Alerts (Watched Items)", font=self.font_title, fg=COLOR_PRIMARY, bg=COLOR_SECONDARY)
        lbl_w_t.pack(anchor="w")
        
        w_tree = ttk.Treeview(wish_card, columns=("category", "keyword", "date"), show="headings", height=10)
        w_tree.pack(fill="both", expand=True, pady=10)
        w_tree.heading("category", text="Watched Category")
        w_tree.heading("keyword", text="Keyword Match")
        w_tree.heading("date", text="Created Date")
        
        w_tree.column("category", width=120)
        w_tree.column("keyword", width=100)
        w_tree.column("date", width=120, anchor="center")
        
        wish_list = controllers.get_my_wishlist(self.active_user_id) or []
        for idx, r in enumerate(wish_list):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            cat = r[1] if r[1] is not None else "Any Category"
            kw = r[2] if r[2] is not None else "Any Keyword"
            w_tree.insert("", "end", iid=str(r[0]), values=(cat, kw, r[3].split()[0]), tags=(tag,))
            
        w_tree.tag_configure("evenrow", background="#F8FAFC")
        w_tree.tag_configure("oddrow", background="#FFFFFF")
            
        def remove_wish():
            sel = w_tree.selection()
            if not sel:
                messagebox.showwarning("Selection Required", "Please select a wishlist alert to delete.")
                return
            wid = int(sel[0])
            controllers.remove_from_wishlist(wid)
            self.show_toast("Wishlist alert deleted.", level="warning")
            self.switch_screen("Saves")
            
        btn_rem_wish = ttk.Button(wish_card, text="Delete Wishlist Alert", style="Secondary.TButton", command=remove_wish)
        btn_rem_wish.pack(anchor="e")

    def draw_maintenance(self):
        frame = tk.Frame(self.viewport_container, bg=BG_MAIN)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        lbl_m_t = tk.Label(frame, text="Maintenance Log & Damage History", font=self.font_header, bg=BG_MAIN, fg=TEXT_PRIMARY)
        lbl_m_t.pack(anchor="w", pady=(0, 10))
        
        card = tk.Frame(frame, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=15, pady=15)
        card.pack(fill="both", expand=True)
        
        m_tree = ttk.Treeview(card, columns=("item", "reported", "issue", "cost", "status", "start", "end"), show="headings", height=15)
        m_tree.pack(fill="both", expand=True, pady=10)
        m_tree.heading("item", text="Resource")
        m_tree.heading("reported", text="Reported By")
        m_tree.heading("issue", text="Issue Details")
        m_tree.heading("cost", text="Estimated Cost")
        m_tree.heading("status", text="Status")
        m_tree.heading("start", text="Logged Date")
        m_tree.heading("end", text="Completed Date")
        
        m_tree.column("item", width=120)
        m_tree.column("reported", width=100)
        m_tree.column("issue", width=220)
        m_tree.column("cost", width=95, anchor="center")
        m_tree.column("status", width=90, anchor="center")
        m_tree.column("start", width=95, anchor="center")
        m_tree.column("end", width=95, anchor="center")
        
        logs = controllers.get_maintenance_records() or []
        for idx, r in enumerate(logs):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            m_tree.insert("", "end", iid=str(r[0]), values=(r[1], r[2], r[3], f"GH₵{r[4]:.2f}", r[5], r[6], r[7] if r[7] else "--"), tags=(tag,))
            
        m_tree.tag_configure("evenrow", background="#F8FAFC")
        m_tree.tag_configure("oddrow", background="#FFFFFF")
            
        def update_repair():
            sel = m_tree.selection()
            if not sel:
                messagebox.showwarning("Selection Required", "Please select a maintenance log from the table.")
                return
                
            m_id = int(sel[0])
            record = [log for log in logs if log[0] == m_id][0]
            listing_id = record[8]
            
            if self.active_user_level != "Admin" and self.active_user_name != record[2]:
                messagebox.showerror("Permission Denied", "Only administrators or the listing owner can log repair completions.")
                return
                
            modal = tk.Toplevel(self)
            modal.title("Update Repair Status")
            modal.geometry("400x250")
            modal.configure(bg=COLOR_SECONDARY)
            modal.transient(self)
            modal.grab_set()
            
            tk.Label(modal, text=f"Update: {record[1]}", font=self.font_title, fg=COLOR_PRIMARY, bg=COLOR_SECONDARY, pady=10).pack()
            
            m_body = tk.Frame(modal, bg=COLOR_SECONDARY, padx=20)
            m_body.pack(fill="both", expand=True)
            
            tk.Label(m_body, text="Repair Status:", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(10, 2))
            cmb_st = ttk.Combobox(m_body, values=["Pending", "In Progress", "Completed"], state="readonly")
            cmb_st.set(record[5])
            cmb_st.pack(fill="x")
            
            tk.Label(m_body, text="Actual Maintenance Cost (GH₵):", font=self.font_bold, bg=COLOR_SECONDARY).pack(anchor="w", pady=(10, 2))
            ent_m_cost = ttk.Entry(m_body)
            ent_m_cost.insert(0, f"{record[4]:.2f}")
            ent_m_cost.pack(fill="x")
            
            def save_repair():
                status = cmb_st.get()
                try:
                    cost_val = float(ent_m_cost.get().strip())
                    if cost_val < 0:
                        raise ValueError
                except ValueError:
                    messagebox.showerror("Error", "Invalid repair cost amount.")
                    return
                    
                res = controllers.update_maintenance(m_id, cost_val, status, listing_id)
                if res > 0:
                    self.show_toast("Maintenance record updated!", level="success")
                    modal.destroy()
                    self.switch_screen("Maintenance")
                else:
                    messagebox.showerror("Error", "Update failed.")
                    
            btn_box = tk.Frame(m_body, bg=COLOR_SECONDARY, pady=15)
            btn_box.pack(fill="x")
            ttk.Button(btn_box, text="Cancel", style="Secondary.TButton", command=modal.destroy).pack(side="right", padx=5)
            ttk.Button(btn_box, text="Save Changes", command=save_repair).pack(side="right", padx=5)
            
        btn_update = ttk.Button(card, text="Log Repair Status / Cost", command=update_repair)
        btn_update.pack(anchor="e")

    def draw_reports(self):
        frame = tk.Frame(self.viewport_container, bg=BG_MAIN)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=3)
        frame.grid_rowconfigure(0, weight=1)
        
        list_card = tk.Frame(frame, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=15, pady=15)
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        
        lbl_list_t = tk.Label(list_card, text="Select Report", font=self.font_title, fg=TEXT_PRIMARY, bg=COLOR_SECONDARY)
        lbl_list_t.pack(anchor="w", pady=(0, 10))
        
        reports_nav = tk.Listbox(list_card, font=self.font_bold, bg=COLOR_SECONDARY, fg=TEXT_PRIMARY, selectbackground=COLOR_PRIMARY, selectforeground="#FFFFFF", bd=0, highlightthickness=0)
        reports_nav.pack(fill="both", expand=True)
        
        report_names = [
            "1. Platform Revenue Summary",
            "2. Highest Earning Owners",
            "3. Highest Spending Borrowers",
            "4. Category Popularity Summary",
            "5. Most Borrowed Resources",
            "6. Resources Never Borrowed",
            "7. Current Overdue Rentals",
            "8. Maintenance Cost Summary",
            "9. Common Rental Purposes",
            "10. Category Rental Periods",
            "11. Highest Rated Lenders",
            "12. Highest Rated Borrowers",
            "13. Listed Resources by Hostel",
            "14. Monthly Transaction Trend",
            "15. Frequently Late Borrowers"
        ]
        
        for name in report_names:
            reports_nav.insert("end", name)
            
        reports_nav.selection_set(0)
        
        results_card = tk.Frame(frame, bg=COLOR_SECONDARY, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=15, pady=15)
        results_card.grid(row=0, column=1, sticky="nsew")
        
        lbl_res_t = tk.Label(results_card, text="Report Results", font=self.font_title, fg=COLOR_PRIMARY, bg=COLOR_SECONDARY)
        lbl_res_t.pack(anchor="w")
        
        self.report_table_frame = tk.Frame(results_card, bg=COLOR_SECONDARY)
        self.report_table_frame.pack(fill="both", expand=True, pady=15)
        
        self.current_headers = []
        self.current_rows = []
        
        def run_selected_report(event=None):
            sel = reports_nav.curselection()
            if not sel:
                return
            idx = int(sel[0]) + 1
            
            lbl_res_t.config(text=f"Report Results: {report_names[idx-1]}")
            
            headers, rows = controllers.get_report_data(idx)
            self.current_headers = headers
            self.current_rows = rows
            
            for child in self.report_table_frame.winfo_children():
                child.destroy()
                
            if not headers:
                tk.Label(self.report_table_frame, text="No data available for this report.", font=self.font_bold, bg=COLOR_SECONDARY).pack(pady=40)
                return
                
            tree = ttk.Treeview(self.report_table_frame, columns=headers, show="headings")
            tree.pack(fill="both", expand=True)
            
            scrollbar = ttk.Scrollbar(self.report_table_frame, orient="vertical", command=tree.yview)
            scrollbar.pack(side="right", fill="y")
            tree.configure(yscrollcommand=scrollbar.set)
            
            for col in headers:
                tree.heading(col, text=col)
                tree.column(col, width=120, anchor="center")
                
            for idx, r in enumerate(rows or []):
                tag = "evenrow" if idx % 2 == 0 else "oddrow"
                formatted_row = []
                for val in r:
                    if isinstance(val, float):
                        formatted_row.append(f"{val:.2f}")
                    elif val is None:
                        formatted_row.append("--")
                    else:
                        formatted_row.append(str(val))
                tree.insert("", "end", values=formatted_row, tags=(tag,))
                
            tree.tag_configure("evenrow", background="#F8FAFC")
            tree.tag_configure("oddrow", background="#FFFFFF")
                
        reports_nav.bind("<<ListboxSelect>>", run_selected_report)
        run_selected_report()
        
        def export_to_csv():
            if not self.current_headers:
                messagebox.showwarning("Warning", "No report data to export.")
                return
                
            file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
            if not file_path:
                return
                
            try:
                with open(file_path, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.current_headers)
                    writer.writerows(self.current_rows)
                self.show_toast("Report saved to CSV successfully!", level="success")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save CSV file:\n{e}")
                
        btn_export = ttk.Button(results_card, text="Export Report to CSV", command=export_to_csv)
        btn_export.pack(anchor="e")

    def draw_admin(self):
        frame = tk.Frame(self.viewport_container, bg=BG_MAIN)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        if self.active_user_level != "Admin":
            tk.Label(frame, text="ACCESS DENIED: Administrator Privileges Required", font=self.font_header, fg=COLOR_RED, bg=BG_MAIN).pack(pady=50)
            tk.Label(frame, text="Please log in with an Administrator account (admin@umat.edu.gh) to view this console.", font=self.font_bold, fg=TEXT_SECONDARY, bg=BG_MAIN).pack()
            return
            
        lbl_adm_t = tk.Label(frame, text="CampusLink Administrative Console", font=self.font_header, bg=BG_MAIN, fg=TEXT_PRIMARY)
        lbl_adm_t.pack(anchor="w", pady=(0, 10))
        
        notebook = ttk.Notebook(frame)
        notebook.pack(fill="both", expand=True)
        
        # Tab 1: Member Verification Queue
        verify_tab = tk.Frame(notebook, bg=COLOR_SECONDARY, padx=15, pady=15)
        notebook.add(verify_tab, text="Verify Registrants")
        
        v_tree = ttk.Treeview(verify_tab, columns=("id", "name", "email", "phone", "level", "dept", "status"), show="headings", height=10)
        v_tree.pack(fill="both", expand=True, pady=10)
        v_tree.heading("id", text="User ID")
        v_tree.heading("name", text="Full Name")
        v_tree.heading("email", text="Email")
        v_tree.heading("phone", text="Phone")
        v_tree.heading("level", text="Verification Status")
        v_tree.heading("dept", text="Department")
        v_tree.heading("status", text="Account Status")
        
        v_tree.column("id", width=60, anchor="center")
        v_tree.column("name", width=120)
        v_tree.column("email", width=150)
        v_tree.column("phone", width=100)
        v_tree.column("level", width=110, anchor="center")
        v_tree.column("dept", width=150)
        v_tree.column("status", width=100, anchor="center")
        
        users_list = controllers.get_all_users() or []
        for idx, r in enumerate(users_list):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            v_tree.insert("", "end", iid=str(r[0]), values=(r[0], r[1], r[2], r[4], r[5], r[6], r[8]), tags=(tag,))
            
        v_tree.tag_configure("evenrow", background="#F8FAFC")
        v_tree.tag_configure("oddrow", background="#FFFFFF")
            
        def set_verification(status):
            sel = v_tree.selection()
            if not sel:
                messagebox.showwarning("Selection Required", "Please select a registrant to verify.")
                return
            uid = int(sel[0])
            controllers.update_user_verification(uid, status)
            self.show_toast(f"User level updated to: {status}", level="success")
            self.switch_screen("Admin")

        def toggle_account_status(status):
            sel = v_tree.selection()
            if not sel:
                messagebox.showwarning("Selection Required", "Please select a user account.")
                return
            uid = int(sel[0])
            controllers.execute_query("UPDATE users SET account_status = ? WHERE user_id = ?;", (status, uid))
            self.show_toast(f"Account status updated to: {status}", level="warning")
            self.switch_screen("Admin")
            
        btn_v_row = tk.Frame(verify_tab, bg=COLOR_SECONDARY)
        btn_v_row.pack(fill="x")
        ttk.Button(btn_v_row, text="Suspend Account", style="Secondary.TButton", command=lambda: toggle_account_status("Suspended")).pack(side="right", padx=5)
        ttk.Button(btn_v_row, text="Activate Account", style="Secondary.TButton", command=lambda: toggle_account_status("Active")).pack(side="right", padx=5)
        ttk.Button(btn_v_row, text="Verify as Staff", command=lambda: set_verification("Verified Staff")).pack(side="right", padx=5)
        ttk.Button(btn_v_row, text="Verify as Student", command=lambda: set_verification("Verified Student")).pack(side="right", padx=5)

        # Tab 2: Suspend Listings Console
        list_tab = tk.Frame(notebook, bg=COLOR_SECONDARY, padx=15, pady=15)
        notebook.add(list_tab, text="Moderate Listings")
        
        l_tree = ttk.Treeview(list_tab, columns=("id", "title", "owner", "rate", "status"), show="headings", height=10)
        l_tree.pack(fill="both", expand=True, pady=10)
        l_tree.heading("id", text="Listing ID")
        l_tree.heading("title", text="Item Title")
        l_tree.heading("owner", text="Owner Name")
        l_tree.heading("rate", text="Daily Rate")
        l_tree.heading("status", text="Status")
        
        l_tree.column("id", width=60, anchor="center")
        l_tree.column("title", width=150)
        l_tree.column("owner", width=120)
        l_tree.column("rate", width=80, anchor="center")
        l_tree.column("status", width=95, anchor="center")
        
        all_listings = controllers.execute_query("""
            SELECT l.listing_id, l.title, u.name, l.rental_rate_per_day, l.status
            FROM listings l
            INNER JOIN users u ON l.owner_id = u.user_id
            WHERE l.status != 'Delisted';
        """, fetch=True) or []
        
        for idx, r in enumerate(all_listings):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            l_tree.insert("", "end", iid=str(r[0]), values=(r[0], r[1], r[2], f"GH₵{r[3]:.2f}", r[4]), tags=(tag,))
            
        l_tree.tag_configure("evenrow", background="#F8FAFC")
        l_tree.tag_configure("oddrow", background="#FFFFFF")
            
        def admin_suspend_listing():
            sel = l_tree.selection()
            if not sel:
                messagebox.showwarning("Selection Required", "Please select a listing to suspend.")
                return
            lid = int(sel[0])
            confirm = messagebox.askyesno("Confirm Suspension", "Are you sure you want to suspend this listing?")
            if confirm:
                controllers.execute_query("UPDATE listings SET status = 'Delisted' WHERE listing_id = ?;", (lid,))
                self.show_toast("Listing suspended.", level="warning")
                self.switch_screen("Admin")
                
        btn_suspend = ttk.Button(list_tab, text="Suspend Selected Listing", command=admin_suspend_listing)
        btn_suspend.pack(anchor="e")

if __name__ == "__main__":
    app = CampusLinkApp()
    app.mainloop()
