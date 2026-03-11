import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QImage
import time
from turret_system import ZoneType

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(QImage, float) # Image, Latency
    # Signal: target_class, target_id, distance, cx, cy, w, h, in_nogo_fire, in_nogo_move
    target_detected_signal = pyqtSignal(str, int, float, int, int, int, int, bool, bool)

    def __init__(self, turret_system):
        super().__init__()
        self._run_flag = True
        self.turret_system = turret_system
        self.mock_targets = []
        self._init_mock_targets()

    def _init_mock_targets(self):
        self.mock_targets = [
            {"id": 1, "class": "İHA", "x": 100, "y": 100, "w": 40, "h": 40, "dx": 3, "dy": 2, "dist": 40.0, "type": "enemy"},
            {"id": 2, "class": "F16-JET", "x": 400, "y": 300, "w": 60, "h": 30, "dx": -4, "dy": -1.5, "dist": 25.0, "type": "enemy"},
            {"id": 3, "class": "DOST-İHA", "x": 50, "y": 350, "w": 45, "h": 25, "dx": 2, "dy": -2, "dist": 60.0, "type": "friendly"}
        ]

    def run(self):
        cap = cv2.VideoCapture(0)
        use_camera = cap.isOpened()

        while self._run_flag:
            start_time = time.time()
            ret = False
            if use_camera:
                ret, cv_img = cap.read()
            
            if not ret:
                cv_img = np.zeros((480, 640, 3), dtype=np.uint8)
                cv_img[:] = (15, 20, 15)
                for i in range(0, 640, 40): cv2.line(cv_img, (i, 0), (i, 480), (25, 30, 25), 1)
                for i in range(0, 480, 40): cv2.line(cv_img, (0, i), (640, i), (25, 30, 25), 1)
            else:
                cv_img = cv2.resize(cv_img, (640, 480))
            
            self._update_mock_targets(cv_img.shape[1], cv_img.shape[0])
            self._draw_hud(cv_img)

            qt_img = self.convert_cv_qt(cv_img)
            
            # Gecikme hesapla (Şartname: < 50ms)
            latency = (time.time() - start_time) * 1000
            self.change_pixmap_signal.emit(qt_img, latency)

            # Watchdog heartbeat
            self.turret_system.update_watchdog()

            time.sleep(max(0, 0.033 - (time.time() - start_time)))

        if use_camera: cap.release()

    def _update_mock_targets(self, width, height):
        for t in self.mock_targets:
            t["x"] += t["dx"]
            t["y"] += t["dy"]
            t["dist"] -= 0.1
            if t["dist"] < 5.0: t["dist"] = 40.0
            if t["x"] < 0 or t["x"] + t["w"] > width: t["dx"] *= -1
            if t["y"] < 0 or t["y"] + t["h"] > height: t["dy"] *= -1

            # Yasak alan kontrolleri
            no_fire, no_move = self.turret_system.check_zones(t["x"], t["y"], t["w"], t["h"])
            
            if self.turret_system.state.is_tracking:
                self.target_detected_signal.emit(
                    t["class"], t["id"], t["dist"], 
                    int(t["x"]), int(t["y"]), t["w"], t["h"],
                    no_fire, no_move
                )

    def _draw_hud(self, cv_img):
        h, w, ch = cv_img.shape
        cx, cy = w // 2, h // 2

        # 1. Sinematik Arka Plan Maskesi (Vignette & Grid)
        overlay = cv_img.copy()
        for i in range(0, w, 60): cv2.line(overlay, (i, 0), (i, h), (10, 40, 10), 1)
        for i in range(0, h, 60): cv2.line(overlay, (0, i), (w, i), (10, 40, 10), 1)
        cv_img = cv2.addWeighted(overlay, 0.4, cv_img, 0.6, 0)

        # 2. Yasak Alanlar
        for zone, z_type in self.turret_system.state.no_go_zones:
            color = (0, 0, 255) if z_type == ZoneType.NO_MOVEMENT else (255, 0, 0)
            label = "NO-MOVE ZONE" if z_type == ZoneType.NO_MOVEMENT else "NO-FIRE ZONE"
            
            # Yarı saydam yasak alan doldurma
            blk = np.zeros(cv_img.shape, np.uint8)
            cv2.rectangle(blk, (zone.x(), zone.y()), (zone.x() + zone.width(), zone.y() + zone.height()), color, cv2.FILLED)
            cv_img = cv2.addWeighted(cv_img, 1.0, blk, 0.2, 1)
            
            cv2.rectangle(cv_img, (zone.x(), zone.y()), (zone.x() + zone.width(), zone.y() + zone.height()), color, 2)
            cv2.putText(cv_img, label, (zone.x() + 5, zone.y() + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

        # 3. Hedefler (DANGER / FRIENDLY Vurgusu)
        for t in self.mock_targets:
            tx, ty, tw, th = int(t["x"]), int(t["y"]), t["w"], t["h"]
            no_fire, no_move = self.turret_system.check_zones(tx, ty, tw, th)
            
            is_friendly = t.get("type") == "friendly"
            
            # Renk belirleme
            if is_friendly:
                color = (255, 144, 30) # Açık Mavi (BGR)
                hud_label = f"FRIENDLY [{t['class']}]"
                alert = "SAFE"
            else:
                color = (0, 0, 255) if t['dist'] < 20 else (0, 255, 255) # Çok yakınsa tam Kırmızı, değilse Sarı
                hud_label = f"TGT-{t['id']} [{t['class']}]"
                alert = "DANGER" if t['dist'] < 20 else "TRACKING"
                
            if no_move: color = (100, 100, 100) # Gridlendirilmiş gri ton

            # Köşe çerçeveleri oluşturma (Modern HUD stili)
            length = 15
            cv2.line(cv_img, (tx, ty), (tx + length, ty), color, 2)
            cv2.line(cv_img, (tx, ty), (tx, ty + length), color, 2)
            cv2.line(cv_img, (tx + tw, ty), (tx + tw - length, ty), color, 2)
            cv2.line(cv_img, (tx + tw, ty), (tx + tw, ty + length), color, 2)
            cv2.line(cv_img, (tx, ty + th), (tx, ty + th - length), color, 2)
            cv2.line(cv_img, (tx, ty + th), (tx + length, ty + th), color, 2)
            cv2.line(cv_img, (tx + tw, ty + th), (tx + tw, ty + th - length), color, 2)
            cv2.line(cv_img, (tx + tw, ty + th), (tx + tw - length, ty + th), color, 2)
            
            # Mesafe ve Bilgi etiketleri
            cv2.putText(cv_img, hud_label, (tx, ty - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
            cv2.putText(cv_img, f"DIST: {t['dist']:.1f}m", (tx, ty - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
            cv2.putText(cv_img, alert, (tx, ty + th + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)

        # 4. Gelişmiş Crosshair & Açı Ölçer Vizörü
        cv2.circle(cv_img, (cx, cy), 40, (0, 255, 0), 1, cv2.LINE_AA)
        cv2.circle(cv_img, (cx, cy), 3, (0, 255, 0), -1)
        
        cv2.line(cv_img, (cx - 60, cy), (cx - 20, cy), (0, 255, 0), 2)
        cv2.line(cv_img, (cx + 20, cy), (cx + 60, cy), (0, 255, 0), 2)
        cv2.line(cv_img, (cx, cy - 60), (cx, cy - 20), (0, 255, 0), 2)
        cv2.line(cv_img, (cx, cy + 20), (cx, cy + 60), (0, 255, 0), 2)

        # Telemetri HUD
        cv2.putText(cv_img, f"MODE: {'AUTONOMOUS' if self.turret_system.state.current_stage == 3 else 'MANUAL/TRACK'}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
        
    def convert_cv_qt(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        return QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

    def stop(self):
        self._run_flag = False
        self.wait()

    def convert_cv_qt(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        # QImage oluştur
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        # Görüntüyü boyuta göre scale et
        return convert_to_Qt_format

    def stop(self):
        self._run_flag = False
        self.wait()
