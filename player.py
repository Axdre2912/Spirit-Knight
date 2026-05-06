import math
import pygame

from weapons import WeaponInstance


class Player:
    def __init__(self, pos):
        self.x, self.y = pos
        self.radius = 14
        self.base_speed = 180.0
        self.speed_multiplier = 1.0
        self.hp = 100
        self.max_hp = 100
        self.coins = 0

        self.weapon_slots = [WeaponInstance("Pistol"), WeaponInstance("Sword")]
        self.active_weapon_idx = 0
        self.pickup_cooldown = 0.0

        self.dash_speed = 540
        self.dash_duration = 0.16
        self.dash_cd = 1.0
        self.dash_timer = 0.0
        self.dash_cooldown_timer = 0.0
        self.invincible_timer = 0.0
        self.dash_dir = pygame.Vector2(0, 0)

        self.fire_rate_boost_timer = 0.0
        self.perm_fire_rate_bonus = 1.0
        self.damage_bonus = 1.0
        self.combo_count = 0
        self.combo_timer = 0.0

    @property
    def alive(self):
        return self.hp > 0

    def active_weapon(self):
        return self.weapon_slots[self.active_weapon_idx]

    def swap_weapon(self):
        self.active_weapon_idx = 1 - self.active_weapon_idx

    def reset_combo(self):
        self.combo_count = 0
        self.combo_timer = 0.0

    def on_kill(self):
        self.combo_count += 1
        self.combo_timer = 2.0
        if self.combo_count >= 5:
            self.fire_rate_boost_timer = 3.0
            self.combo_count = 0

    def use_dash(self, move_dir):
        if self.dash_cooldown_timer > 0 or self.dash_timer > 0:
            return
        dash = pygame.Vector2(move_dir.x, move_dir.y)
        if dash.length_squared() == 0:
            dash = pygame.Vector2(1, 0)
        self.dash_dir = dash.normalize()
        self.dash_timer = self.dash_duration
        self.dash_cooldown_timer = self.dash_cd
        self.invincible_timer = self.dash_duration + 0.05

    def take_damage(self, amount):
        if self.invincible_timer > 0:
            return
        self.hp = max(0, self.hp - amount)

    def move(self, dt, keys, room_bounds, blocked_rects):
        move = pygame.Vector2(0, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x += 1
        if move.length_squared() > 0:
            move = move.normalize()

        speed = self.base_speed * self.speed_multiplier
        if self.dash_timer > 0:
            vel = self.dash_dir * self.dash_speed
        else:
            vel = move * speed
        dx = vel.x * dt
        dy = vel.y * dt

        new_x = self.x + dx
        new_y = self.y + dy
        test_rect = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)

        test_rect.center = (new_x, self.y)
        if self._inside_room(test_rect, room_bounds) and not self._hits_blocked(test_rect, blocked_rects):
            self.x = new_x
        test_rect.center = (self.x, new_y)
        if self._inside_room(test_rect, room_bounds) and not self._hits_blocked(test_rect, blocked_rects):
            self.y = new_y
        return move

    def _inside_room(self, rect, room_bounds):
        return room_bounds.contains(rect)

    def _hits_blocked(self, rect, blocked_rects):
        return any(rect.colliderect(r) for r in blocked_rects)

    def update(self, dt):
        self.pickup_cooldown = max(0.0, self.pickup_cooldown - dt)
        self.dash_timer = max(0.0, self.dash_timer - dt)
        self.dash_cooldown_timer = max(0.0, self.dash_cooldown_timer - dt)
        self.invincible_timer = max(0.0, self.invincible_timer - dt)
        self.combo_timer = max(0.0, self.combo_timer - dt)
        if self.combo_timer <= 0:
            self.combo_count = 0
        self.fire_rate_boost_timer = max(0.0, self.fire_rate_boost_timer - dt)

    def fire_multiplier(self):
        temp = 1.35 if self.fire_rate_boost_timer > 0 else 1.0
        return temp * self.perm_fire_rate_bonus

    def try_shoot(self, now, mouse_world):
        weapon = self.active_weapon()
        angle = math.atan2(mouse_world[1] - self.y, mouse_world[0] - self.x)
        if weapon.melee:
            if weapon.can_fire(now):
                weapon.next_fire_time = now + (weapon.cooldown / self.fire_multiplier())
                print("pew pew")
                return "melee", angle, weapon.data["range"], weapon.data["damage"] * self.damage_bonus
            return None
        shots = weapon.try_fire(now, (self.x, self.y), angle, self.fire_multiplier())
        for s in shots:
            s.damage *= self.damage_bonus
        return shots

    def draw(self, surf, camera):
        pos = (int(self.x + camera[0]), int(self.y + camera[1]))
        color = (80, 220, 255) if self.invincible_timer <= 0 else (250, 250, 250)
        pygame.draw.circle(surf, color, pos, self.radius)

    def draw_weapon(self, surf, mouse_world, camera):
        weapon = self.active_weapon()
        px = self.x + camera[0]
        py = self.y + camera[1]
        angle = math.atan2(mouse_world[1] - self.y, mouse_world[0] - self.x)
        if weapon.melee:
            for i in range(3):
                arc_r = weapon.data["range"] - i * 8
                pygame.draw.arc(
                    surf,
                    (220, 220, 220),
                    pygame.Rect(px - arc_r, py - arc_r, arc_r * 2, arc_r * 2),
                    angle - 0.5,
                    angle + 0.5,
                    2,
                )
        else:
            tip = (px + math.cos(angle) * 22, py + math.sin(angle) * 22)
            pygame.draw.line(surf, weapon.data["color"], (px, py), tip, 4)
