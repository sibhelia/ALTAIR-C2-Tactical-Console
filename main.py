import sys
from PyQt6.QtWidgets import QApplication
from logger import SystemLogger
from turret_system import TurretSystem
from video_thread import VideoThread
from ui_main import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    logger = SystemLogger()
    turret_system = TurretSystem(logger)
    window = MainWindow(turret_system)
    
    video_thread = VideoThread(turret_system)
    
    # Yeni Sinyal Bağlantıları
    video_thread.change_pixmap_signal.connect(window.update_frame)
    video_thread.target_detected_signal.connect(window.handle_target)
    
    video_thread.start()
    
    logger.log("ALTAIR-C2 Mimari v2.0 Başlatıldı.", "SYSTEM")
    logger.log("Haberleşme: ASENKRON (Hedef < 50ms Gecikme)", "INFO")
    
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
