import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QListWidget, QGroupBox, QGridLayout,
    QRubberBand, QFrame
)
from PyQt6.QtCore import Qt, QRect, QPoint, QSize
from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor

class VideoLabel(QLabel):
    """
    Özelleştirilmiş QLabel; fare ile ekrana yasak alan (RubberBand) çizimi yapılmasını sağlar.
    """
    def __init__(self, turret_system, parent=None):
        super().__init__(parent)
        self.turret_system = turret_system
        self.rubberBand = None
        self.origin = QPoint()
        self.setMouseTracking(True)
        # Siyah arkaplan ve askeri bir çerçeve
        self.setStyleSheet("background-color: #0d1117; border: 2px solid #22c55e;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.pos()
            if not self.rubberBand:
                self.rubberBand = QRubberBand(QRubberBand.Shape.Rectangle, self)
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            self.rubberBand.show()
        elif event.button() == Qt.MouseButton.RightButton:
            # Sağ tıkla son çizilen yasak alanı sil
            if self.turret_system.state.no_go_zones:
                self.turret_system.state.no_go_zones.pop()
                self.turret_system.logger.log("Son yasak alan temizlendi.", "INFO")

    def mouseMoveEvent(self, event):
        if not self.origin.isNull() and self.rubberBand:
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rubberBand:
            rect = self.rubberBand.geometry()
            # Ufak veya yanlış tıklamaları es geç
            if rect.width() > 20 and rect.height() > 20:
                self.turret_system.state.no_go_zones.append(rect)
                self.turret_system.logger.log(f"Yeni Yasak Alan Eklendi: ({rect.x()}, {rect.y()}, {rect.width()}x{rect.height()})", "WARNING")
            self.rubberBand.hide()

class MainWindow(QMainWindow):
    def __init__(self, turret_system):
        super().__init__()
        self.turret_system = turret_system
        
        self.setWindowTitle("ALTAIR C2 TACTICAL CONSOLE")
        self.setMinimumSize(1024, 768)
        self.setStyleSheet("""
            QMainWindow { background-color: #0a0a0a; }
            QGroupBox {
                border: 1px solid #333333;
                border-radius: 5px;
                margin-top: 1ex;
                background-color: #111111;
                color: #22c55e;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
                color: #22c55e;
            }
            QPushButton {
                background-color: #1f2937;
                border: 1px solid #22c55e;
                color: #22c55e;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #22c55e;
                color: #000000;
            }
            QListWidget {
                background-color: #050505;
                color: #22c55e;
                border: 1px solid #333333;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
            QLabel {
                color: #f3f4f6;
            }
        """)

        # Ana Widget ve Layout
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        
        # --- Sol Panel (Video Katmanı) ---
        left_layout = QVBoxLayout()
        # Headings
        header = QLabel("HAVA SAVUNMA NİŞANGAH SİSTEMİ - AŞAMA 2/3 OTONOM YETENEKLİ")
        header.setStyleSheet("color: #22c55e; font-size: 16px; font-weight: bold;")
        left_layout.addWidget(header)
        
        # Video
        self.video_label = VideoLabel(self.turret_system)
        self.video_label.setFixedSize(640, 480)
        left_layout.addWidget(self.video_label)
        
        # Bilgi Notu
        info = QLabel("* Yasak alan (No-Go Zone) çizmek için farenin SOL tuşuyla sürükleyiniz. Silmek için SAĞ tıklayınız.")
        info.setStyleSheet("color: #6b7280; font-size: 12px;")
        left_layout.addWidget(info)
        
        left_layout.addStretch()
        main_layout.addLayout(left_layout, stretch=2)

        # --- Sağ Panel (Telemetri ve Kontroller) ---
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)

        # 1. Telemetri Verileri
        telemetry_group = QGroupBox("TELEMETRİ VE İSTATİSTİK")
        telemetry_layout = QGridLayout(telemetry_group)
        
        self.lbl_pan = QLabel("PAN (Yaw): 0.0°")
        self.lbl_tilt = QLabel("TILT (Pitch): 0.0°")
        self.lbl_kills = QLabel("Toplam İmha: 0")
        self.lbl_last_kill = QLabel("Son Hedef: Yok")
        
        # Büyük dijital stil
        digital_style = "color: #22c55e; font-size: 16px; font-weight: bold; font-family: monospace;"
        self.lbl_pan.setStyleSheet(digital_style)
        self.lbl_tilt.setStyleSheet(digital_style)
        self.lbl_kills.setStyleSheet("color: #eab308; font-size: 14px;") # Sarımsı
        self.lbl_last_kill.setStyleSheet("color: #eab308; font-size: 14px;")
        
        telemetry_layout.addWidget(self.lbl_pan, 0, 0)
        telemetry_layout.addWidget(self.lbl_tilt, 0, 1)
        telemetry_layout.addWidget(self.lbl_kills, 1, 0)
        telemetry_layout.addWidget(self.lbl_last_kill, 1, 1)
        right_layout.addWidget(telemetry_group)

        # 2. Sistem Kontrolleri (Butonlar)
        controls_group = QGroupBox("TAKTİK KONTROLLER")
        controls_layout = QGridLayout(controls_group)
        
        self.btn_auto_track = QPushButton("OTOMATİK TAKİP (KAPALI)")
        self.btn_auto_track.setCheckable(True)
        self.btn_auto_track.clicked.connect(self.toggle_tracking)
        
        self.btn_autonomous = QPushButton("OTONOM ATEŞLEME (KAPALI)")
        self.btn_autonomous.setCheckable(True)
        self.btn_autonomous.clicked.connect(self.toggle_autonomous)
        
        self.btn_manual_fire = QPushButton("MANUEL ATEŞLEME")
        self.btn_manual_fire.setStyleSheet("""
            QPushButton { background-color: #7f1d1d; color: white; border: 1px solid #ef4444; }
            QPushButton:hover { background-color: #dc2626; color: white; }
        """)
        self.btn_manual_fire.clicked.connect(self.manual_fire_action)
        
        self.btn_calibrate = QPushButton("KALİBRASYON (SIFIRLA)")
        self.btn_calibrate.clicked.connect(self.calibrate_action)

        controls_layout.addWidget(self.btn_auto_track, 0, 0)
        controls_layout.addWidget(self.btn_autonomous, 0, 1)
        controls_layout.addWidget(self.btn_calibrate, 1, 0)
        controls_layout.addWidget(self.btn_manual_fire, 1, 1)
        right_layout.addWidget(controls_group)

        # 3. Sistem Akışı (Log Paneli)
        log_group = QGroupBox("SİSTEM AKIŞI (LOGS)")
        log_layout = QVBoxLayout(log_group)
        self.log_list = QListWidget()
        log_layout.addWidget(self.log_list)
        right_layout.addWidget(log_group)
        
        # 4. Acil Durdurma (Emergency Stop)
        self.btn_estop = QPushButton("ACİL DURDURMA (E-STOP)")
        self.btn_estop.setStyleSheet("""
            QPushButton {
                background-color: #b91c1c; /* Koyu kırmızı */
                color: #ffffff;
                font-size: 18px;
                font-weight: 900;
                padding: 20px;
                border: 3px solid #7f1d1d;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #ef4444; }
        """)
        self.btn_estop.clicked.connect(self.trigger_estop)
        right_layout.addWidget(self.btn_estop)

        main_layout.addLayout(right_layout, stretch=1)
        self.setCentralWidget(main_widget)
        
        # Logger Sinyalini Bağlama
        self.turret_system.logger.log_emitted.connect(self.add_log_entry)

    # --- UI Slotları (Buton Tıklamaları) ---
    def toggle_tracking(self, checked):
        if self.turret_system.state.e_stop_active:
            self.btn_auto_track.setChecked(False) # E-Stop varken basılamaz
            self.turret_system.toggle_tracking(False)
            return

        state_str = "AÇIK" if checked else "KAPALI"
        self.btn_auto_track.setText(f"OTOMATİK TAKİP ({state_str})")
        if checked:
            self.btn_auto_track.setStyleSheet("background-color: #15803d; color: white;")
        else:
            self.btn_auto_track.setStyleSheet("")
            
        self.turret_system.toggle_tracking(checked)

    def toggle_autonomous(self, checked):
        if self.turret_system.state.e_stop_active:
            self.btn_autonomous.setChecked(False)
            self.turret_system.set_mode(False)
            return

        state_str = "AÇIK" if checked else "KAPALI"
        self.btn_autonomous.setText(f"OTONOM ATEŞLEME ({state_str})")
        if checked:
            self.btn_autonomous.setStyleSheet("background-color: #b45309; color: white; border: 1px solid #f59e0b;")
        else:
            self.btn_autonomous.setStyleSheet("")
            
        self.turret_system.set_mode(checked)

    def manual_fire_action(self):
        fire_success = self.turret_system.manual_fire()
        if fire_success:
            self.update_telemetry_ui()

    def calibrate_action(self):
        self.turret_system.calibrate()
        self.update_telemetry_ui()

    def trigger_estop(self):
        # E-Stop iptal (Toggle) özelliği de eklenebilir veya sadece kilitlenebilir.
        if self.turret_system.state.e_stop_active:
            # Unlock E-Stop
            self.turret_system.reset_e_stop()
            self.btn_estop.setText("ACİL DURDURMA (E-STOP)")
            self.btn_estop.setStyleSheet("""
                QPushButton { background-color: #b91c1c; color: #ffffff; font-size: 18px; font-weight: 900; padding: 20px; border-radius: 8px; }
                QPushButton:hover { background-color: #ef4444; }
            """)
        else:
            # Trigger E-Stop
            self.turret_system.trigger_e_stop()
            self.btn_estop.setText("SİSTEM KİLİTLİ (AÇMAK İÇİN TIKLAYIN)")
            self.btn_estop.setStyleSheet("""
                QPushButton { background-color: #111827; color: #ef4444; font-size: 16px; font-weight: 900; padding: 20px; border: 2px solid #ef4444; border-radius: 8px; }
                QPushButton:hover { background-color: #1f2937; }
            """)
            # Buton durumlarını sıfırla
            self.btn_auto_track.setChecked(False)
            self.btn_auto_track.setText("OTOMATİK TAKİP (KAPALI)")
            self.btn_auto_track.setStyleSheet("")
            self.btn_autonomous.setChecked(False)
            self.btn_autonomous.setText("OTONOM ATEŞLEME (KAPALI)")
            self.btn_autonomous.setStyleSheet("")

    def add_log_entry(self, msg):
        self.log_list.addItem(msg)
        self.log_list.scrollToBottom()

    def update_telemetry_ui(self):
        self.lbl_pan.setText(f"PAN (Yaw): {self.turret_system.state.pan:.1f}°")
        self.lbl_tilt.setText(f"TILT (Pitch): {self.turret_system.state.tilt:.1f}°")
        self.lbl_kills.setText(f"Toplam İmha: {self.turret_system.state.total_kills}")
        self.lbl_last_kill.setText(f"Son Hedef: {self.turret_system.state.last_kill_info}")

    # --- Video ve Algılama Sinyalleri için Slotlar ---
    def update_image(self, qt_img):
        # Görüntüyü QLabel'a bas
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    def handle_target_detected(self, t_class, t_id, distance, cx, cy, w, h):
        # Hedef tespiti yapıldı, takip açık.
        
        # Pan / Tilt hareketini simüle et
        # Hedef merkezin sağına kayıyorsa pan +, yukarı kayıyorsa tilt -
        screen_cx, screen_cy = 320, 240 # 640x480'in yarısı
        tx = cx + w/2
        ty = cy + h/2
        
        # Basit proportional kontrol simülasyonu
        err_x = (tx - screen_cx) * 0.05
        err_y = (ty - screen_cy) * 0.05
        
        self.turret_system.state.pan += err_x
        self.turret_system.state.tilt -= err_y
        
        # Otonom Ateşleme Kontrolü
        if self.turret_system.state.mode == "AUTONOMOUS":
            # Hedef yasak alanda değilse ateş et
            in_nogo = self.turret_system.check_no_go_zones(cx, cy, w, h)
            if not in_nogo:
                fired = self.turret_system.autonomous_fire(t_class, t_id, distance)
            
        self.update_telemetry_ui()
