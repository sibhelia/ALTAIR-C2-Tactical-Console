import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QListWidget, QGroupBox, QGridLayout,
    QRubberBand, QFrame, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, QTimer
from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor
from turret_system import ZoneType

class VideoLabel(QLabel):
    def __init__(self, turret_system, parent=None):
        super().__init__(parent)
        self.turret_system = turret_system
        self.rubberBand = None
        self.origin = QPoint()
        self.current_zone_type = ZoneType.NO_MOVEMENT
        self.setStyleSheet("background-color: #0d1117; border: 2px solid #22c55e;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_zone_type(self, z_type):
        self.current_zone_type = z_type

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.pos()
            if not self.rubberBand:
                self.rubberBand = QRubberBand(QRubberBand.Shape.Rectangle, self)
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            self.rubberBand.show()
        elif event.button() == Qt.MouseButton.RightButton:
            if self.turret_system.state.no_go_zones:
                self.turret_system.state.no_go_zones.pop()
                self.turret_system.logger.log("Son yasak alan temizlendi.", "INFO")

    def mouseMoveEvent(self, event):
        if not self.origin.isNull() and self.rubberBand:
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rubberBand:
            rect = self.rubberBand.geometry()
            if rect.width() > 10 and rect.height() > 10:
                self.turret_system.state.no_go_zones.append((rect, self.current_zone_type))
                self.turret_system.logger.log(f"Yeni {self.current_zone_type.name} Alanı Eklendi.", "WARNING")
            self.rubberBand.hide()

class MainWindow(QMainWindow):
    def __init__(self, turret_system):
        super().__init__()
        self.turret_system = turret_system
        self.setWindowTitle("ALTAIR TACTICAL INTERFACE - [CINEMATIC 8K HUD]")
        self.setMinimumSize(1280, 800)
        
        # Cyberpunk / Cinematic Askeri Stil tanımlamaları
        self.setStyleSheet("""
            QMainWindow { background-color: #050b14; }
            QGroupBox {
                border: 1px solid #102a43; border-radius: 6px; margin-top: 2ex;
                background-color: rgba(10, 20, 35, 0.8); color: #00ffcc; font-weight: 900;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 5px; color: #00ffcc; }
            QPushButton {
                background-color: rgba(15, 30, 50, 0.9); border: 1px solid #00ffcc; color: #00ffcc;
                padding: 10px; border-radius: 4px; font-weight: bold; letter-spacing: 1px;
            }
            QPushButton:hover { background-color: #00ffcc; color: #000; }
            QPushButton:checked { background-color: #00ffcc; color: #000; }
            QListWidget { background-color: rgba(5, 10, 20, 0.9); color: #22c55e; font-family: 'Consolas'; font-size: 11px; border: 1px solid #102a43; }
            QLabel { color: #829ab1; font-family: 'Segoe UI'; font-weight: 600; }
            QRadioButton { color: #00ffcc; font-weight: bold; }
        """)

        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # --- SOL PANEL ---
        left_layout = QVBoxLayout()
        self.header = QLabel("ALTAIR | COMMAND AND CONTROL - LIVE FEED")
        self.header.setStyleSheet("color: #00ffcc; font-size: 20px; font-weight: 900; letter-spacing: 2px;")
        left_layout.addWidget(self.header)
        
        self.video_label = VideoLabel(self.turret_system)
        self.video_label.setFixedSize(640, 480)
        left_layout.addWidget(self.video_label)

        # Yasak Alan Tipi Seçimi
        zone_sel_group = QGroupBox("YASAK ALAN ÇİZİM TİPİ")
        zone_sel_layout = QHBoxLayout(zone_sel_group)
        self.rb_move = QRadioButton("Harekete Yasak (Kırmızı)")
        self.rb_fire = QRadioButton("Atışa Yasak (Mavi)")
        self.rb_move.setChecked(True)
        self.rb_move.toggled.connect(lambda: self.video_label.set_zone_type(ZoneType.NO_MOVEMENT))
        self.rb_fire.toggled.connect(lambda: self.video_label.set_zone_type(ZoneType.NO_FIRE))
        zone_sel_layout.addWidget(self.rb_move)
        zone_sel_layout.addWidget(self.rb_fire)
        left_layout.addWidget(zone_sel_group)
        
        left_layout.addStretch()
        main_layout.addLayout(left_layout, stretch=2)

        # --- SAĞ PANEL ---
        right_layout = QVBoxLayout()
        
        # 1. Sistem Aşaması
        stage_group = QGroupBox("GÖREV AŞAMASI (STAGE MGMT)")
        stage_layout = QHBoxLayout(stage_group)
        self.stage_btns = QButtonGroup()
        for i in range(1, 4):
            btn = QPushButton(f"PHASE-{i}")
            btn.setCheckable(True)
            if i == 1: btn.setChecked(True)
            btn.clicked.connect(lambda checked, s=i: self.turret_system.set_stage(s))
            self.stage_btns.addButton(btn)
            stage_layout.addWidget(btn)
        right_layout.addWidget(stage_group)

        # 2. Telemetri ve Gecikme
        tele_group = QGroupBox("SYSTEM HEALTH & TELEMETRY")
        tele_layout = QGridLayout(tele_group)
        self.lbl_coords = QLabel("COORD: P:0.0 T:0.0")
        self.lbl_latency = QLabel("LATENCY: 0ms")
        self.lbl_watchdog = QLabel("WATCHDOG: OK")
        
        # Dijital font ve parlaklık
        font_style = "font-family: 'Consolas'; font-size: 14px; font-weight: bold; color: #00ffcc;"
        self.lbl_coords.setStyleSheet(font_style)
        self.lbl_latency.setStyleSheet("font-family: 'Consolas'; font-size: 14px; font-weight: bold; color: #22c55e;")
        self.lbl_watchdog.setStyleSheet("font-family: 'Consolas'; font-size: 14px; font-weight: bold; color: #22c55e;")
        
        tele_layout.addWidget(self.lbl_coords, 0, 0)
        tele_layout.addWidget(self.lbl_latency, 0, 1)
        tele_layout.addWidget(self.lbl_watchdog, 1, 0)
        right_layout.addWidget(tele_group)

        # 3. Kontroller
        ctrl_group = QGroupBox("TACTICAL OVERRIDE")
        ctrl_layout = QGridLayout(ctrl_group)
        self.btn_fire = QPushButton("MANUAL FIRE [AUTHORIZED]")
        self.btn_fire.setStyleSheet("""
            QPushButton { background-color: rgba(60, 10, 10, 0.9); border: 2px solid #ff3333; color: #ff3333; font-size: 14px; }
            QPushButton:hover { background-color: #ff3333; color: #ffffff; }
        """)
        self.btn_fire.clicked.connect(self.turret_system.manual_fire)
        ctrl_layout.addWidget(self.btn_fire, 0, 0)
        right_layout.addWidget(ctrl_group)

        # 4. Logs
        self.log_list = QListWidget()
        right_layout.addWidget(self.log_list)

        # 5. E-STOP
        self.btn_estop = QPushButton("EMERGENCY STOP (E-STOP)")
        self.btn_estop.setStyleSheet("""
            QPushButton {
                background-color: #ff0000; color: #000; padding: 20px; font-size: 18px; font-weight: 900;
                border: 3px solid #880000; border-radius: 6px; letter-spacing: 2px;
            }
            QPushButton:hover { background-color: #cc0000; color: #fff; }
        """)
        self.btn_estop.clicked.connect(self.handle_estop)
        right_layout.addWidget(self.btn_estop)

        main_layout.addLayout(right_layout, stretch=1)
        self.setCentralWidget(central_widget)
        
        self.turret_system.logger.log_emitted.connect(self.add_log)
        
        # Watchdog Checker Timer
        self.wd_timer = QTimer()
        self.wd_timer.timeout.connect(self.check_system_health)
        self.wd_timer.start(500)

    def update_frame(self, qt_img, latency):
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))
        self.lbl_latency.setText(f"LATENCY: {latency:.1f}ms")
        if latency > 50: self.lbl_latency.setStyleSheet("font-family: 'Consolas'; font-size: 14px; font-weight: bold; color: #ff3333;")
        else: self.lbl_latency.setStyleSheet("font-family: 'Consolas'; font-size: 14px; font-weight: bold; color: #22c55e;")

    def handle_target(self, t_class, t_id, distance, cx, cy, w, h, no_fire, no_move):
        # Hareket Filtreleme
        if not no_move:
            # Otomatik takip simülasyonu
            target_p = self.turret_system.state.pan + (cx + w/2 - 320) * 0.05
            target_t = self.turret_system.state.tilt - (cy + h/2 - 240) * 0.05
            # Filtreden geçir
            self.turret_system.state.pan, self.turret_system.state.tilt = \
                self.turret_system.apply_movement_filter(target_p, target_t)
        
        # Otonom Ateşleme (Sadece Aşama 3 ve No-Fire değilse)
        if self.turret_system.state.current_stage == 3 and not no_fire:
            self.turret_system.autonomous_fire(t_class, t_id, distance)
            
        self.lbl_coords.setText(f"COORD: P:{self.turret_system.state.pan:.1f} T:{self.turret_system.state.tilt:.1f}")

    def check_system_health(self):
        is_ok = self.turret_system.check_watchdog()
        if not is_ok:
            self.lbl_watchdog.setText("WATCHDOG: ERROR")
            self.lbl_watchdog.setStyleSheet("color: #ef4444;")
        else:
            self.lbl_watchdog.setText("WATCHDOG: OK")
            self.lbl_watchdog.setStyleSheet("color: #22c55e;")

    def handle_estop(self):
        if self.turret_system.state.e_stop_active:
            self.turret_system.reset_e_stop()
            self.btn_estop.setText("ACİL DURDURMA (E-STOP)")
            self.btn_estop.setStyleSheet("background-color: #dc2626; color: white; padding: 15px;")
        else:
            self.turret_system.trigger_e_stop()
            self.btn_estop.setText("SİSTEM KİLİTLİ")
            self.btn_estop.setStyleSheet("background-color: #111; color: #ef4444; border: 2px solid #ef4444;")

    def add_log(self, msg):
        self.log_list.addItem(msg)
        self.log_list.scrollToBottom()
