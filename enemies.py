import math
import random
import pygame

from weapons import Projectile


class Enemy:
    def __init__(self, x, y, hp, speed, damage, color):
        self.x = x
        self.y = y
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.damage = damage
        self.radius = 13
        self.color = color
        self.cooldown = 0
        self.slow_timer = 0.0
        self.affix = random.choice(["none", "none", "fire", "ice"])

    @property
    def alive(self):
        return self.hp > 0

    def take_damage(self, amount):
        self.hp -= amount

    def base_move(self, dt, player, stop_dist=20):
        speed_mult = 0.55 if self.slow_timer > 0 else 1.0
        dx, dy = player.x - self.x, player.y - self.y
        d = max(0.001, math.hypot(dx, dy))
        if d > stop_dist:
            self.x += (dx / d) * self.speed * speed_mult * dt
            self.y += (dy / d) * self.speed * speed_mult * dt
        return d

    def update(self, dt, player, enemy_projectiles):
        self.slow_timer = max(0.0, self.slow_timer - dt)
        self.cooldown = max(0.0, self.cooldown - dt)

    def draw(self, surf, camera):
        pos = (int(self.x + camera[0]), int(self.y + camera[1]))
        pygame.draw.circle(surf, self.color, pos, self.radius)
        if self.affix == "fire":
            pygame.draw.circle(surf, (255, 120, 40), pos, self.radius + 3, 2)
        elif self.affix == "ice":
            pygame.draw.circle(surf, (100, 180, 255), pos, self.radius + 3, 2)
        self.draw_hp(surf, camera)

    def draw_hp(self, surf, camera):
        w, h = 28, 4
        x = int(self.x + camera[0] - w // 2)
        y = int(self.y + camera[1] - self.radius - 10)
        ratio = max(0, self.hp / self.max_hp)
        pygame.draw.rect(surf, (40, 30, 30), (x, y, w, h))
        pygame.draw.rect(surf, (80, 220, 100), (x, y, int(w * ratio), h))


class Goblin(Enemy):
    def __init__(self, x, y, floor):
        super().__init__(x, y, int(45 + floor * 7), 105 + floor * 7, 10 + floor * 2, (60, 200, 70))
        self.radius = 14

    def update(self, dt, player, enemy_projectiles):
        super().update(dt, player, enemy_projectiles)
        d = self.base_move(dt, player, stop_dist=24)
        if d < 30 and self.cooldown <= 0:
            player.take_damage(self.damage)
            self.cooldown = 0.75


class RangedSlime(Enemy):
    def __init__(self, x, y, floor):
        super().__init__(x, y, int(52 + floor * 8), 80 + floor * 5, 8 + floor, (110, 220, 120))
        self.radius = 16

    def update(self, dt, player, enemy_projectiles):
        super().update(dt, player, enemy_projectiles)
        d = self.base_move(dt, player, stop_dist=180)
        if d < 280 and self.cooldown <= 0:
            dx, dy = player.x - self.x, player.y - self.y
            dist = max(0.001, math.hypot(dx, dy))
            enemy_projectiles.append(
                Projectile(
                    self.x,
                    self.y,
                    dx / dist * 240,
                    dy / dist * 240,
                    self.damage,
                    500,
                    (150, 240, 150),
                    radius=6,
                    owner="enemy",
                    slow_effect=0.35 if self.affix == "ice" else 0.0,
                )
            )
            self.cooldown = 1.45


class Bat(Enemy):
    def __init__(self, x, y, floor):
        super().__init__(x, y, int(30 + floor * 5), 145 + floor * 15, 7 + floor, (180, 90, 220))
        self.radius = 11
        self.dash_cd = random.uniform(1.2, 2.0)
        self.dash_time = 0.0
        self.vx = 0
        self.vy = 0

    def update(self, dt, player, enemy_projectiles):
        super().update(dt, player, enemy_projectiles)
        self.dash_cd -= dt
        if self.dash_time > 0:
            self.dash_time -= dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            if math.hypot(player.x - self.x, player.y - self.y) < 23 and self.cooldown <= 0:
                player.take_damage(self.damage + 3)
                self.cooldown = 0.8
            return
        self.base_move(dt, player, stop_dist=12)
        if self.dash_cd <= 0:
            dx, dy = player.x - self.x, player.y - self.y
            d = max(0.001, math.hypot(dx, dy))
            self.vx = dx / d * 440
            self.vy = dy / d * 440
            self.dash_time = 0.16
            self.dash_cd = random.uniform(1.3, 2.1)


class BossGolem(Enemy):
    def __init__(self, x, y, floor):
        super().__init__(x, y, 500 + floor * 120, 75 + floor * 8, 18 + floor * 2, (160, 130, 110))
        self.radius = 36
        self.phase_timer = 1.6
        self.attack = "idle"
        self.charge_v = pygame.Vector2(0, 0)
        self.charge_time = 0
        self.slam_r = 0
        self.slam_hit = False

    def weapon_damage_multiplier(self, weapon_name):
        if weapon_name in ("Machine Gun", "Pistol"):
            return 0.85
        return 1.0

    def update(self, dt, player, enemy_projectiles):
        super().update(dt, player, enemy_projectiles)
        self.phase_timer -= dt

        if self.attack == "charge":
            self.charge_time -= dt
            self.x += self.charge_v.x * dt
            self.y += self.charge_v.y * dt
            if math.hypot(player.x - self.x, player.y - self.y) < self.radius + player.radius + 4:
                player.take_damage(self.damage + 10)
            if self.charge_time <= 0:
                self.attack = "idle"
                self.phase_timer = 1.1
            return

        if self.attack == "slam":
            self.slam_r += 320 * dt
            d = math.hypot(player.x - self.x, player.y - self.y)
            if not self.slam_hit and d < self.slam_r + 8 and d > self.slam_r - 14:
                player.take_damage(self.damage + 8)
                self.slam_hit = True
            if self.slam_r > 220:
                self.attack = "idle"
                self.phase_timer = 1.0
            return

        if self.phase_timer <= 0:
            pattern = random.choice(["slam", "rock", "charge"])
            if pattern == "slam":
                self.attack = "slam"
                self.slam_r = 20
                self.slam_hit = False
                self.phase_timer = 0.9
            elif pattern == "rock":
                dx, dy = player.x - self.x, player.y - self.y
                d = max(0.001, math.hypot(dx, dy))
                enemy_projectiles.append(
                    Projectile(
                        self.x,
                        self.y,
                        dx / d * 300,
                        dy / d * 300,
                        self.damage + 6,
                        700,
                        (170, 140, 120),
                        radius=10,
                        owner="enemy",
                    )
                )
                self.phase_timer = 1.2
            else:
                dx, dy = player.x - self.x, player.y - self.y
                d = max(0.001, math.hypot(dx, dy))
                self.charge_v = pygame.Vector2(dx / d * 500, dy / d * 500)
                self.charge_time = 0.42
                self.attack = "charge"

    def draw(self, surf, camera):
        super().draw(surf, camera)
        if self.attack == "slam":
            pygame.draw.circle(
                surf,
                (210, 180, 130),
                (int(self.x + camera[0]), int(self.y + camera[1])),
                int(self.slam_r),
                3,
            )
