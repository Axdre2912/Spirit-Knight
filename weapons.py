import math
import random
from dataclasses import dataclass


WEAPON_DEFS = {
    "Pistol": {
        "damage": 16,
        "fire_rate": 4.0,
        "ammo": -1,
        "range": 440,
        "speed": 560,
        "spread": 0,
        "pellets": 1,
        "color": (250, 230, 90),
        "rarity": "common",
    },
    "Shotgun": {
        "damage": 9,
        "fire_rate": 1.4,
        "ammo": 28,
        "range": 280,
        "speed": 500,
        "spread": 20,
        "pellets": 6,
        "color": (255, 180, 100),
        "rarity": "common",
    },
    "Machine Gun": {
        "damage": 7,
        "fire_rate": 10.0,
        "ammo": 90,
        "range": 380,
        "speed": 620,
        "spread": 7,
        "pellets": 1,
        "color": (170, 240, 255),
        "rarity": "common",
    },
    "Rocket Launcher": {
        "damage": 45,
        "fire_rate": 1.0,
        "ammo": 12,
        "range": 460,
        "speed": 380,
        "spread": 0,
        "pellets": 1,
        "color": (255, 110, 90),
        "rarity": "rare",
    },
    "Sword": {
        "damage": 32,
        "fire_rate": 2.3,
        "ammo": -1,
        "range": 74,
        "speed": 0,
        "spread": 65,
        "pellets": 1,
        "color": (220, 220, 230),
        "rarity": "common",
        "melee": True,
    },
    "Laser Rifle": {
        "damage": 18,
        "fire_rate": 7.0,
        "ammo": 80,
        "range": 520,
        "speed": 760,
        "spread": 2,
        "pellets": 1,
        "color": (220, 90, 255),
        "rarity": "rare",
    },
}


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    damage: float
    max_range: float
    color: tuple
    radius: int = 4
    traveled: float = 0.0
    owner: str = "player"
    explosive: bool = False
    slow_effect: float = 0.0

    def update(self, dt):
        dx = self.vx * dt
        dy = self.vy * dt
        self.x += dx
        self.y += dy
        self.traveled += math.hypot(dx, dy)
        return self.traveled < self.max_range


class WeaponInstance:
    def __init__(self, name):
        self.name = name
        self.data = WEAPON_DEFS[name].copy()
        self.max_ammo = self.data["ammo"]
        self.ammo = self.max_ammo
        self.cooldown = 1.0 / max(0.001, self.data["fire_rate"])
        self.next_fire_time = 0.0
        self.melee = self.data.get("melee", False)

    def restore_mana(self):
        self.next_fire_time = 0.0

    def can_fire(self, now):
        has_ammo = self.ammo != 0
        return now >= self.next_fire_time and has_ammo

    def try_fire(self, now, origin, angle, fire_rate_bonus=1.0):
        if not self.can_fire(now):
            return []
        if self.ammo > 0:
            self.ammo -= 1
        self.next_fire_time = now + (self.cooldown / max(0.2, fire_rate_bonus))
        print("pew pew")
        return self.spawn_projectiles(origin, angle)

    def spawn_projectiles(self, origin, angle):
        out = []
        pellet_count = self.data["pellets"]
        spread = self.data["spread"]
        if self.melee:
            return []
        for i in range(pellet_count):
            if pellet_count == 1:
                ang = angle + math.radians(random.uniform(-spread, spread))
            else:
                t = i / max(1, pellet_count - 1)
                centered = (t - 0.5) * 2.0
                ang = angle + math.radians(centered * spread + random.uniform(-1.5, 1.5))
            vx = math.cos(ang) * self.data["speed"]
            vy = math.sin(ang) * self.data["speed"]
            out.append(
                Projectile(
                    x=origin[0],
                    y=origin[1],
                    vx=vx,
                    vy=vy,
                    damage=self.data["damage"],
                    max_range=self.data["range"],
                    color=self.data["color"],
                    explosive=self.name == "Rocket Launcher",
                )
            )
        return out


def random_weapon(common_only=False):
    pool = [k for k, v in WEAPON_DEFS.items() if (v["rarity"] == "common" or not common_only)]
    return WeaponInstance(random.choice(pool))
