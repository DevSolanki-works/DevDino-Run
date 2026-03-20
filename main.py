import pygame
import random
import os
import sys
import asyncio
import math

# ==========================================
# 1. UTILITY & FILE HANDLING FUNCTIONS
# ==========================================
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def save_leaderboard(new_score):
    scores = load_leaderboard()
    scores.append(int(new_score))
    scores.sort(reverse=True)
    scores = scores[:3]
    try:
        with open("leaderboard.txt", "w") as f:
            for s in scores:
                f.write(f"{s}\n")
    except: pass

def load_leaderboard():
    scores = []
    try:
        if os.path.exists("leaderboard.txt"):
            with open("leaderboard.txt", "r") as f:
                for line in f:
                    if line.strip():
                        scores.append(int(line.strip()))
    except: pass
    while len(scores) < 3:
        scores.append(0)
    return sorted(scores, reverse=True)

def draw_text_with_shadow(surface, text, font, color, x, y, shadow_color=(80, 80, 80), alpha=255):
    shadow = font.render(text, True, shadow_color)
    main_text = font.render(text, True, color)
    if alpha < 255:
        shadow.set_alpha(alpha)
        main_text.set_alpha(alpha)
    surface.blit(shadow, (x + 2, y + 2))
    surface.blit(main_text, (x, y))

# ==========================================
# 2. PYGAME INITIALIZATION
# ==========================================
pygame.init()
pygame.mixer.init()
WIDTH, HEIGHT = 800, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dog Runner Pro")

# Fonts
font = pygame.font.SysFont("Comic Sans MS", 26, bold=True)
big_font = pygame.font.SysFont("Comic Sans MS", 50, bold=True)
small_font = pygame.font.SysFont("Comic Sans MS", 20, bold=True)
clock = pygame.time.Clock()

async def main():
    # --- State Variables ---
    leaderboard = load_leaderboard()
    high_score = leaderboard[0]
    old_high_score = high_score
    is_new_best = False
    
    sound_enabled = True
    def play_sound(snd):
        if snd and sound_enabled:
            try: snd.play()
            except: pass
            
    # --- Asset Loading ---
    try:
        jump_sound = pygame.mixer.Sound(resource_path("jump.ogg"))
        death_sound = pygame.mixer.Sound(resource_path("die.ogg"))
        try:
            point_sound = pygame.mixer.Sound(resource_path("point.ogg"))
        except: point_sound = None
        
        all_backgrounds, obstacle_sets = [], []
        
        for i in range(1, 11):
            bg_path = resource_path(f"background{i}.png")
            if os.path.exists(bg_path):
                img = pygame.image.load(bg_path).convert()
                all_backgrounds.append(pygame.transform.scale(img, (WIDTH, HEIGHT)))
                
                current_set = []
                for j in range(1, 7):
                    obs_path = resource_path(f"obs{i}_{j}.png")
                    if os.path.exists(obs_path):
                        o_img = pygame.image.load(obs_path).convert_alpha()
                        current_set.append(pygame.transform.scale(pygame.transform.flip(o_img, True, False), (70, 70)))
                
                if not current_set:
                    for j in range(1, 7):
                        d_path = resource_path(f"d{j}.png")
                        if os.path.exists(d_path):
                            o_img = pygame.image.load(d_path).convert_alpha()
                            current_set.append(pygame.transform.scale(pygame.transform.flip(o_img, True, False), (70, 70)))
                
                obstacle_sets.append(current_set if current_set else [pygame.Surface((70, 70))])

        if not all_backgrounds:
            bg_surface = pygame.Surface((WIDTH, HEIGHT))
            bg_surface.fill((135, 206, 235))
            all_backgrounds.append(bg_surface)
            obstacle_sets.append([pygame.Surface((70, 70))])
            
        bg_image = all_backgrounds[0]
        
        player_frames = [
            pygame.image.load(resource_path("cat_frame1.png")).convert_alpha(),
            pygame.image.load(resource_path("cat_frame2.png")).convert_alpha()
        ]
        player_run = [pygame.transform.scale(pygame.transform.flip(f, True, False), (64, 64)) for f in player_frames]
            
    except Exception as e:
        all_backgrounds = [pygame.Surface((WIDTH, HEIGHT))]
        all_backgrounds[0].fill((135, 206, 235))
        obstacle_sets = [[pygame.Surface((70, 70))]]
        bg_image = all_backgrounds[0]
        player_run = [pygame.Surface((64, 64))]

    # --- Game Physics & Entities ---
    GRAVITY = 0.5
    GROUND_Y = 350
    score = 0
    player_rect = pygame.Rect(80, GROUND_Y - 64, 40, 50)
    player_vel_y = 0
    jump_count = 0 
    
    # Lists for dynamic objects
    obstacles = [] 
    particles = []
    coins = []             # NEW: Collectible coins (now dicts for bobbing)
    floating_texts = []    # NEW: Floating score popups
    
    glitter_colors = [(255, 215, 0), (255, 105, 180), (0, 255, 255), (255, 255, 255), (255, 250, 205)]
    
    obstacle_speed = 5
    spawn_timer = 0
    bg_x = 0
    current_bg_index = 0
    
    p_frame = 0
    p_timer = 0
    pulse_timer = 0
    
    # Visual Effects States
    fade_surface = pygame.Surface((WIDTH, HEIGHT))
    fade_surface.fill((0, 0, 0))
    fade_alpha = 0
    is_fading = False
    fade_state = "out" 
    screen_shake = 0       # NEW: Screen shake timer
    
    # UI Elements
    pause_btn = pygame.Rect(WIDTH - 60, 20, 40, 40)
    sound_btn = pygame.Rect(WIDTH - 110, 20, 40, 40)
    
    # Main Game States
    game_active = False
    start_screen = True
    is_paused = False      # NEW: Pause state
    running = True
    
    # Main rendering surface to allow screen shake
    display_surface = pygame.Surface((WIDTH, HEIGHT))

    # ==========================================
    # 3. MAIN GAME LOOP
    # ==========================================
    while running:
        pulse_timer += 0.08
        pulse_offset = int(5 * math.sin(pulse_timer))
        
        # --- EVENT HANDLING ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                # NEW FEATURE: UI Buttons Click
                action_handled = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if sound_btn.collidepoint(event.pos):
                        sound_enabled = not sound_enabled
                        action_handled = True
                    elif pause_btn.collidepoint(event.pos) and game_active:
                        is_paused = not is_paused
                        action_handled = True
                
                if action_handled:
                    continue

                # NEW FEATURE: Pause System
                if event.type == pygame.KEYDOWN and event.key == pygame.K_p and game_active:
                    is_paused = not is_paused
                    
                is_space = (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE) or event.type == pygame.MOUSEBUTTONDOWN
                
                if is_space and not is_paused:
                    if not game_active:
                        # Reset Game
                        game_active = True
                        start_screen = False
                        score = 0
                        obstacle_speed = 7
                        obstacles.clear()
                        particles.clear()
                        coins.clear()
                        floating_texts.clear()
                        player_rect.bottom = GROUND_Y
                        jump_count = 0
                        is_new_best = False
                        old_high_score = high_score
                        current_bg_index = 0
                        bg_image = all_backgrounds[0]
                        fade_alpha = 0
                        is_fading = False
                    elif jump_count < 2: 
                        # Jump Logic
                        player_vel_y = -13
                        jump_count += 1
                        play_sound(jump_sound)
                        for _ in range(15):
                            c = random.choice(glitter_colors)
                            particles.append([player_rect.centerx, player_rect.bottom, random.uniform(-4, 2), random.uniform(-4, 0), random.randint(3, 6), c])

        # --- GAME LOGIC UPDATE ---
        if game_active and not is_paused:
            # Physics
            player_vel_y += GRAVITY
            player_rect.y += player_vel_y
            if player_rect.bottom >= GROUND_Y:
                player_rect.bottom = GROUND_Y
                player_vel_y = 0
                jump_count = 0 
                if p_timer % 3 == 0:
                    c = random.choice(glitter_colors)
                    particles.append([player_rect.left + 15, player_rect.bottom - 5, random.uniform(-2, -0.5), random.uniform(-2, 0), random.randint(2, 4), c])
            
            # Animations
            p_timer += 1
            if p_timer > 7:
                p_frame = (p_frame + 1) % len(player_run)
                p_timer = 0
            
            # Background & Score
            bg_x = (bg_x - (obstacle_speed // 2)) % -WIDTH
            score += 1 
            if int(score) > high_score:
                high_score = int(score)

            # Level Up / Background Transition
            if int(score) % 2000 == 0 and int(score) > 0 and not is_fading:
                is_fading = True
                fade_state = "out"
                floating_texts.append({"x": WIDTH//2 - 100, "y": 150, "text": "LEVEL UP!", "alpha": 255, "color": (255, 105, 180)})
            
            if is_fading:
                if fade_state == "out":
                    fade_alpha += 10
                    if fade_alpha >= 255:
                        fade_alpha = 255
                        fade_state = "in"
                        current_bg_index = (current_bg_index + 1) % len(all_backgrounds)
                        bg_image = all_backgrounds[current_bg_index]
                else:
                    fade_alpha -= 10
                    if fade_alpha <= 0:
                        fade_alpha = 0
                        is_fading = False
            
            # Speed Increase
            if int(score) > 0 and int(score) % 1000 == 0:
                obstacle_speed += 0.78
                floating_texts.append({"x": player_rect.x, "y": player_rect.y - 40, "text": "SPEED UP!", "alpha": 255, "color": (0, 255, 255)})
                play_sound(point_sound)
            
            # Spawning System (Obstacles and Coins)
            spawn_timer += 1
            if spawn_timer > random.randint(70, 140): 
                # Spawn Obstacle
                new_rect = pygame.Rect(WIDTH + 50, GROUND_Y - 65, 50, 60)
                obstacles.append([new_rect, 0, 0, current_bg_index])
                
                # NEW FEATURE: Spawn Coin (Higher up to require double jump)
                if random.random() < 0.30:
                    coin_base_y = random.choice([GROUND_Y - 170, GROUND_Y - 210]) 
                    coins.append({"rect": pygame.Rect(WIDTH + 150, coin_base_y, 30, 30), "base_y": coin_base_y, "offset": random.random() * 10})
                
                spawn_timer = 0
            
            # Update Coins
            for coin in coins[:]:
                coin["rect"].x -= obstacle_speed
                # Add a cute bobbing motion
                coin["rect"].y = coin["base_y"] + math.sin(pulse_timer * 3 + coin["offset"]) * 8
                
                if coin["rect"].right < 0:
                    coins.remove(coin)
                elif player_rect.colliderect(coin["rect"]):
                    score += 200
                    coins.remove(coin)
                    play_sound(point_sound)
                    # Burst of particles
                    for _ in range(8):
                        particles.append([coin["rect"].centerx, coin["rect"].centery, random.uniform(-3, 3), random.uniform(-3, 3), random.randint(3, 5), (255, 215, 0)])
                    floating_texts.append({"x": player_rect.x, "y": player_rect.y - 20, "text": "+200", "alpha": 255, "color": (255, 215, 0)})

            # Update Obstacles & Collisions
            for ob in obstacles[:]:
                ob[0].x -= obstacle_speed
                ob[2] += 1 
                if ob[2] > 5: 
                    ob[1] = (ob[1] + 1) % len(obstacle_sets[ob[3]])
                    ob[2] = 0
                if ob[0].right < 0:
                    obstacles.remove(ob)
                    
                # Collision Check
                if player_rect.colliderect(ob[0]):
                    game_active = False
                    screen_shake = 20 # NEW FEATURE: Trigger Screen Shake
                    if int(score) > old_high_score:
                        is_new_best = True
                    save_leaderboard(score)
                    leaderboard = load_leaderboard()
                    play_sound(death_sound)

        # Update Floating Texts (even when dead, but not paused)
        if not is_paused:
            for txt in floating_texts[:]:
                txt["y"] -= 1.5
                txt["alpha"] -= 3
                if txt["alpha"] <= 0:
                    floating_texts.remove(txt)

        # --- DRAWING PHASE ---
        display_surface.fill((173, 216, 230)) 
        
        if bg_image:
            display_surface.blit(bg_image, (bg_x, 0))
            display_surface.blit(bg_image, (bg_x + WIDTH, 0))

        # Particles
        if not game_active and not start_screen and is_new_best and not is_paused:
            for _ in range(3):
                c = random.choice(glitter_colors)
                particles.append([WIDTH//2 + random.randint(-200, 200), random.randint(50, 150), random.uniform(-3, 3), random.uniform(-4, 2), random.randint(4, 8), c])

        if not is_paused:
            for p in particles[:]:
                p[0] += p[2]
                p[1] += p[3]
                p[4] -= 0.1 
                if p[4] <= 0:
                    particles.remove(p)
                else:
                    pygame.draw.circle(display_surface, p[5], (int(p[0]), int(p[1])), int(p[4]))
        else:
            # Draw frozen particles if paused
            for p in particles:
                pygame.draw.circle(display_surface, p[5], (int(p[0]), int(p[1])), int(p[4]))
            
        # Draw Entities
        for ob in obstacles:
            display_surface.blit(obstacle_sets[ob[3]][ob[1]], (ob[0].x - 10, ob[0].y - 10))
            
        for coin in coins:
            # Cute Indie Coin drawing
            cx, cy = coin["rect"].center
            pygame.draw.circle(display_surface, (200, 150, 0), (cx, cy + 2), 16) # Shadow/Depth
            pygame.draw.circle(display_surface, (255, 215, 0), (cx, cy), 16)     # Main coin
            pygame.draw.circle(display_surface, (255, 235, 100), (cx, cy), 12)   # Inner highlight
            pygame.draw.circle(display_surface, (255, 255, 255), (cx - 4, cy - 4), 4) # Sparkle
            
        display_surface.blit(player_run[p_frame], (player_rect.x - 10, player_rect.y - 10))
        
        # Draw Floating Texts
        for txt in floating_texts:
            draw_text_with_shadow(display_surface, txt["text"], font, txt["color"], txt["x"], txt["y"], alpha=txt["alpha"])
        
        # Draw Dark Fading Overlay
        if fade_alpha > 0:
            fade_surface.set_alpha(fade_alpha)
            display_surface.blit(fade_surface, (0, 0))

        # HUD / UI
        score_txt = f"SCORE: {int(score)}"
        best_txt = f"BEST: {high_score}"
        # Moved to Left to accommodate buttons on Right
        draw_text_with_shadow(display_surface, score_txt, font, (255, 255, 255), 20, 20)
        draw_text_with_shadow(display_surface, best_txt, font, (255, 235, 150), 20, 60)
        
        # Draw Pause Button
        pygame.draw.rect(display_surface, (255, 255, 255, 200), pause_btn, border_radius=10)
        pygame.draw.rect(display_surface, (100, 149, 237), pause_btn, 3, border_radius=10)
        if not is_paused:
            pygame.draw.rect(display_surface, (100, 149, 237), (pause_btn.x + 12, pause_btn.y + 10, 6, 20))
            pygame.draw.rect(display_surface, (100, 149, 237), (pause_btn.x + 24, pause_btn.y + 10, 6, 20))
        else:
            pygame.draw.polygon(display_surface, (100, 149, 237), [(pause_btn.x + 14, pause_btn.y + 10), (pause_btn.x + 14, pause_btn.y + 30), (pause_btn.x + 30, pause_btn.y + 20)])

        # Draw Sound Button
        pygame.draw.rect(display_surface, (255, 255, 255, 200), sound_btn, border_radius=10)
        pygame.draw.rect(display_surface, (100, 149, 237), sound_btn, 3, border_radius=10)
        pygame.draw.polygon(display_surface, (100, 149, 237), [(sound_btn.x + 10, sound_btn.y + 16), (sound_btn.x + 10, sound_btn.y + 24), (sound_btn.x + 16, sound_btn.y + 24), (sound_btn.x + 24, sound_btn.y + 30), (sound_btn.x + 24, sound_btn.y + 10), (sound_btn.x + 16, sound_btn.y + 16)])
        if not sound_enabled:
            pygame.draw.line(display_surface, (255, 100, 100), (sound_btn.x + 6, sound_btn.y + 6), (sound_btn.x + 34, sound_btn.y + 34), 4)
        else:
            pygame.draw.arc(display_surface, (100, 149, 237), (sound_btn.x + 16, sound_btn.y + 12, 12, 16), -math.pi/2, math.pi/2, 3)
        
        # Paused Screen
        if is_paused:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            display_surface.blit(overlay, (0,0))
            draw_text_with_shadow(display_surface, "TAKING A BREAK", big_font, (255, 250, 205), WIDTH//2 - big_font.size("TAKING A BREAK")[0]//2, HEIGHT//2 - 50)
            resume_txt = font.render("Tap Pause or 'P' to Resume", True, (200, 200, 200))
            display_surface.blit(resume_txt, (WIDTH//2 - resume_txt.get_width()//2, HEIGHT//2 + 20))
        
        # Start Screen
        if start_screen:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 240, 245, 180)) 
            display_surface.blit(overlay, (0,0))
            draw_text_with_shadow(display_surface, "Welcome to ", font, (100, 149, 237), WIDTH//2 - font.size("Welcome to ")[0]//2, 80)
            draw_text_with_shadow(display_surface, "DevDino Run", big_font, (255, 105, 180), WIDTH//2 - big_font.size("DevDino Run")[0]//2, 130 + pulse_offset, (255, 200, 210))
            st_txt = font.render("Tap Space or Click To Play!", True, (120, 120, 120))
            display_surface.blit(st_txt, (WIDTH//2 - st_txt.get_width()//2, 230))
            
        # Game Over Screen
        if not game_active and not start_screen and not is_paused:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 240, 245, 185))
            display_surface.blit(overlay, (0,0))
            
            panel = pygame.Surface((340, 260), pygame.SRCALPHA)
            pygame.draw.rect(panel, (255, 255, 255, 230), (0, 0, 340, 260), border_radius=25)
            pygame.draw.rect(panel, (100, 149, 237), (0, 0, 340, 260), 5, border_radius=25)
            display_surface.blit(panel, (WIDTH//2 - 170, 70))

            if is_new_best:
                draw_text_with_shadow(display_surface, "NEW RECORD! 🎉", font, (255, 105, 180), WIDTH//2 - font.size("NEW RECORD! 🎉")[0]//2, 85 + pulse_offset)
            else:
                draw_text_with_shadow(display_surface, " Try Again ", font, (255, 100, 100), WIDTH//2 - font.size(" Try Again ")[0]//2, 85 + pulse_offset)
            
            draw_text_with_shadow(display_surface, "LEADERBOARD", small_font, (100, 149, 237), WIDTH//2 - small_font.size("LEADERBOARD")[0]//2, 135)
            
            for i, s in enumerate(leaderboard):
                color = (255, 215, 0) if i == 0 else (180, 180, 180) if i == 1 else (205, 127, 50)
                txt = f"Rank {i+1} : {s}"
                draw_text_with_shadow(display_surface, txt, small_font, color, WIDTH//2 - small_font.size(txt)[0]//2, 170 + (i * 30), (50, 50, 50))

            retry = small_font.render("Click or Press Space to Restart", True, (120, 120, 120))
            display_surface.blit(retry, (WIDTH//2 - retry.get_width()//2, 285))

        # --- FINAL RENDER & SCREEN SHAKE LOGIC ---
        render_offset = (0, 0)
        if screen_shake > 0:
            render_offset = (random.randint(-10, 10), random.randint(-10, 10))
            screen_shake -= 1

        screen.fill((0, 0, 0)) # Clean edges during shake
        screen.blit(display_surface, render_offset)

        pygame.display.flip()
        clock.tick(60) 
        await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())

