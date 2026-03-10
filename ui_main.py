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
        self.setWindowTitle("ALTAIR-C2 TACTICAL CONSOLE (v2.0)")
        self.setMinimumSize(1100, 800)
        
        # Stil tanımlamaları
        self.setStyleSheet("""
            QMainWindow { background-color: #0a0a0a; }
            QGroupBox {
                border: 1px solid #333; border-radius: 4px; margin-top: 2ex;
                background-color: #111; color: #22c55e; font-weight: bold;
            }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 3px; }
            QPushButton {
                background-color: #1f2937; border: 1px solid #22c55e; color: #22c55e;
                padding: 8px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #22c55e; color: #000; }
            QListWidget { background-color: #050505; color: #22c55e; font-family: 'Consolas'; font-size: 10px; }
            QLabel { color: #e5e7eb; }
            QRadioButton { color: #22c55e; font-weight: bold; }
        """)

        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        
        # --- SOL PANEL ---
        left_layout = QVBoxLayout()
        self.header = QLabel("ALTAIR-C2 | MERKEZİ KARAR VE OPERASYON PANELİ")
        self.header.setStyleSheet("color: #22c55e; font-size: 18px; font-weight: 800;")
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
        
        # 1. Sistem Aşaması (Dynamic Stage Management)
        stage_group = QGroupBox("GÖREV AŞAMASI (ŞARTNAME MADDE 6)")
        stage_layout = QHBoxLayout(stage_group)
        self.stage_btns = QButtonGroup()
        for i in range(1, 4):
            btn = QPushButton(f"AŞAMA-{i}")
            btn.setCheckable(True)
            if i == 1: btn.setChecked(True)
            btn.clicked.connect(lambda checked, s=i: self.turret_system.set_stage(s))
            self.stage_btns.addButton(btn)
            stage_layout.addWidget(btn)
        right_layout.addWidget(stage_group)

        # 2. Telemetri ve Gecikme
        tele_group = QGroupBox("SİSTEM DURUMU")
        tele_layout = QGridLayout(tele_group)
        self.lbl_coords = QLabel("COORD: P:0.0 T:0.0")
        self.lbl_latency = QLabel("LATENCY: 0ms")
        self.lbl_watchdog = QLabel("WATCHDOG: OK")
        self.lbl_coords.setStyleSheet("font-family: monospace; color: #22c55e;")
        self.lbl_latency.setStyleSheet("font-family: monospace;")
        tele_layout.addWidget(self.lbl_coords, 0, 0)
        tele_layout.addWidget(self.lbl_latency, 0, 1)
        tele_layout.addWidget(self.lbl_watchdog, 1, 0)
        right_layout.addWidget(tele_group)

        # 3. Kontroller
        ctrl_group = QGroupBox("OPERASYONEL KONTROLLER")
        ctrl_layout = QGridLayout(ctrl_group)
        self.btn_fire = QPushButton("MANUEL ATEŞLEME")
        self.btn_fire.setStyleSheet("background-color: #450a0a; color: #ef4444; border: 1px solid #ef4444;")
        self.btn_fire.clicked.connect(self.turret_system.manual_fire)
        ctrl_layout.addWidget(self.btn_fire, 0, 0)
        right_layout.addWidget(ctrl_group)

        # 4. Logs
        self.log_list = QListWidget()
        right_layout.addWidget(self.log_list)

        # 5. E-STOP
        self.btn_estop = QPushButton("ACİL DURDURMA (E-STOP)")
        self.btn_estop.setStyleSheet("background-color: #dc2626; color: white; padding: 15px;")
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
        if latency > 50: self.lbl_latency.setStyleSheet("color: #ef4444;")
        else: self.lbl_latency.setStyleSheet("color: #22c55e;")

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
