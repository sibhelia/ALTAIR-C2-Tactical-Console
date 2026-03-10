import math

class TurretState:
    def __init__(self):
        self.pan = 0.0
        self.tilt = 0.0
        self.mode = "MANUAL" # MANUAL or AUTONOMOUS
        self.e_stop_active = False
        self.is_tracking = False
        self.total_kills = 0
        self.last_kill_info = "Yok"
        self.no_go_zones = [] # list of QRect

    def reset_coords(self):
        self.pan = 0.0
        self.tilt = 0.0

class TurretSystem:
    def __init__(self, logger):
        self.state = TurretState()
        self.logger = logger

    def set_mode(self, autonomous: bool):
        if self.state.e_stop_active:
            self.logger.log("HATA: E-Stop aktif. Mod değiştirilemez.", "ERROR")
            return
        
        self.state.mode = "AUTONOMOUS" if autonomous else "MANUAL"
        self.logger.log(f"Sistem Modu Değiştirildi: {self.state.mode}", "SYSTEM")

    def toggle_tracking(self, active: bool):
        if self.state.e_stop_active:
            self.logger.log("HATA: E-Stop aktif. Takip başlatılamaz.", "ERROR")
            return
        self.state.is_tracking = active
        status = "AÇIK" if active else "KAPALI"
        self.logger.log(f"Otomatik Takip: {status}", "SYSTEM")

    def trigger_e_stop(self):
        self.state.e_stop_active = True
        self.state.is_tracking = False
        self.state.mode = "MANUAL" # Revert to manual for safety
        self.logger.log("ACİL DURDURMA DEVREYE GİRDİ! GÜÇ KESİLDİ.", "CRITICAL")

    def reset_e_stop(self):
        self.state.e_stop_active = False
        self.logger.log("Acil Durdurma iptal edildi. Sistem yeniden başlatılıyor.", "SYSTEM")

    def calibrate(self):
        self.state.reset_coords()
        self.logger.log("Kalibrasyon Yapıldı. Pan: 0.0, Tilt: 0.0", "INFO")

    def manual_fire(self):
        if self.state.e_stop_active:
            self.logger.log("HATA: E-Stop aktif. Ateşleme yapılamaz.", "ERROR")
            return False
        self.logger.log("MANUEL ATEŞLEME EMRİ GÖNDERİLDİ", "ACTION")
        self.state.total_kills += 1
        self.state.last_kill_info = "Manuel Hedef"
        return True

    def evaluate_target(self, target_class, distance):
        if self.state.e_stop_active:
            return False
        
        # Angajman kuralları (Örn: F16 için mesafe 10-15m)
        if target_class == "F16":
            if 10 <= distance <= 15:
                return True
            else:
                return False
        elif target_class == "İHA":
            if distance < 30: 
                return True
            return False
        return False

    def autonomous_fire(self, target_class, target_id, distance):
        if self.state.mode != "AUTONOMOUS":
            return False

        if self.evaluate_target(target_class, distance):
            self.logger.log(f"OTONOM ATEŞLEME: Hedef ID {target_id} sınıf {target_class} kilitlendi ve vuruldu.", "ACTION")
            self.state.total_kills += 1
            self.state.last_kill_info = f"ID:{target_id} {target_class}"
            return True
        else:
            self.logger.log(f"İPTAL: Hedef ID {target_id} sınıf {target_class} angajman menzili dışında (Masafe: {distance}m).", "WARNING")
            return False

    def check_no_go_zones(self, x, y, width, height):
        # Nokta hedefin merkezi alınır
        target_center_x = x + width/2
        target_center_y = y + height/2
        
        for zone in self.state.no_go_zones:
            if zone.contains(int(target_center_x), int(target_center_y)):
                return True
        return False
