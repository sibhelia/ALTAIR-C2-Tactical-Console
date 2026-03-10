import sys
from PyQt6.QtWidgets import QApplication
from logger import SystemLogger
from turret_system import TurretSystem
from video_thread import VideoThread
from ui_main import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Koyu Tema Uygulaması (Global Qt Stil)
    app.setStyle("Fusion")
    
    # 1. Çekirdek Sistemleri Başlat
    logger = SystemLogger()
    turret_system = TurretSystem(logger)
    
    # 2. Ana Arayüzü Başlat
    window = MainWindow(turret_system)
    
    # 3. Video / Görüntü İşleme İş Parçacığını (QThread) Başlat
    video_thread = VideoThread(turret_system)
    
    # Sinyalleri arayüze bağla
    video_thread.change_pixmap_signal.connect(window.update_image)
    video_thread.target_detected_signal.connect(window.handle_target_detected)
    
    # Thread'i çalıştır
    video_thread.start()
    
    # Log Başlangıcı
    logger.log("ALTAIR Taktik Konsolu Başlatıldı.", "SYSTEM")
    logger.log("Video Akışı Bekleniyor...", "INFO")
    
    # Pencereyi göster
    window.show()
    
    # Çıkış işlemi
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
