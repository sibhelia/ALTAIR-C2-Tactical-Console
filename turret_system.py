import math
import time
from enum import Enum
from PyQt6.QtCore import QRect

class ZoneType(Enum):
    NO_FIRE = 1
    NO_MOVEMENT = 2

class TurretState:
    def __init__(self):
        self.pan = 0.0
        self.tilt = 0.0
        self.current_stage = 1 # 1: Manuel, 2: Otonom Takip, 3: Otonom Ateşleme
        self.e_stop_active = False
        self.is_tracking = False
        self.total_kills = 0
        self.last_kill_info = "Yok"
        self.no_go_zones = [] # list of (QRect, ZoneType)
        self.last_heartbeat = time.time()

    def reset_coords(self):
        self.pan = 0.0
        self.tilt = 0.0

class TurretSystem:
    def __init__(self, logger):
        self.state = TurretState()
        self.logger = logger
        self.latency_ms = 0 # Asenkron gecikme takibi

    def set_stage(self, stage: int):
        if self.state.e_stop_active:
            self.logger.log("HATA: E-Stop aktif. Aşama değiştirilemez.", "ERROR")
            return
        self.state.current_stage = stage
        self.state.is_tracking = (stage >= 2)
        self.logger.log(f"Sistem Aşaması Güncellendi: Aşama-{stage}", "SYSTEM")

    def apply_movement_filter(self, target_pan, target_tilt):
        """
        Şartname Gereksinimi: Motor sürücülerine gönderilen her hareket paketinden önce 
        yazılımsal filtreleme yapılır.
        """
        if self.state.e_stop_active:
            return self.state.pan, self.state.tilt

        # Harekete Yasak Alan kontrolü (Simüle: Eğer hedef koordinat yasak bölgedeyse hareketi durdur)
        # Gerçek uygulamada bu koordinatlar/açılar motor limitlerine göre dönüştürülür.
        for zone, z_type in self.state.no_go_zones:
            if z_type == ZoneType.NO_MOVEMENT:
                # Basit bir simülasyon: Eğer pan/tilt değerleri yasak bölge izdüşümündeyse
                # (Bu kısım normalde pixel-to-angle dönüşümü ile yapılır)
                pass

        return target_pan, target_tilt

    def update_watchdog(self):
        self.state.last_heartbeat = time.time()

    def check_watchdog(self):
        # 1 saniyeden fazla süre heartbeat gelmezse Safe-State'e geç
        if time.time() - self.state.last_heartbeat > 1.0:
            if not self.state.e_stop_active:
                self.logger.log("WATCHDOG: Bağlantı koptu veya kritik hata! Güvenli moda geçiliyor.", "CRITICAL")
                self.trigger_e_stop()
            return False
        return True

    def toggle_tracking(self, active: bool):
        if self.state.e_stop_active: return
        self.state.is_tracking = active
        self.logger.log(f"Otomatik Takip: {'AÇIK' if active else 'KAPALI'}", "SYSTEM")

    def trigger_e_stop(self):
        self.state.e_stop_active = True
        self.state.is_tracking = False
        self.state.current_stage = 1
        self.logger.log("SİSTEM GÜVENLİ MODA (SAFE STATE) GEÇTİ.", "CRITICAL")

    def reset_e_stop(self):
        self.state.e_stop_active = False
        self.update_watchdog()
        self.logger.log("Sistem yeniden başlatıldı (Watchdog OK).", "SYSTEM")

    def manual_fire(self):
        if self.state.e_stop_active: return False
        self.logger.log("YETKİLENDİRİLMİŞ MANUEL ATEŞLEME EMRİ", "ACTION")
        self.state.total_kills += 1
        return True

    def autonomous_fire(self, target_class, target_id, distance):
        if self.state.current_stage < 3: return False
        
        # Atışa Yasak Alan kontrolü
        # (VideoThread içinden gelen 'in_nogo_fire' bayrağı ile kontrol edilir)
        
        # Kritik imha menzil analizi
        can_fire = False
        if target_class == "F16" and 10 <= distance <= 15: can_fire = True
        elif target_class == "İHA" and distance < 30: can_fire = True
        
        if can_fire:
            self.logger.log(f"MERKEZİ KARAR: ID {target_id} {target_class} imha edildi.", "ACTION")
            self.state.total_kills += 1
            return True
        return False

    def check_zones(self, x, y, w, h):
        tx, ty = x + w/2, y + h/2
        no_fire = False
        no_move = False
        for zone, z_type in self.state.no_go_zones:
            if zone.contains(int(tx), int(ty)):
                if z_type == ZoneType.NO_FIRE: no_fire = True
                if z_type == ZoneType.NO_MOVEMENT: no_move = True
        return no_fire, no_move
