import math
import random
import pygame

from player import Player
from room import FloorMap, blocked_door_rects, roll_minion_drop, roll_boss_drop
from weapons import Projectile, WeaponInstance


WIDTH, HEIGHT = 960, 640
FPS = 60
ROOM_RECT = pygame.Rect(80, 70, 800, 500)


def draw_text(surf, text, pos, size=22, color=(240, 240, 240), center=False):
    font = pygame.font.SysFont("consolas", size)
    t = font.render(text, True, color)
    r = t.get_rect(center=pos) if center else t.get_rect(topleft=pos)
    surf.blit(t, r)


def circle_hit(ax, ay, ar, bx, by, br):
    return math.hypot(ax - bx, ay - by) <= (ar + br)


def draw_minimap(surf, fmap):
    base_x, base_y = WIDTH - 170, 20
    for (gx, gy), room in fmap.rooms.items():
        x = base_x + gx * 24
        y = base_y + gy * 24
        color = (80, 80, 80)
        if room.explored:
            color = (120, 140, 170)
        if room.rtype == "boss":
            color = (160, 80, 80) if room.explored else color
        if (gx, gy) == fmap.current:
            color = (240, 220, 120)
        pygame.draw.rect(surf, color, (x, y, 20, 20), border_radius=3)


def try_room_transition(player, fmap):
    room = fmap.current_room()
    if not room.cleared and room.rtype in ("enemy", "boss"):
        return False
    midx = ROOM_RECT.centerx
    midy = ROOM_RECT.centery
    door_half = 60
    if player.y <= ROOM_RECT.top + player.radius + 2 and abs(player.x - midx) < door_half and "N" in room.neighbors:
        if fmap.move_room("N"):
            player.y = ROOM_RECT.bottom - player.radius - 6
            return True
    if player.y >= ROOM_RECT.bottom - player.radius - 2 and abs(player.x - midx) < door_half and "S" in room.neighbors:
        if fmap.move_room("S"):
            player.y = ROOM_RECT.top + player.radius + 6
            return True
    if player.x <= ROOM_RECT.left + player.radius + 2 and abs(player.y - midy) < door_half and "W" in room.neighbors:
        if fmap.move_room("W"):
            player.x = ROOM_RECT.right - player.radius - 6
            return True
    if player.x >= ROOM_RECT.right - player.radius - 2 and abs(player.y - midy) < door_half and "E" in room.neighbors:
        if fmap.move_room("E"):
            player.x = ROOM_RECT.left + player.radius + 6
            return True
    return False


def draw_room_geometry(screen, room):
    pygame.draw.rect(screen, (42, 45, 55), ROOM_RECT, border_radius=8)
    pygame.draw.rect(screen, (18, 18, 24), ROOM_RECT, 8, border_radius=8)
    door_w = 120
    if "N" in room.neighbors:
        pygame.draw.rect(screen, (90, 100, 120), (ROOM_RECT.centerx - door_w // 2, ROOM_RECT.top - 2, door_w, 10))
    if "S" in room.neighbors:
        pygame.draw.rect(screen, (90, 100, 120), (ROOM_RECT.centerx - door_w // 2, ROOM_RECT.bottom - 8, door_w, 10))
    if "W" in room.neighbors:
        pygame.draw.rect(screen, (90, 100, 120), (ROOM_RECT.left - 2, ROOM_RECT.centery - door_w // 2, 10, door_w))
    if "E" in room.neighbors:
        pygame.draw.rect(screen, (90, 100, 120), (ROOM_RECT.right - 8, ROOM_RECT.centery - door_w // 2, 10, door_w))


def spawn_ground_weapon(room, x, y, name=None):
    weapon_name = name or random.choice(["Pistol", "Shotgun", "Machine Gun", "Sword"])
    room.weapon_pickups.append({"x": x, "y": y, "weapon": WeaponInstance(weapon_name)})


def process_chest(player, room):
    if not room.chest or room.chest["opened"]:
        return
    if math.hypot(player.x - room.chest["x"], player.y - room.chest["y"]) < 28:
        room.chest["opened"] = True
        if room.chest["rarity"] == "rare":
            if random.random() < 0.5:
                player.speed_multiplier *= 1.2
            else:
                player.perm_fire_rate_bonus *= 1.15
        else:
            if random.random() < 0.5:
                spawn_ground_weapon(room, room.chest["x"] + 24, room.chest["y"], random.choice(["Shotgun", "Machine Gun", "Sword"]))
            else:
                room.drops.append({"type": "coins", "x": room.chest["x"] + 20, "y": room.chest["y"], "value": 10})


def apply_player_drop(player, drop):
    t = drop["type"]
    if t == "health_orb":
        player.hp = min(player.max_hp, player.hp + drop["value"])
    elif t == "mana_orb":
        for w in player.weapon_slots:
            w.restore_mana()
    elif t == "coins":
        player.coins += drop["value"]
    elif t == "legendary":
        if drop["bonus"] == "damage_boost":
            player.damage_bonus *= 1.2
        else:
            player.speed_multiplier *= 1.2


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Spirit Knight - Roguelite")
    clock = pygame.time.Clock()

    player = Player((ROOM_RECT.centerx, ROOM_RECT.centery))
    floor_num = 1
    fmap = FloorMap(floor_num)
    has_key = False
    game_over = False

    projectiles = []
    camera = pygame.Vector2(0, 0)

    while True:
        dt = clock.tick(FPS) / 1000.0
        now = pygame.time.get_ticks() / 1000.0
        mouse_screen = pygame.mouse.get_pos()
        mouse_world = (mouse_screen[0] - camera.x, mouse_screen[1] - camera.y)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_e):
                    player.swap_weapon()
                if event.key == pygame.K_SPACE:
                    keys = pygame.key.get_pressed()
                    mv = pygame.Vector2((keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]),
                                        (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]))
                    player.use_dash(mv)
                if event.key == pygame.K_r and game_over:
                    return main()
            if event.type == pygame.MOUSEBUTTONDOWN and not game_over:
                if event.button == 1:
                    out = player.try_shoot(now, mouse_world)
                    if isinstance(out, list):
                        projectiles.extend(out)
                    elif out and out[0] == "melee":
                        _, ang, rng, dmg = out
                        room = fmap.current_room()
                        for enemy in room.enemies:
                            d = math.hypot(enemy.x - player.x, enemy.y - player.y)
                            if d <= rng:
                                a = math.atan2(enemy.y - player.y, enemy.x - player.x)
                                if abs((a - ang + math.pi) % (2 * math.pi) - math.pi) <= 0.6:
                                    mod = 1.0
                                    if enemy.__class__.__name__ == "BossGolem":
                                        mod = enemy.weapon_damage_multiplier(player.active_weapon().name)
                                    enemy.take_damage(dmg * mod)
                if event.button == 3:
                    player.use_dash(pygame.Vector2(mouse_world[0] - player.x, mouse_world[1] - player.y))

        if game_over:
            screen.fill((8, 8, 12))
            draw_text(screen, "GAME OVER", (WIDTH // 2, HEIGHT // 2 - 30), size=48, color=(255, 90, 90), center=True)
            draw_text(screen, f"Final Score (Coins): {player.coins}", (WIDTH // 2, HEIGHT // 2 + 20), size=28, center=True)
            draw_text(screen, "Press R to Restart", (WIDTH // 2, HEIGHT // 2 + 60), size=20, color=(200, 200, 220), center=True)
            pygame.display.flip()
            continue

        room = fmap.current_room()
        room.explored = True
        room.spawn_contents(floor_num)
        keys = pygame.key.get_pressed()
        move_dir = player.move(dt, keys, ROOM_RECT, blocked_door_rects(room, ROOM_RECT))
        player.update(dt)
        if keys[pygame.K_LSHIFT]:
            player.use_dash(move_dir)
        if pygame.mouse.get_pressed()[0]:
            out = player.try_shoot(now, mouse_world)
            if isinstance(out, list):
                projectiles.extend(out)

        for b in room.breakables:
            if b["hp"] > 0 and math.hypot(player.x - b["x"], player.y - b["y"]) < 20 and player.dash_timer > 0:
                b["hp"] = 0
                if random.random() < 0.35:
                    room.drops.append({"type": "coins", "x": b["x"], "y": b["y"], "value": random.randint(1, 3)})
                if random.random() < 0.10:
                    room.drops.append({"type": "health_orb", "x": b["x"] + 5, "y": b["y"], "value": 8})

        alive_enemies = []
        for enemy in room.enemies:
            if enemy.alive:
                enemy.update(dt, player, room.enemy_projectiles)
            if enemy.alive:
                alive_enemies.append(enemy)
            else:
                player.on_kill()
                if enemy.__class__.__name__ == "BossGolem":
                    room.drops.extend(roll_boss_drop(enemy.x, enemy.y))
                else:
                    room.drops.extend(roll_minion_drop(enemy.x, enemy.y))
                    if random.random() < 0.10:
                        spawn_ground_weapon(room, enemy.x, enemy.y)
        room.enemies = alive_enemies

        all_projectiles = projectiles + room.enemy_projectiles
        keep_player = []
        keep_enemy = []
        for p in all_projectiles:
            if not p.update(dt):
                continue
            if not ROOM_RECT.collidepoint(p.x, p.y):
                continue
            if p.owner == "player":
                hit = False
                for enemy in room.enemies:
                    if circle_hit(p.x, p.y, p.radius, enemy.x, enemy.y, enemy.radius):
                        mod = 1.0
                        if enemy.__class__.__name__ == "BossGolem":
                            mod = enemy.weapon_damage_multiplier(player.active_weapon().name)
                        enemy.take_damage(p.damage * mod)
                        if p.explosive:
                            for e2 in room.enemies:
                                if math.hypot(e2.x - p.x, e2.y - p.y) < 52:
                                    e2.take_damage(p.damage * 0.5)
                        hit = True
                        break
                if not hit:
                    keep_player.append(p)
            else:
                if circle_hit(p.x, p.y, p.radius, player.x, player.y, player.radius):
                    player.take_damage(p.damage)
                    if p.slow_effect > 0:
                        player.invincible_timer = max(player.invincible_timer, 0.02)
                    if random.random() < 0.08:
                        room.drops.append({"type": "fire_patch", "x": player.x, "y": player.y, "time": 2.2})
                else:
                    keep_enemy.append(p)
        projectiles = keep_player
        room.enemy_projectiles = keep_enemy

        for d in list(room.drops):
            if d["type"] == "fire_patch":
                d["time"] -= dt
                if d["time"] <= 0:
                    room.drops.remove(d)
                    continue
                if math.hypot(player.x - d["x"], player.y - d["y"]) < 16:
                    player.take_damage(4 * dt)
                continue
            if math.hypot(player.x - d["x"], player.y - d["y"]) < 20:
                if d["type"] == "key":
                    has_key = True
                else:
                    apply_player_drop(player, d)
                room.drops.remove(d)

        for wp in list(room.weapon_pickups):
            if math.hypot(player.x - wp["x"], player.y - wp["y"]) < 24 and player.pickup_cooldown <= 0:
                player.weapon_slots[player.active_weapon_idx] = wp["weapon"]
                player.pickup_cooldown = 0.3
                room.weapon_pickups.remove(wp)

        process_chest(player, room)

        if room.rtype == "shop":
            for item in room.shop_items:
                if math.hypot(player.x - item["x"], player.y - item["y"]) < 24 and keys[pygame.K_f]:
                    if player.coins >= item["price"]:
                        player.coins -= item["price"]
                        if item["type"] == "heal":
                            player.hp = min(player.max_hp, player.hp + 40)
                        else:
                            player.weapon_slots[player.active_weapon_idx] = WeaponInstance(item["name"])

        room.cleared = room.is_combat_cleared()
        transitioned = try_room_transition(player, fmap)
        if transitioned:
            projectiles.clear()

        if room.rtype == "boss" and room.cleared and has_key and keys[pygame.K_n]:
            floor_num += 1
            fmap = FloorMap(floor_num)
            player.x, player.y = ROOM_RECT.centerx, ROOM_RECT.centery
            has_key = False
            projectiles.clear()

        if player.hp <= 0:
            game_over = True

        target_cam = pygame.Vector2(WIDTH / 2 - player.x, HEIGHT / 2 - player.y)
        camera += (target_cam - camera) * min(1.0, dt * 7.0)

        screen.fill((22, 22, 30))
        draw_room_geometry(screen, room)

        for b in room.breakables:
            if b["hp"] > 0:
                pygame.draw.rect(screen, (140, 100, 70), (b["x"] - 10 + camera.x, b["y"] - 10 + camera.y, 20, 20))
        if room.chest:
            c = room.chest
            col = (170, 110, 70) if not c["opened"] else (90, 70, 55)
            pygame.draw.rect(screen, col, (c["x"] - 12 + camera.x, c["y"] - 10 + camera.y, 24, 20))

        for d in room.drops:
            color = {
                "health_orb": (90, 240, 90),
                "mana_orb": (70, 170, 255),
                "coins": (255, 215, 80),
                "key": (255, 245, 150),
                "legendary": (255, 120, 255),
                "fire_patch": (255, 90, 50),
            }.get(d["type"], (255, 255, 255))
            r = 7 if d["type"] != "fire_patch" else 13
            pygame.draw.circle(screen, color, (int(d["x"] + camera.x), int(d["y"] + camera.y)), r)

        for wp in room.weapon_pickups:
            pygame.draw.rect(screen, wp["weapon"].data["color"], (wp["x"] - 8 + camera.x, wp["y"] - 4 + camera.y, 16, 8))
            draw_text(screen, wp["weapon"].name, (wp["x"] - 30 + camera.x, wp["y"] - 20 + camera.y), size=14)

        for p in projectiles + room.enemy_projectiles:
            pygame.draw.circle(screen, p.color, (int(p.x + camera.x), int(p.y + camera.y)), p.radius)
        for enemy in room.enemies:
            enemy.draw(screen, camera)

        player.draw(screen, camera)
        player.draw_weapon(screen, mouse_world, camera)
        for r in blocked_door_rects(room, ROOM_RECT):
            pygame.draw.rect(screen, (180, 60, 60), r, 2)

        pygame.draw.rect(screen, (30, 20, 20), (20, 20, 200, 20))
        pygame.draw.rect(screen, (220, 80, 90), (20, 20, int(200 * (player.hp / player.max_hp)), 20))
        draw_text(screen, f"HP {int(player.hp)} / {player.max_hp}", (25, 22), size=16)

        w = player.active_weapon()
        ammo_text = "INF" if w.ammo < 0 else str(w.ammo)
        draw_text(screen, f"{w.name} | Ammo: {ammo_text}", (WIDTH // 2 - 90, HEIGHT - 36), size=22)
        draw_text(screen, f"Coins: {player.coins}", (WIDTH - 150, 20), size=24, color=(255, 230, 90))
        draw_minimap(screen, fmap)
        draw_text(screen, f"Floor {floor_num}", (20, HEIGHT - 36), size=22)

        if room.rtype == "shop":
            draw_text(screen, "Shop: stand near item + press F", (300, 88), size=20, color=(180, 220, 255))
            for it in room.shop_items:
                pygame.draw.rect(screen, (90, 150, 180), (it["x"] - 14 + camera.x, it["y"] - 14 + camera.y, 28, 28), 2)
                label = "Heal +40" if it["type"] == "heal" else it["name"]
                draw_text(screen, f"{label} (${it['price']})", (it["x"] - 44 + camera.x, it["y"] + 18 + camera.y), size=14)

        if fmap.current_room().rtype == "boss" and fmap.current_room().cleared and has_key:
            draw_text(screen, "Press N to descend (Endless mode)", (WIDTH // 2 - 150, 34), size=20, color=(255, 230, 140))

        pygame.display.flip()


if __name__ == "__main__":
    main()
