from PyQt6.QtCore import QObject, pyqtSignal
from datetime import datetime

class SystemLogger(QObject):
    """
    UI ipliğine log mesajlarını sinyalle gönderen loglama sistemi.
    Bu sayede QThread içerisinden güvenle arayüze log yazdırılabilir.
    """
    # Signal that emits the log string
    log_emitted = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def log(self, message: str, level: str = "INFO"):
        now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted_msg = f"[{now}] [{level}] {message}"
        # Emit to UI
        self.log_emitted.emit(formatted_msg)
        # Also print to console for debugging
        print(formatted_msg)
