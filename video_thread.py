import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QImage
import time

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(QImage)
    # Sinxal: target_class, target_id, distance, cx, cy, w, h
    target_detected_signal = pyqtSignal(str, int, float, int, int, int, int)

    def __init__(self, turret_system):
        super().__init__()
        self._run_flag = True
        self.turret_system = turret_system
        self.mock_targets = []
        self._init_mock_targets()

    def _init_mock_targets(self):
        # ID, class, x, y, w, h, dx, dy, distance
        self.mock_targets = [
            {"id": 1, "class": "İHA", "x": 100, "y": 100, "w": 40, "h": 40, "dx": 3, "dy": 2, "dist": 40.0},
            {"id": 2, "class": "F16", "x": 400, "y": 300, "w": 60, "h": 30, "dx": -4, "dy": -1.5, "dist": 25.0}
        ]

    def run(self):
        # OpenCV ile kamera deneyelim
        cap = cv2.VideoCapture(0)
        use_camera = True
        if not cap.isOpened():
            use_camera = False

        while self._run_flag:
            ret = False
            if use_camera:
                ret, cv_img = cap.read()
            
            if not ret:
                # Mock frame (askeri karanlık arka plan)
                cv_img = np.zeros((480, 640, 3), dtype=np.uint8)
                cv_img[:] = (20, 25, 20)
                
                # Izgara (Grid) çizimi
                for i in range(0, 640, 40):
                    cv2.line(cv_img, (i, 0), (i, 480), (30, 40, 30), 1)
                for i in range(0, 480, 40):
                    cv2.line(cv_img, (0, i), (640, i), (30, 40, 30), 1)
            else:
                cv_img = cv2.resize(cv_img, (640, 480))
            
            # Hedefleri güncelle
            self._update_mock_targets(cv_img.shape[1], cv_img.shape[0])

            # HUD ve tespit maskeleri çiz
            self._draw_hud(cv_img)

            # Qt'ye dönüştür ve sinyal fırlat
            qt_img = self.convert_cv_qt(cv_img)
            self.change_pixmap_signal.emit(qt_img)

            # ~30 FPS
            time.sleep(0.033)

        if use_camera:
            cap.release()

    def _update_mock_targets(self, width, height):
        for t in self.mock_targets:
            t["x"] += t["dx"]
            t["y"] += t["dy"]
            t["dist"] -= 0.15 # Hedef yaklaşıyor simülasyonu
            if t["dist"] < 8.0: 
                t["dist"] = 40.0 # Yeniden uzaklaşsın (respawn)

            # Kenarlardan sekme
            if t["x"] < 0 or t["x"] + t["w"] > width:
                t["dx"] *= -1
            if t["y"] < 0 or t["y"] + t["h"] > height:
                t["dy"] *= -1

            # Takip ve Otonom ateşleme kuralları için UI ipliğine/Turret Sisteme sinyal
            if self.turret_system.state.is_tracking:
                self.target_detected_signal.emit(
                    t["class"], t["id"], t["dist"], 
                    int(t["x"]), int(t["y"]), t["w"], t["h"]
                )

    def _draw_hud(self, cv_img):
        h, w, ch = cv_img.shape
        cx, cy = w // 2, h // 2

        # 1. Yasak Alanların Çizilmesi
        for zone in self.turret_system.state.no_go_zones:
            cv2.rectangle(cv_img, (zone.x(), zone.y()), 
                          (zone.x() + zone.width(), zone.y() + zone.height()), 
                          (0, 0, 255), 2)
            cv2.putText(cv_img, "YASAK ALAN", (zone.x(), zone.y() - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # 2. Hedeflerin Çizilmesi
        for t in self.mock_targets:
            tx, ty, tw, th = int(t["x"]), int(t["y"]), t["w"], t["h"]
            
            in_nogo = self.turret_system.check_no_go_zones(tx, ty, tw, th)
            color = (0, 255, 255) # Sarı (Tespit)
            if in_nogo:
                color = (0, 0, 255) # Kırmızı (Yasak alan)
            elif self.turret_system.state.is_tracking:
                color = (0, 165, 255) # Turuncu (Takipte)

            # Bounding box
            cv2.rectangle(cv_img, (tx, ty), (tx + tw, ty + th), color, 2)
            
            # Hedef Bilgisi
            info = f"ID:{t['id']} {t['class']} D:{t['dist']:.1f}m"
            cv2.putText(cv_img, info, (tx, ty - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Merkezden hedefe izleme çizgisi çiz (Eğer takipte ve yasak alanda değilse)
            if self.turret_system.state.is_tracking and not in_nogo:
                tcx, tcy = tx + tw // 2, ty + th // 2
                cv2.line(cv_img, (cx, cy), (tcx, tcy), (0, 200, 0), 1)

        # 3. Taret Merkez Artı (Crosshair) Çizimi
        cv2.line(cv_img, (cx - 25, cy), (cx + 25, cy), (0, 255, 0), 2)
        cv2.line(cv_img, (cx, cy - 25), (cx, cy + 25), (0, 255, 0), 2)
        cv2.circle(cv_img, (cx, cy), 12, (0, 255, 0), 1)
        
        # 4. Telemetri verilerini basitçe sol alta bas
        pan_tilt_str = f"PAN: {self.turret_system.state.pan:.1f}  TILT: {self.turret_system.state.tilt:.1f}"
        cv2.putText(cv_img, pan_tilt_str, (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

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
