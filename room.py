import random
import pygame

from enemies import Goblin, RangedSlime, Bat, BossGolem
from weapons import WeaponInstance


DIRS = {
    "N": (0, -1),
    "S": (0, 1),
    "W": (-1, 0),
    "E": (1, 0),
}


class Room:
    def __init__(self, gx, gy, rtype="enemy"):
        self.gx = gx
        self.gy = gy
        self.rtype = rtype
        self.explored = False
        self.cleared = rtype in ("start", "shop")
        self.spawned = False
        self.enemies = []
        self.enemy_projectiles = []
        self.drops = []
        self.weapon_pickups = []
        self.breakables = []
        self.chest = None
        self.neighbors = set()

    def spawn_contents(self, floor_level):
        if self.spawned:
            return
        self.spawned = True

        if self.rtype == "enemy":
            count = random.randint(4, 6 + floor_level)
            for _ in range(count):
                x = random.randint(180, 780)
                y = random.randint(140, 520)
                t = random.choice(["goblin", "slime", "bat"])
                if t == "goblin":
                    self.enemies.append(Goblin(x, y, floor_level))
                elif t == "slime":
                    self.enemies.append(RangedSlime(x, y, floor_level))
                else:
                    self.enemies.append(Bat(x, y, floor_level))
            if random.random() < 0.10:
                self.chest = {"rarity": "rare" if random.random() < 0.05 else "common", "opened": False, "x": 480, "y": 320}
            for _ in range(random.randint(1, 4)):
                self.breakables.append({"x": random.randint(150, 810), "y": random.randint(130, 530), "hp": 18})
        elif self.rtype == "boss":
            self.enemies.append(BossGolem(480, 320, floor_level))
        elif self.rtype == "shop":
            self.shop_items = [
                {"type": "heal", "price": 20, "x": 380, "y": 300},
                {"type": "weapon", "price": 30, "x": 480, "y": 300, "name": random.choice(["Shotgun", "Machine Gun", "Pistol"])},
                {"type": "weapon", "price": 45, "x": 580, "y": 300, "name": random.choice(["Rocket Launcher", "Laser Rifle"])},
            ]

    def is_combat_cleared(self):
        if self.rtype in ("start", "shop"):
            return True
        return len([e for e in self.enemies if e.alive]) == 0


class FloorMap:
    def __init__(self, floor_num):
        self.floor_num = floor_num
        self.rooms = {}
        self.current = (0, 0)
        self._generate()

    def _add_room(self, pos, rtype):
        self.rooms[pos] = Room(pos[0], pos[1], rtype)

    def _link_neighbors(self):
        for (x, y), room in self.rooms.items():
            for d, (dx, dy) in DIRS.items():
                if (x + dx, y + dy) in self.rooms:
                    room.neighbors.add(d)

    def _generate(self):
        start_type = "start" if self.floor_num == 1 else "shop"
        self._add_room((0, 0), start_type)
        x, y = 0, 0
        for i in range(3):
            x += 1
            self._add_room((x, y), "enemy")
        x += 1
        self._add_room((x, y), "boss")
        self.boss_pos = (x, y)
        self._add_room((0, 1), "shop")
        self._link_neighbors()

    def current_room(self):
        return self.rooms[self.current]

    def total_cleared_enemy_rooms(self):
        return sum(1 for r in self.rooms.values() if r.rtype == "enemy" and r.cleared)

    def move_room(self, direction):
        dx, dy = DIRS[direction]
        nxt = (self.current[0] + dx, self.current[1] + dy)
        if nxt in self.rooms:
            self.current = nxt
            return True
        return False


def blocked_door_rects(room, bounds):
    if room.is_combat_cleared():
        room.cleared = True
        return []
    door_w = 120
    thick = 14
    x, y, w, h = bounds
    out = []
    if "N" in room.neighbors:
        out.append(pygame.Rect(x + w // 2 - door_w // 2, y - 2, door_w, thick))
    if "S" in room.neighbors:
        out.append(pygame.Rect(x + w // 2 - door_w // 2, y + h - thick + 2, door_w, thick))
    if "W" in room.neighbors:
        out.append(pygame.Rect(x - 2, y + h // 2 - door_w // 2, thick, door_w))
    if "E" in room.neighbors:
        out.append(pygame.Rect(x + w - thick + 2, y + h // 2 - door_w // 2, thick, door_w))
    return out


def roll_minion_drop(x, y):
    r = random.random()
    out = []
    if r < 0.05:
        out.append({"type": "health_orb", "x": x, "y": y, "value": 20})
    elif r < 0.10:
        out.append({"type": "mana_orb", "x": x, "y": y})
    if random.random() < 0.30:
        out.append({"type": "coins", "x": x + 8, "y": y + 3, "value": random.randint(1, 5)})
    return out


def roll_boss_drop(x, y):
    out = [
        {"type": "coins", "x": x, "y": y, "value": 50},
        {"type": "key", "x": x + 18, "y": y},
    ]
    if random.random() < 0.50:
        out.append({"type": "weapon", "x": x - 22, "y": y, "weapon": WeaponInstance(random.choice(["Rocket Launcher", "Laser Rifle"]))})
    if random.random() < 0.10:
        out.append({"type": "legendary", "x": x, "y": y + 20, "bonus": random.choice(["damage_boost", "speed_boost"])})
    return out
