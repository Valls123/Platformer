"""
Платформер - Уровень 2
"""
import arcade
import os
import sys
import math
import time
from arcade.camera import Camera2D
from arcade import PhysicsEnginePlatformer

# Добавляем путь к первому уровню для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем классы из первого уровня
from level_1 import (
    SoundDatabase,
    PlayerCharacter,
    FloatingText,
    Door,
    LevelCompleteView,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    TILE_SCALING,
    COIN_SCALING,
    SPRITE_PIXEL_SIZE,
    GRAVITY,
    PLAYER_MOVEMENT_SPEED,
    PLAYER_JUMP_SPEED,
    COYOTE_TIME,
    JUMP_BUFFER,
    MAX_JUMPS,
    CAMERA_LERP
)

# Настройки второго уровня
SCREEN_TITLE = "Приключения Джо: Platformer - Уровень 2: Прогулка в лесу"
PLAYER_START_X = SPRITE_PIXEL_SIZE * TILE_SCALING * 2
PLAYER_START_Y = SPRITE_PIXEL_SIZE * TILE_SCALING * 3
DOOR_X = 2200
DOOR_Y = 120


class WormEnemy(arcade.Sprite):
    """Враг-слизень, который убивает игрока при касании"""

    def __init__(self):
        super().__init__()
        self.scale = TILE_SCALING * 0.8
        self.textures = []

        # Загружаем текстуры для анимации
        self.textures.append(arcade.load_texture(":resources:/images/enemies/slimeBlue.png"))
        self.textures.append(arcade.load_texture(":resources:/images/enemies/slimeBlue_move.png"))

        self.texture = self.textures[0]
        self.cur_texture = 0
        self.animation_timer = 0
        self.animation_speed = 0.2  # Смена текстуры каждые 0.2 секунды

        # Настройки движения
        self.move_direction = 1  # 1 - вправо, -1 - влево
        self.move_speed = 1.5
        self.move_range = 100  # Дистанция движения
        self.start_x = 0
        self.damage = 1  # Урон при касании

    def update_animation(self, delta_time):
        """Обновление анимации слизня"""
        self.animation_timer += delta_time
        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0
            self.cur_texture = (self.cur_texture + 1) % len(self.textures)
            self.texture = self.textures[self.cur_texture]

    def update_movement(self):
        """Обновление движения слизня"""
        if not self.start_x:
            self.start_x = self.center_x

        # Движение вперед-назад в пределах диапазона
        self.center_x += self.move_direction * self.move_speed

        # Проверяем, не вышел ли за пределы диапазона
        if abs(self.center_x - self.start_x) >= self.move_range:
            self.move_direction *= -1


class Spike(arcade.Sprite):
    """Опасные шипы, убивающие игрока"""

    def __init__(self):
        super().__init__()
        self.texture = arcade.load_texture(":resources:images/tiles/spikes.png")
        self.scale = TILE_SCALING
        self.damage = 1


class GameOverView(arcade.View):
    """Вью для проигрыша"""

    def __init__(self, window, level_class):
        super().__init__()
        self.window = window
        self.level_class = level_class
        self.alpha = 0
        self.show_restart_button = False
        self.restart_button_rect = None
        self.sound_db = SoundDatabase()

    def on_show_view(self):
        """Вызывается при показе вью"""
        # Проигрываем звук проигрыша
        pass

    def update(self, delta_time):
        """Обновляет анимацию"""
        # Плавное появление
        if self.alpha < 255:
            self.alpha = min(255, self.alpha + 5)

        # Показываем кнопку через 1 секунду
        if self.alpha >= 255:
            self.show_restart_button = True

        # Определяем прямоугольник кнопки
        button_width = 300
        button_height = 60
        self.restart_button_rect = (
            SCREEN_WIDTH // 2 - button_width // 2,
            SCREEN_HEIGHT // 2 - 100 - button_height // 2,
            button_width,
            button_height
        )

    def draw(self):
        """Рисует экран проигрыша"""
        # Затемнение фона
        arcade.draw_lrbt_rectangle_filled(
            0,
            SCREEN_WIDTH,
            0,
            SCREEN_HEIGHT,
            (0, 0, 0, int(self.alpha * 0.8))
        )

        container_width = 600
        container_height = 300
        container_x = SCREEN_WIDTH // 2
        container_y = SCREEN_HEIGHT // 2

        # Фон контейнера
        left = container_x - container_width // 2
        right = container_x + container_width // 2
        bottom = container_y - container_height // 2
        top = container_y + container_height // 2

        arcade.draw_lrbt_rectangle_filled(
            left, right, bottom, top,
            (40, 20, 20, self.alpha)
        )

        # Рамка контейнера
        arcade.draw_lrbt_rectangle_outline(
            left, right, bottom, top,
            (255, 100, 100, self.alpha),
            4
        )

        # Заголовок
        arcade.draw_text(
            "Вы проиграли!",
            container_x,
            container_y + 60,
            (255, 50, 50, self.alpha),
            48,
            bold=True,
            anchor_x="center",
            anchor_y="center"
        )

        # Сообщение
        arcade.draw_text(
            "Ваш персонаж был убит",
            container_x,
            container_y,
            (255, 200, 200, self.alpha),
            32,
            bold=True,
            anchor_x="center",
            anchor_y="center"
        )

        # Кнопка перезапуска
        if self.show_restart_button:
            x, y, w, h = self.restart_button_rect

            mouse_x = self.window._mouse_x
            mouse_y = self.window._mouse_y

            is_hovered = x <= mouse_x <= x + w and y <= mouse_y <= y + h
            color = (50, 200, 50, self.alpha) if is_hovered else (0, 150, 0, self.alpha)

            arcade.draw_lrbt_rectangle_filled(
                x,
                x + w,
                y,
                y + h,
                color
            )
            arcade.draw_lrbt_rectangle_outline(
                x,
                x + w,
                y,
                y + h,
                (255, 255, 255, self.alpha),
                3
            )

            arcade.draw_text(
                "RESTART",
                x + w // 2,
                y + h // 2,
                (255, 255, 255, self.alpha),
                28,
                bold=True,
                anchor_x="center",
                anchor_y="center"
            )

    def on_mouse_press(self, x, y, button, modifiers):
        """Обрабатывает нажатие мыши"""
        if button == arcade.MOUSE_BUTTON_LEFT and self.show_restart_button:
            button_x, button_y, button_w, button_h = self.restart_button_rect
            if (button_x <= x <= button_x + button_w and
                    button_y <= y <= button_y + button_h):
                # Перезапускаем уровень
                new_game = self.level_class()
                new_game.setup()
                self.window.show_view(new_game)


class Level2CompleteView(LevelCompleteView):
    """Вью для завершения уровня 2"""

    def __init__(self, window, score, play_time_seconds):
        super().__init__(window, score, play_time_seconds, current_level=2)
        # level_number уже устанавливается в родительском классе

    def save_to_database(self):
        """Сохраняет результат уровня 2 в базу данных"""
        import sqlite3
        from pathlib import Path

        try:
            # Определяем путь к основной папке с БД
            current_dir = Path(__file__).parent  # папка levels
            base_dir = current_dir.parent  # основная папка проекта
            db_path = base_dir / "game_stats.db"

            print(f"Путь к БД: {db_path}")

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Вставляем результат уровня 2
            player_id = "player_1"
            level_number = self.current_level

            # Проверяем, есть ли уже запись для этого уровня
            cursor.execute('''
                SELECT score FROM level_results 
                WHERE player_id = ? AND level_number = ?
            ''', (player_id, level_number))

            existing_result = cursor.fetchone()

            if existing_result:
                # Если результат уже есть, обновляем только если новый результат лучше
                old_score = existing_result[0]
                if self.score > old_score:
                    cursor.execute('''
                        UPDATE level_results 
                        SET score = ?, play_time_seconds = ?, completed = 1, completed_at = CURRENT_TIMESTAMP
                        WHERE player_id = ? AND level_number = ?
                    ''', (self.score, self.play_time_seconds, player_id, level_number))
                    print(f"✅ Результат уровня {level_number} обновлен: {self.score} (было: {old_score})")
                else:
                    print(f"✅ Старый результат лучше: {old_score} > {self.score}, оставляем старый")
            else:
                # Если записи нет, создаем новую
                cursor.execute('''
                    INSERT INTO level_results 
                    (player_id, level_number, score, completed, play_time_seconds)
                    VALUES (?, ?, ?, 1, ?)
                ''', (player_id, level_number, self.score, self.play_time_seconds))
                print(f"✅ Результат уровня {level_number} сохранен: {self.score}")

            conn.commit()
            conn.close()
            self.level_saved = True

        except Exception as e:
            print(f"❌ Ошибка при сохранении в БД: {e}")
            import traceback
            traceback.print_exc()

    def draw(self):
        """Рисует экран завершения уровня с измененным заголовком"""
        # Затемнение фона
        arcade.draw_lrbt_rectangle_filled(
            0,
            SCREEN_WIDTH,
            0,
            SCREEN_HEIGHT,
            (0, 0, 0, int(self.alpha * 0.7))
        )

        # Частицы
        for particle in self.particles:
            particle.draw()

        container_width = 600
        container_height = 400
        container_x = SCREEN_WIDTH // 2
        container_y = SCREEN_HEIGHT // 2

        # Фон контейнера
        left = container_x - container_width // 2
        right = container_x + container_width // 2
        bottom = container_y - container_height // 2
        top = container_y + container_height // 2

        arcade.draw_lrbt_rectangle_filled(
            left, right, bottom, top,
            (20, 20, 40, self.alpha)
        )

        # Рамка контейнера
        arcade.draw_lrbt_rectangle_outline(
            left, right, bottom, top,
            (100, 100, 255, self.alpha),
            4
        )

        # Заголовок
        arcade.draw_text(
            f"УРОВЕНЬ {self.current_level} ПРОЙДЕН!",
            container_x,
            container_y + 100,
            (255, 215, 0, self.alpha),
            48,
            bold=True,
            anchor_x="center",
            anchor_y="center"
        )

        # Подзаголовок
        arcade.draw_text(
            "Вы справились!",
            container_x,
            container_y + 40,
            (255, 255, 255, self.alpha),
            36,
            bold=True,
            anchor_x="center",
            anchor_y="center"
        )

        # Счет
        arcade.draw_text(
            f"Ваш счет: {self.score}",
            container_x,
            container_y - 10,
            (0, 255, 255, self.alpha),
            32,
            bold=True,
            anchor_x="center",
            anchor_y="center"
        )

        # Время прохождения (в секундах и минутах)
        play_time_minutes = self.play_time_seconds / 60.0
        arcade.draw_text(
            f"Время: {self.play_time_seconds:.1f} сек ({play_time_minutes:.1f} мин)",
            container_x,
            container_y - 60,
            (255, 200, 0, self.alpha),
            28,
            bold=True,
            anchor_x="center",
            anchor_y="center"
        )

        # Кнопка выхода
        if self.show_exit_button:
            x, y, w, h = self.exit_button_rect

            mouse_x = self.window._mouse_x
            mouse_y = self.window._mouse_y

            is_hovered = x <= mouse_x <= x + w and y <= mouse_y <= y + h
            color = (200, 50, 50, self.alpha) if is_hovered else (150, 0, 0, self.alpha)

            arcade.draw_lrbt_rectangle_filled(
                x,
                x + w,
                y,
                y + h,
                color
            )
            arcade.draw_lrbt_rectangle_outline(
                x,
                x + w,
                y,
                y + h,
                (255, 255, 255, self.alpha),
                3
            )

            arcade.draw_text(
                "ВЕРНУТЬСЯ В МЕНЮ",
                x + w // 2,
                y + h // 2,
                (255, 255, 255, self.alpha),
                28,
                bold=True,
                anchor_x="center",
                anchor_y="center"
            )

    def on_mouse_press(self, x, y, button, modifiers):
        """Обрабатывает нажатие мыши"""
        if button == arcade.MOUSE_BUTTON_LEFT and self.show_exit_button:
            button_x, button_y, button_w, button_h = self.exit_button_rect
            if (button_x <= x <= button_x + button_w and
                    button_y <= y <= button_y + button_h):
                # Закрываем окно уровня
                self.window.close()


class MyGame(arcade.View):
    """
    Главный класс игры для уровня 2
    """

    def __init__(self):
        """
        Инициализатор игры
        """
        super().__init__()

        self.music_player = None

        # инициализация БД звуков
        self.sound_db = SoundDatabase()

        # интро
        self.show_intro = True
        self.intro_timer = 0.0
        self.intro_duration = 9.0

        # заморозка игрока
        self.player_frozen = True

        # музыка
        sound_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  "assets", "sounds", "intro_level_2.mp3")

        # Загружаем звук
        self.intro_sound = arcade.load_sound(sound_path)

        # Загружаем громкость музыки из БД
        music_volume = self.sound_db.get_volume('music')
        self.music_player = arcade.play_sound(
            self.intro_sound,
            volume=music_volume,
            loop=False
        )

        # Вью завершения уровня
        self.level_complete_view = None

        # Вью проигрыша
        self.game_over_view = None

        # Отслеживание позиции мыши
        self._mouse_x = 0
        self._mouse_y = 0

        # Таймер для отслеживания времени игры
        self.game_start_time = None
        self.total_play_time_seconds = 0.0

        # Камеры
        self.world_camera = Camera2D()
        self.gui_camera = Camera2D()

        # Отслеживание нажатых клавиш
        self.left = False
        self.right = False
        self.jump = False
        self.down = False

        # Переменные для совместимости со старым кодом
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False

        # Списки спрайтов
        self.coin_list = None
        self.wall_list = None
        self.background_list = None
        self.ladder_list = None
        self.player_list = None
        self.door_list = None
        self.enemy_list = None
        self.spike_list = None
        self.door = None
        self.floating_texts = []

        # Отдельная переменная для спрайта игрока
        self.player_sprite = None

        # Физический движок
        self.physics_engine = None

        # Физика прыжка
        self.time_since_ground = 5.0
        self.jumps_left = MAX_JUMPS
        self.jump_buffer_timer = 0.0
        self.jump_cooldown = 0.0
        self.can_jump_again = True

        # Для скроллинга
        self.view_bottom = 0
        self.view_left = 0

        self.end_of_map = 0

        # Загрузка звуков
        self.collect_coin_sound = arcade.load_sound(":resources:sounds/coin1.wav")
        self.jump_sound = arcade.load_sound(":resources:sounds/jump1.wav")
        self.game_over_sound = arcade.load_sound(":resources:sounds/gameover1.wav")
        self.door_open_sound = arcade.load_sound(":resources:sounds/upgrade1.wav")

        # Переменная для подсказки о двери
        self.show_door_hint = False
        self.door_hint_timer = 0.0

    def play_sound_with_db_volume(self, sound, sound_type):
        """
        Воспроизводит звук с громкостью из базы данных

        Args:
            sound: объект звука arcade
            sound_type: тип звука из БД ('music', 'door_open', 'game_over')
        """
        try:
            volume = self.sound_db.get_volume(sound_type)
            if volume > 0:
                arcade.play_sound(sound, volume=volume)
        except Exception as e:
            # Если есть проблема с БД, воспроизводим со стандартной громкостью
            print(f"Ошибка при получении громкости из БД: {e}")
            arcade.play_sound(sound, volume=0.7)

    def setup(self):
        """ Настройка игры. Вызывается для перезапуска игры. """
        # Сбрасываем параметры скроллинга
        self.view_bottom = 0
        self.view_left = 0

        # Сбрасываем переменные физики
        self.time_since_ground = 5.0
        self.jumps_left = MAX_JUMPS
        self.jump_buffer_timer = 0.0
        self.jump_cooldown = 0.0
        self.can_jump_again = True

        # Сбрасываем вью завершения
        self.level_complete_view = None
        self.game_over_view = None
        self.show_door_hint = False
        self.door_hint_timer = 0.0

        # Сбрасываем таймер
        self.game_start_time = None
        self.total_play_time_seconds = 0.0

        # Создаем списки спрайтов
        self.player_list = arcade.SpriteList()
        self.background_list = arcade.SpriteList()
        self.wall_list = arcade.SpriteList()
        self.coin_list = arcade.SpriteList()
        self.ladder_list = arcade.SpriteList()
        self.door_list = arcade.SpriteList()
        self.enemy_list = arcade.SpriteList()
        self.spike_list = arcade.SpriteList()
        self.floating_texts = []

        # Создаем и размещаем игрока
        self.player_sprite = PlayerCharacter()
        self.player_sprite.center_x = PLAYER_START_X
        self.player_sprite.center_y = PLAYER_START_Y
        self.player_list.append(self.player_sprite)

        # Создаем дверь и добавляем в спрайт-лист
        self.door = Door()
        self.door.center_x = DOOR_X
        self.door.center_y = DOOR_Y + 64
        self.door_list.append(self.door)

        # --- Создаем уровень 2 вручную ---
        # Создаем землю
        for x in range(0, 2500, 64):
            wall = arcade.Sprite(":resources:images/tiles/grassMid.png", TILE_SCALING)
            wall.center_x = x
            wall.center_y = 32
            self.wall_list.append(wall)

        # Платформа 1 - стартовая
        for x in range(0, 300, 64):
            wall = arcade.Sprite(":resources:images/tiles/grassMid.png", TILE_SCALING)
            wall.center_x = x
            wall.center_y = 200
            self.wall_list.append(wall)

        # Платформа 2 - с первым врагом
        for x in range(400, 600, 64):
            wall = arcade.Sprite(":resources:images/tiles/grassMid.png", TILE_SCALING)
            wall.center_x = x
            wall.center_y = 250
            self.wall_list.append(wall)

        # Добавляем первого врага на платформу 2
        worm1 = WormEnemy()
        worm1.center_x = 500
        worm1.center_y = 270 + 32  # На платформе
        self.enemy_list.append(worm1)

        # Платформа 3 - опасная, с двумя врагами
        for x in range(700, 1000, 64):
            wall = arcade.Sprite(":resources:images/tiles/grassMid.png", TILE_SCALING)
            wall.center_x = x
            wall.center_y = 320
            self.wall_list.append(wall)

        # Два врага на платформе 3
        worm2 = WormEnemy()
        worm2.center_x = 780
        worm2.center_y = 340 + 32
        worm2.move_range = 80  # Меньший диапазон
        self.enemy_list.append(worm2)

        worm3 = WormEnemy()
        worm3.center_x = 920
        worm3.center_y = 340 + 32
        worm3.move_range = 50
        worm3.move_direction = -1  # Начинает движение влево
        self.enemy_list.append(worm3)

        # Платформа 4 - высокая, нужно прыгать
        for x in range(1100, 1300, 64):
            wall = arcade.Sprite(":resources:images/tiles/grassMid.png", TILE_SCALING)
            wall.center_x = x
            wall.center_y = 420
            self.wall_list.append(wall)

        # Враг на высокой платформе
        worm4 = WormEnemy()
        worm4.center_x = 1200
        worm4.center_y = 440 + 32
        worm4.move_speed = 2.0  # Быстрее
        self.enemy_list.append(worm4)

        # Платформа 5 - движущаяся к двери
        for x in range(1450, 1600, 64):
            wall = arcade.Sprite(":resources:images/tiles/grassMid.png", TILE_SCALING)
            wall.center_x = x
            wall.center_y = 350
            self.wall_list.append(wall)

        # Платформа 6 - перед дверью
        for x in range(1800, 2000, 64):
            wall = arcade.Sprite(":resources:images/tiles/grassMid.png", TILE_SCALING)
            wall.center_x = x
            wall.center_y = 280
            self.wall_list.append(wall)

        # Последний враг перед дверью
        worm5 = WormEnemy()
        worm5.center_x = 1900
        worm5.center_y = 300 + 32
        self.enemy_list.append(worm5)

        # Платформа перед дверью
        for x in range(2150, 2250, 64):
            wall = arcade.Sprite(":resources:images/tiles/grassMid.png", TILE_SCALING)
            wall.center_x = x
            wall.center_y = 120
            self.wall_list.append(wall)

        for y in range(180, 450, 64):
            ladder = arcade.Sprite(":resources:images/tiles/ladderMid.png", TILE_SCALING)
            ladder.center_x = 1350
            ladder.center_y = y
            self.ladder_list.append(ladder)

        # Создаем монеты
        coin_positions = [
            (250, 250),  # На первой платформе
            (550, 300),  # Над первым врагом
            (850, 370),  # На опасной платформе
            (1150, 470),  # На высокой платформе
            (1250, 470),  # На высокой платформе
            (1500, 400),  # На платформе к двери
            (1700, 330),  # Перед последним врагом
            (1950, 330),  # После последнего врага
            (2000, 330),  # Вторая монета на той же платформе
            (2100, 170),  # Перед дверью
        ]

        for x, y in coin_positions:
            coin = arcade.Sprite(":resources:images/items/coinGold.png", COIN_SCALING)
            coin.center_x = x
            coin.center_y = y
            self.coin_list.append(coin)

        # Добавляем опасные шипы
        spike_positions = [
            (1600, 95),
            (1632, 95),
            (1664, 95),
            (1696, 95),
            (1728, 95),
        ]

        for x, y in spike_positions:
            spike = Spike()
            spike.center_x = x
            spike.center_y = y
            self.spike_list.append(spike)

        # Устанавливаем конец карты
        self.end_of_map = 2500

        # Устанавливаем цвет фона (более мрачный для уровня 2)
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_GRAY)

        # Создаем физический движок
        self.physics_engine = PhysicsEnginePlatformer(
            player_sprite=self.player_sprite,
            gravity_constant=GRAVITY,
            walls=self.wall_list,
            ladders=self.ladder_list
        )

    def on_draw(self):
        """ Отрисовка экрана. """
        # Очищаем экран
        self.clear()

        # Используем мировую камеру для игровых объектов
        self.world_camera.use()

        # Отрисовываем спрайты
        self.wall_list.draw()
        self.background_list.draw()
        self.ladder_list.draw()
        self.coin_list.draw()
        self.door_list.draw()
        self.enemy_list.draw()
        self.spike_list.draw()

        self.player_list.draw()

        # Отрисовываем счет над головой игрока
        self.player_sprite.draw_score()

        # Отрисовываем плавающие тексты "+10"
        for text in self.floating_texts:
            text.draw()

        # Переключаемся на камеру интерфейса
        self.gui_camera.use()

        # --- ОТРИСОВКА СТАРТОВОГО ИНТРО ---
        if self.show_intro:
            p = self.intro_timer / self.intro_duration

            if p < 0.3:
                alpha = int(255 * (p / 0.3))
            elif p > 0.7:
                alpha = int(255 * (1 - (p - 0.7) / 0.3))
            else:
                alpha = 255

            color = (255, 255, 255, alpha)

            arcade.draw_lrbt_rectangle_filled(
                0, SCREEN_WIDTH, 0, SCREEN_HEIGHT,
                (0, 0, 0, 180)
            )

            arcade.draw_text(
                "Level 2: Прогулка в лесу",
                SCREEN_WIDTH // 2,
                SCREEN_HEIGHT // 2 + 40,
                color,
                42,
                bold=True,
                anchor_x="center",
                anchor_y="center"
            )

            arcade.draw_text(
                "Избегайте опасности и доберитесь до конца!",
                SCREEN_WIDTH // 2,
                SCREEN_HEIGHT // 2 - 20,
                (255, 100, 100, alpha),
                26,
                anchor_x="center",
                anchor_y="center"
            )
            arcade.draw_text(
                "Интересный факт: Собрав все монеты на карте вы наберёте 100 поинтов!",
                SCREEN_WIDTH // 2,
                SCREEN_HEIGHT // 3 - 20,
                (230, 214, 144, alpha),
                15,
                anchor_x="center",
                anchor_y="center"
            )
            arcade.draw_text(
                "Уровень загружается...",
                SCREEN_WIDTH - 100,
                SCREEN_HEIGHT // 10 - 20,
                (255, 215, 0, alpha),
                10,
                anchor_x="center",
                anchor_y="center"
            )

        # --- Рисуем номер уровня сверху ---
        arcade.draw_text(
            "Level: 2",
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 50,
            arcade.color.YELLOW,
            24,
            bold=True,
            anchor_x="center"
        )

        # Таймер игры (если игра началась)
        if self.game_start_time and not self.level_complete_view and not self.game_over_view:
            current_time = time.time()
            play_time_seconds = current_time - self.game_start_time
            play_time_minutes = play_time_seconds / 60.0

            # Рисуем таймер в верхнем правом углу
            timer_text = f"Время: {play_time_seconds:.1f} сек"
            arcade.draw_text(
                timer_text,
                SCREEN_WIDTH - 150,
                SCREEN_HEIGHT - 50,
                arcade.color.WHITE,
                16,
                bold=True,
                anchor_x="center"
            )

        # Подсказка для двери (если игрок рядом)
        if self.show_door_hint and self.door_hint_timer > 0 and not self.game_over_view:
            hint_x = SCREEN_WIDTH // 2
            hint_y = SCREEN_HEIGHT - 100

            # Фон подсказки
            arcade.draw_lrbt_rectangle_filled(
                hint_x - 250, hint_x + 250,
                hint_y - 30, hint_y + 30,
                arcade.color.BLACK
            )

            # Рамка
            arcade.draw_lrbt_rectangle_outline(
                hint_x - 250, hint_x + 250,
                hint_y - 30, hint_y + 30,
                arcade.color.YELLOW,
                2
            )

            # Текст подсказки
            arcade.draw_text(
                "Нажмите ПРАВУЮ кнопку мыши у двери для завершения уровня",
                hint_x,
                hint_y,
                arcade.color.YELLOW,
                14,
                bold=True,
                anchor_x="center",
                anchor_y="center"
            )

        # Отрисовка вью завершения уровня
        if self.level_complete_view:
            self.level_complete_view.draw()

        # Отрисовка вью проигрыша
        if self.game_over_view:
            self.game_over_view.draw()

    def process_movement(self):
        """Обработка движения игрока"""
        if self.level_complete_view or self.game_over_view:
            return

        if self.right and not self.left:
            self.player_sprite.change_x = PLAYER_MOVEMENT_SPEED
        elif self.left and not self.right:
            self.player_sprite.change_x = -PLAYER_MOVEMENT_SPEED
        else:
            self.player_sprite.change_x = 0

        if self.physics_engine.is_on_ladder():
            if self.up_pressed and not self.down_pressed:
                self.player_sprite.change_y = PLAYER_MOVEMENT_SPEED
            elif self.down_pressed and not self.up_pressed:
                self.player_sprite.change_y = -PLAYER_MOVEMENT_SPEED
            elif not self.up_pressed and not self.down_pressed:
                self.player_sprite.change_y = 0

    def on_key_press(self, key, modifiers):
        """Вызывается при нажатии клавиши. """
        if self.level_complete_view or self.game_over_view:
            return

        if self.player_frozen:
            return
        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = True
            if self.can_jump_again:
                self.jump = True
                self.jump_buffer_timer = JUMP_BUFFER

        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = True
            self.down = True
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = True
            self.left = True
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = True
            self.right = True

        self.process_movement()

    def on_key_release(self, key, modifiers):
        """Вызывается при отпускании клавиши. """
        if self.level_complete_view or self.game_over_view:
            return

        if self.player_frozen:
            return
        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = False
            self.jump = False
            if self.player_sprite.change_y > 0:
                self.player_sprite.change_y *= 0.45
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = False
            self.down = False
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = False
            self.left = False
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = False
            self.right = False

        self.process_movement()

    def on_mouse_motion(self, x, y, dx, dy):
        """Отслеживает движение мыши"""
        self._mouse_x = x
        self._mouse_y = y

    def on_mouse_press(self, x, y, button, modifiers):
        """Обрабатывает нажатие мыши"""
        if self.level_complete_view:
            self.level_complete_view.on_mouse_press(x, y, button, modifiers)
            return

        if self.game_over_view:
            self.game_over_view.on_mouse_press(x, y, button, modifiers)
            return

        if button == arcade.MOUSE_BUTTON_RIGHT and self.door:
            dx = self.player_sprite.center_x - self.door.center_x
            dy = self.player_sprite.center_y - self.door.center_y
            distance = math.hypot(dx, dy)

            if distance < self.door.interaction_radius:
                self.complete_level()

    def create_floating_text(self, text):
        """Создает эффект плавающего текста"""
        floating_text = FloatingText(text, self.player_sprite)
        self.floating_texts.append(floating_text)

    def complete_level(self):
        """Завершает уровень и показывает экран завершения"""
        if not self.level_complete_view and not self.game_over_view:
            # Рассчитываем время игры в секундах
            if self.game_start_time:
                current_time = time.time()
                play_time_seconds = current_time - self.game_start_time
            else:
                play_time_seconds = 0.0

            # Используем громкость из БД для звука открытия двери
            self.play_sound_with_db_volume(self.door_open_sound, 'door_open')

            self.level_complete_view = Level2CompleteView(
                self.window,
                self.player_sprite.score,
                play_time_seconds
            )
            self.player_frozen = True
            self.player_sprite.change_x = 0
            self.player_sprite.change_y = 0

    def game_over(self):
        """Проигрыш - игрок коснулся врага или шипов"""
        if not self.game_over_view and not self.level_complete_view:
            # Останавливаем музыку уровня
            if self.music_player:
                self.music_player.pause()
                self.music_player = None

            # Проигрываем звук поражения
            self.play_sound_with_db_volume(self.game_over_sound, 'game_over')

            self.game_over_view = GameOverView(self.window, MyGame)
            self.player_frozen = True
            self.player_sprite.change_x = 0
            self.player_sprite.change_y = 0

    def on_update(self, delta_time):
        """ Обновление игровой логики и движения """
        if self.level_complete_view:
            self.level_complete_view.update(delta_time)
            return

        if self.game_over_view:
            self.game_over_view.update(delta_time)
            return

        if self.show_intro:
            self.intro_timer += delta_time

            if self.intro_timer >= self.intro_duration:
                self.show_intro = False
                self.player_frozen = False

                # Запускаем таймер игры
                self.game_start_time = time.time()

                if self.music_player:
                    self.music_player.pause()
                    self.music_player = None

            self.player_sprite.change_x = 0
            self.player_sprite.change_y = 0

            self.physics_engine.update()
            self.player_list.update_animation(delta_time)
            return

        # Проверяем близость к двери для показа подсказки
        if self.door and not self.level_complete_view and not self.game_over_view:
            dx = self.player_sprite.center_x - self.door.center_x
            dy = self.player_sprite.center_y - self.door.center_y
            distance = math.hypot(dx, dy)

            if distance < self.door.interaction_radius * 2:
                self.show_door_hint = True
                self.door_hint_timer = 3.0
            else:
                self.door_hint_timer -= delta_time
                if self.door_hint_timer <= 0:
                    self.show_door_hint = False

        # Обновляем врагов
        for enemy in self.enemy_list:
            if isinstance(enemy, WormEnemy):
                enemy.update_animation(delta_time)
                enemy.update_movement()

        # Проверяем столкновения с врагами
        enemy_hit_list = arcade.check_for_collision_with_list(self.player_sprite, self.enemy_list)
        if enemy_hit_list:
            self.game_over()

        # Проверяем столкновения с шипами
        spike_hit_list = arcade.check_for_collision_with_list(self.player_sprite, self.spike_list)
        if spike_hit_list:
            self.game_over()

        # Обрабатываем движение
        self.process_movement()

        if self.jump_cooldown > 0:
            self.jump_cooldown -= delta_time
            if self.jump_cooldown <= 0:
                self.can_jump_again = True

        self.physics_engine.update()

        if self.physics_engine.can_jump():
            self.player_sprite.can_jump = False
        else:
            self.player_sprite.can_jump = True

        if self.physics_engine.is_on_ladder() and not self.physics_engine.can_jump():
            self.player_sprite.is_on_ladder = True
        else:
            self.player_sprite.is_on_ladder = False

        grounded = self.physics_engine.can_jump(y_distance=6)
        if grounded:
            self.time_since_ground = 0
            self.jumps_left = MAX_JUMPS
            self.can_jump_again = True
        else:
            self.time_since_ground += delta_time

        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= delta_time

        want_jump = self.jump or (self.jump_buffer_timer > 0)

        if want_jump and self.can_jump_again:
            can_coyote = (self.time_since_ground <= COYOTE_TIME)
            if grounded or can_coyote:
                self.physics_engine.jump(PLAYER_JUMP_SPEED)
                self.jump_buffer_timer = 0
                # Просто воспроизводим звук прыжка со стандартной громкостью
                arcade.play_sound(self.jump_sound, volume=0.7)
                self.jump_cooldown = 0.3
                self.can_jump_again = False
                self.jump = False

        self.coin_list.update_animation(delta_time)
        self.player_list.update_animation(delta_time)
        self.wall_list.update()

        self.floating_texts = [text for text in self.floating_texts if text.update(delta_time)]

        coin_hit_list = arcade.check_for_collision_with_list(self.player_sprite,
                                                             self.coin_list)

        for coin in coin_hit_list:
            points = 10
            self.player_sprite.add_score(points)
            self.create_floating_text(f"+{points}")
            coin.remove_from_sprite_lists()
            # Просто воспроизводим звук сбора монеты со стандартной громкостью
            arcade.play_sound(self.collect_coin_sound, volume=0.7)

        target_x = self.player_sprite.center_x
        target_y = self.player_sprite.center_y

        current_x, current_y = self.world_camera.position

        smooth_x = current_x + (target_x - current_x) * CAMERA_LERP
        smooth_y = current_y + (target_y - current_y) * CAMERA_LERP

        half_width = SCREEN_WIDTH / 2
        half_height = SCREEN_HEIGHT / 2

        world_width = self.end_of_map
        world_height = 1000

        cam_x = max(half_width, min(world_width - half_width, smooth_x))
        cam_y = max(half_height, min(world_height - half_height, smooth_y))

        self.world_camera.position = (cam_x, cam_y)
        self.gui_camera.position = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)


def main():
    """ Главная функция """
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    game = MyGame()
    game.setup()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()
