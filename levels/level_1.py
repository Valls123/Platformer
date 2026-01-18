"""
Платформер
"""
import arcade
import os
import math
import random
import sqlite3
import time
from arcade.camera import Camera2D
from arcade import PhysicsEnginePlatformer

# Константы
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 650
SCREEN_TITLE = "Приключения Джо: Platformer - Уровень 1: Обучение"

# Константы для масштабирования спрайтов
TILE_SCALING = 0.5
CHARACTER_SCALING = TILE_SCALING * 2
COIN_SCALING = TILE_SCALING
DOOR_SCALING = TILE_SCALING * 1.5
SPRITE_PIXEL_SIZE = 128
GRID_PIXEL_SIZE = (SPRITE_PIXEL_SIZE * TILE_SCALING)

# Физика и движение
GRAVITY = 1.5  # Гравитация в пикс/с^2
PLAYER_MOVEMENT_SPEED = 7  # Скорость движения в пикс/с
PLAYER_JUMP_SPEED = 30  # Начальная скорость прыжка в пикс/с

# Улучшения управления
COYOTE_TIME = 0.08  # Время после схода с платформы, когда еще можно прыгнуть
JUMP_BUFFER = 0.12  # Если нажали прыжок чуть раньше приземления, запоминаем
MAX_JUMPS = 1  # Количество прыжков (1 = без двойного прыжка)

# Настройки камеры
CAMERA_LERP = 0.12  # Плавность движения камеры

# Стартовая позиция игрока
PLAYER_START_X = SPRITE_PIXEL_SIZE * TILE_SCALING * 2
PLAYER_START_Y = SPRITE_PIXEL_SIZE * TILE_SCALING * 1

# Позиция двери
DOOR_X = 1900  # Правая часть карты
DOOR_Y = 120  # На уровне земли

# Направление взгляда персонажа
RIGHT_FACING = 0
LEFT_FACING = 1


def load_texture_pair(filename):
    """
    Загружает пару текстур: оригинальную и зеркальную.
    """
    texture = arcade.load_texture(filename)
    flipped_texture = texture.flip_horizontally()

    return [texture, flipped_texture]


class SoundDatabase:
    """Менеджер базы данных звуков SQLite"""

    def __init__(self, db_name=None):
        from pathlib import Path

        if db_name is None:
            current_dir = Path(__file__).parent  # папка levels
            base_dir = current_dir.parent
            db_name = str(base_dir / "sounds.db")

        self.db_name = db_name
        self.init_database()

    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Создаем таблицу для настроек звуков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sound_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sound_type TEXT NOT NULL,
                volume REAL NOT NULL,
                is_enabled INTEGER DEFAULT 1,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(sound_type)
            )
        ''')

        # Вставляем начальные значения, если их нет
        default_settings = [
            ('music', 0.5),
            ('ui_click', 0.8),
            ('environment', 0.6),
            ('door_open', 0.7),  # Громкость открытия двери
            ('game_over', 0.6)  # Громкость проигрыша
        ]

        for sound_type, volume in default_settings:
            cursor.execute('''
                INSERT OR IGNORE INTO sound_settings (sound_type, volume)
                VALUES (?, ?)
            ''', (sound_type, volume))

        conn.commit()
        conn.close()

    def get_volume(self, sound_type):
        """Получает громкость для типа звука"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT volume, is_enabled FROM sound_settings WHERE sound_type = ?
        ''', (sound_type,))

        result = cursor.fetchone()
        conn.close()

        if result:
            volume, is_enabled = result
            return volume if is_enabled else 0.0
        return 0.5

    def set_volume(self, sound_type, volume):
        """Устанавливает громкость для типа звука"""
        volume = max(0.0, min(1.0, volume))  # Ограничиваем от 0 до 1

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE sound_settings 
            SET volume = ?, last_updated = CURRENT_TIMESTAMP
            WHERE sound_type = ?
        ''', (volume, sound_type))

        conn.commit()
        conn.close()

    def get_all_settings(self):
        """Получает все настройки звуков"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT sound_type, volume, is_enabled FROM sound_settings
        ''')

        settings = {}
        for sound_type, volume, is_enabled in cursor.fetchall():
            settings[sound_type] = {
                'volume': volume,
                'enabled': bool(is_enabled)
            }

        conn.close()
        return settings

    def enable_sound(self, sound_type, enabled=True):
        """Включает или выключает звук"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE sound_settings 
            SET is_enabled = ?, last_updated = CURRENT_TIMESTAMP
            WHERE sound_type = ?
        ''', (1 if enabled else 0, sound_type))

        conn.commit()
        conn.close()


class DatabaseManager:
    """Менеджер базы данных SQLite"""

    def __init__(self, db_name=None):
        from pathlib import Path

        if db_name is None:
            current_dir = Path(__file__).parent  # папка levels
            base_dir = current_dir.parent
            db_name = str(base_dir / "game_stats.db")

        self.db_name = db_name
        self.init_database()

    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Создаем таблицу для статистики игроков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                level INTEGER NOT NULL,
                score INTEGER NOT NULL,
                play_time_seconds REAL NOT NULL,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Создаем таблицу для результатов уровней
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS level_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                level_number INTEGER NOT NULL,
                score INTEGER NOT NULL,
                completed INTEGER DEFAULT 0,
                play_time_seconds REAL DEFAULT 0,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Создаем индексы для быстрого поиска
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_player_level 
            ON level_results (player_id, level_number)
        ''')

        conn.commit()
        conn.close()

    def save_level_result(self, player_id, level, score, play_time_seconds):
        """Сохраняет результат прохождения уровня"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Обновляем или вставляем результат уровня
        cursor.execute('''
            INSERT OR REPLACE INTO level_results 
            (player_id, level_number, score, completed, play_time_seconds, completed_at)
            VALUES (?, ?, ?, 1, ?, CURRENT_TIMESTAMP)
        ''', (player_id, level, score, play_time_seconds))

        conn.commit()
        conn.close()

    def get_player_stats(self, player_id):
        """Получает статистику игрока"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT level, score, play_time_seconds, completed_at
            FROM level_results 
            WHERE player_id = ?
            ORDER BY completed_at DESC
        ''', (player_id,))

        stats = cursor.fetchall()
        conn.close()

        return stats

    def get_completed_levels_count(self, player_id="player_1"):
        """Получает количество пройденных уровней"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(DISTINCT level_number) 
            FROM level_results 
            WHERE player_id = ? AND completed = 1
        ''', (player_id,))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else 0

    def get_level_best_score(self, player_id, level):
        """Получает лучший счет для уровня"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT MAX(score) FROM level_results 
            WHERE player_id = ? AND level_number = ?
        ''', (player_id, level))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result and result[0] else 0


class PlayerCharacter(arcade.Sprite):
    """ Спрайт игрока """

    def __init__(self):
        # Инициализация родительского класса
        super().__init__()

        # Направление взгляда по умолчанию - вправо
        self.character_face_direction = RIGHT_FACING

        # Для анимации
        self.cur_texture = 0
        self.scale = CHARACTER_SCALING

        # Состояния персонажа
        self.jumping = False
        self.climbing = False
        self.is_on_ladder = False

        # Очки игрока, отображаемые над головой
        self.score = 0
        self.score_text = None

        # --- Загрузка текстур ---
        main_path = ":resources:images/animated_characters/male_person/malePerson"

        # Текстуры для стояния на месте
        self.idle_texture_pair = load_texture_pair(f"{main_path}_idle.png")
        self.jump_texture_pair = load_texture_pair(f"{main_path}_jump.png")
        self.fall_texture_pair = load_texture_pair(f"{main_path}_fall.png")

        # Текстуры для ходьбы
        self.walk_textures = []
        for i in range(8):
            texture = load_texture_pair(f"{main_path}_walk{i}.png")
            self.walk_textures.append(texture)

        # Текстуры для лазания по лестнице
        self.climbing_textures = []
        texture = arcade.load_texture(f"{main_path}_climb0.png")
        self.climbing_textures.append(texture)
        texture = arcade.load_texture(f"{main_path}_climb1.png")
        self.climbing_textures.append(texture)

        # Устанавливаем начальную текстуру
        self.texture = self.idle_texture_pair[0]

    def update_animation(self, delta_time: float = 1 / 60):
        """Обновление анимации персонажа"""
        # Определяем направление взгляда
        if self.change_x < 0 and self.character_face_direction == RIGHT_FACING:
            self.character_face_direction = LEFT_FACING
        elif self.change_x > 0 and self.character_face_direction == LEFT_FACING:
            self.character_face_direction = RIGHT_FACING

        # Анимация лазания по лестнице
        if self.is_on_ladder:
            self.climbing = True
        if not self.is_on_ladder and self.climbing:
            self.climbing = False
        if self.climbing and abs(self.change_y) > 1:
            self.cur_texture += 1
            if self.cur_texture > 7:
                self.cur_texture = 0
        if self.climbing:
            self.texture = self.climbing_textures[self.cur_texture // 4]
            return

        # Анимация прыжка
        if self.change_y > 0 and not self.is_on_ladder:
            self.texture = self.jump_texture_pair[self.character_face_direction]
            return
        elif self.change_y < 0 and not self.is_on_ladder:
            self.texture = self.fall_texture_pair[self.character_face_direction]
            return

        # Анимация стояния на месте
        if self.change_x == 0:
            self.texture = self.idle_texture_pair[self.character_face_direction]
            return

        # Анимация ходьбы
        self.cur_texture += 1
        if self.cur_texture > 7:
            self.cur_texture = 0
        self.texture = self.walk_textures[self.cur_texture][self.character_face_direction]

    def add_score(self, points):
        """Добавляет очки к счету игрока"""
        self.score += points

    def draw_score(self):
        """Отрисовывает счет над головой игрока"""
        if self.score_text is None:
            self.score_text = arcade.Text(
                f"Очки: {self.score}",
                self.center_x,
                self.top + 20,
                arcade.color.YELLOW,
                14,
                bold=True,
                anchor_x="center"
            )
        else:
            self.score_text.text = f"Points: {self.score}"
            self.score_text.x = self.center_x
            self.score_text.y = self.top + 20

        # Получаем размеры текста
        text_width = self.score_text.content_width
        text_height = self.score_text.content_height

        # Рисуем фон для лучшей видимости
        left = self.center_x - (text_width + 10) // 2
        right = self.center_x + (text_width + 10) // 2
        bottom = (self.top + 20) - (text_height + 6) // 2
        top = (self.top + 20) + (text_height + 6) // 2

        arcade.draw_lrbt_rectangle_filled(
            left, right, bottom, top,
            arcade.color.BLACK
        )

        # Рисуем рамку
        arcade.draw_lrbt_rectangle_outline(
            left, right, bottom, top,
            arcade.color.WHITE,
            2
        )

        # Рисуем текст счета
        self.score_text.draw()


class FloatingText:
    """Текст, который всплывает над спрайтом и исчезает"""

    def __init__(self, text, sprite, color=arcade.color.GREEN, font_size=16):
        self.sprite = sprite
        self.text = arcade.Text(
            text,
            sprite.center_x,
            sprite.top + 30,
            color,
            font_size,
            bold=True,
            anchor_x="center"
        )
        self.lifetime = 1.0
        self.timer = 0.0

    def update(self, delta_time):
        """Обновляет позицию и время жизни"""
        self.text.x = self.sprite.center_x
        self.text.y += 1
        self.timer += delta_time
        return self.timer < self.lifetime

    def draw(self):
        """Отрисовывает текст"""
        self.text.draw()


class ConfettiParticle:
    """Частица для эффекта салюта"""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = random.randint(3, 8)
        self.velocity_x = random.uniform(-3, 3)
        self.velocity_y = random.uniform(2, 8)
        self.gravity = 0.2
        self.lifetime = random.uniform(1.0, 2.5)
        self.timer = 0.0

        # Случайный цвет для разнообразия
        colors = [
            (255, 0, 0),  # RED
            (0, 0, 255),  # BLUE
            (0, 255, 0),  # GREEN
            (255, 255, 0),  # YELLOW
            (128, 0, 128),  # PURPLE
            (255, 165, 0),  # ORANGE
            (255, 192, 203),  # PINK
            (0, 255, 255)  # CYAN
        ]
        self.color = colors[random.randint(0, len(colors) - 1)]

    def update(self, delta_time):
        """Обновляет частицу"""
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.velocity_y -= self.gravity
        self.timer += delta_time
        return self.timer < self.lifetime

    def draw(self):
        """Рисует частицу"""
        alpha = int(255 * (1 - self.timer / self.lifetime))

        rgba_color = (
            self.color[0],
            self.color[1],
            self.color[2],
            alpha
        )

        arcade.draw_circle_filled(
            self.x, self.y, self.size,
            rgba_color
        )


class Door(arcade.Sprite):
    """Дверь для завершения уровня"""

    def __init__(self):
        super().__init__()
        self.texture = arcade.load_texture(":resources:images/tiles/doorClosed_mid.png")
        self.scale = DOOR_SCALING
        self.is_open = False
        self.interaction_radius = 50
        self.show_interaction_hint = False


class LevelCompleteView:
    """Вью для завершения уровня"""

    def __init__(self, window, score, play_time_seconds, current_level=1):
        self.window = window
        self.score = score
        self.play_time_seconds = play_time_seconds
        self.current_level = current_level
        self.alpha = 0
        self.particles = []
        self.show_exit_button = False
        self.exit_button_rect = None
        self.level_saved = False

        # Создаем частицы салюта
        for _ in range(100):
            x = random.randint(200, SCREEN_WIDTH - 200)
            y = random.randint(100, SCREEN_HEIGHT - 100)
            self.particles.append(ConfettiParticle(x, y))

        # Сохраняем результат сразу при создании вью
        self.save_to_database()

    def save_to_database(self):
        """Сохраняет результат уровня в базу данных"""
        import sqlite3
        from pathlib import Path

        try:
            # Определяем путь к основной папке с БД
            current_dir = Path(__file__).parent  # папка levels
            base_dir = current_dir.parent  # основная папка проекта
            db_path = base_dir / "game_stats.db"

            print(f"\n=== СОХРАНЕНИЕ ПРОГРЕССА УРОВНЯ {self.current_level} ===")
            print(f"Путь к БД: {db_path}")

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Вставляем результат уровня
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

            print(f"Игрок: {player_id}")
            print(f"Счет: {self.score}")
            print(f"Время: {self.play_time_seconds:.1f} секунд")
            print("=" * 50)

        except Exception as e:
            print(f"❌ Ошибка при сохранении в БД: {e}")
            import traceback
            traceback.print_exc()

    def update(self, delta_time):
        """Обновляет анимацию завершения уровня"""
        # Плавное появление
        if self.alpha < 255:
            self.alpha = min(255, self.alpha + 5)

        # Обновляем частицы
        self.particles = [p for p in self.particles if p.update(delta_time)]

        # Добавляем новые частицы
        if len(self.particles) < 50:
            x = random.randint(200, SCREEN_WIDTH - 200)
            y = random.randint(100, SCREEN_HEIGHT - 100)
            self.particles.append(ConfettiParticle(x, y))

        # Показываем кнопку через 1 секунду
        if self.alpha >= 255:
            self.show_exit_button = True

        # Определяем прямоугольник кнопки
        button_width = 300
        button_height = 60
        self.exit_button_rect = (
            SCREEN_WIDTH // 2 - button_width // 2,
            SCREEN_HEIGHT // 2 - 100 - button_height // 2,
            button_width,
            button_height
        )

    def draw(self):
        """Рисует экран завершения уровня"""
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
        container_height = 350
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
            "УРОВЕНЬ ПРОЙДЕН!",
            container_x,
            container_y + 80,
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
            container_y + 30,
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
            container_y - 20,
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

        # Сообщение о сохранении
        if self.level_saved:
            arcade.draw_text(
                "Прогресс сохранен!",
                container_x,
                container_y - 100,
                (0, 255, 0, self.alpha),
                24,
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
                24,
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


class MyGame(arcade.Window):
    """
    Главный класс игры
    """

    def __init__(self):
        """
        Инициализатор игры
        """
        # инициализация БД звуков
        self.sound_db = SoundDatabase()

        # интро
        self.show_intro = True
        self.intro_timer = 0.0
        self.intro_duration = 6.0

        # заморозка игрока
        self.player_frozen = True

        # музыка
        sound_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  "assets", "sounds", "intro_level_1.mp3")

        # Загружаем звук
        self.intro_sound = arcade.load_sound(sound_path)

        # Загружаем громкость музыки из БД
        music_volume = self.sound_db.get_volume('music')
        self.intro_player = arcade.play_sound(self.intro_sound, volume=music_volume, loop=False)

        # Вью завершения уровня
        self.level_complete_view = None

        # Отслеживание позиции мыши
        self._mouse_x = 0
        self._mouse_y = 0

        # Таймер для отслеживания времени игры
        self.game_start_time = None
        self.total_play_time_seconds = 0.0

        # Номер текущего уровня
        self.current_level = 1

        # Вызываем родительский класс и настраиваем окно
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        # Устанавливаем путь к программе
        file_path = os.path.dirname(os.path.abspath(__file__))
        os.chdir(file_path)

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
        self.game_over = arcade.load_sound(":resources:sounds/gameover1.wav")
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

        # --- Создаем простой уровень вручную ---
        # Создаем землю
        for x in range(0, 2000, 64):
            wall = arcade.Sprite(":resources:images/tiles/grassMid.png", TILE_SCALING)
            wall.center_x = x
            wall.center_y = 32
            self.wall_list.append(wall)

        # Создаем платформы
        for x in range(300, 600, 64):
            wall = arcade.Sprite(":resources:images/tiles/grassMid.png", TILE_SCALING)
            wall.center_x = x
            wall.center_y = 200
            self.wall_list.append(wall)

        for x in range(700, 1000, 64):
            wall = arcade.Sprite(":resources:images/tiles/grassMid.png", TILE_SCALING)
            wall.center_x = x
            wall.center_y = 300
            self.wall_list.append(wall)

        # Платформа перед дверью
        for x in range(1850, 1950, 64):
            wall = arcade.Sprite(":resources:images/tiles/grassMid.png", TILE_SCALING)
            wall.center_x = x
            wall.center_y = 120
            self.wall_list.append(wall)

        # Создаем монеты
        for x in range(200, 1200, 100):
            coin = arcade.Sprite(":resources:images/items/coinGold.png", COIN_SCALING)
            coin.center_x = x
            coin.center_y = 150
            self.coin_list.append(coin)

        # Создаем лестницу
        for y in range(80, 400, 64):
            ladder = arcade.Sprite(":resources:images/tiles/ladderMid.png", TILE_SCALING)
            ladder.center_x = 630
            ladder.center_y = y
            self.ladder_list.append(ladder)

        # Устанавливаем конец карты
        self.end_of_map = 2000

        # Устанавливаем цвет фона
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)

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
                "Добро пожаловать",
                SCREEN_WIDTH // 2,
                SCREEN_HEIGHT // 2 + 40,
                color,
                42,
                bold=True,
                anchor_x="center",
                anchor_y="center"
            )

            arcade.draw_text(
                "Level 1: Обучение",
                SCREEN_WIDTH // 2,
                SCREEN_HEIGHT // 2 - 20,
                color,
                26,
                anchor_x="center",
                anchor_y="center"
            )

        # --- Рисуем гайд по управлению в небе ---
        guide_x = SCREEN_WIDTH // 2
        guide_y = SCREEN_HEIGHT - 100

        # Фон для гайда
        arcade.draw_lrbt_rectangle_filled(
            guide_x - 200, guide_x + 200,
            guide_y - 40, guide_y + 40,
            arcade.color.BLACK
        )

        # Рамка
        arcade.draw_lrbt_rectangle_outline(
            guide_x - 200, guide_x + 200,
            guide_y - 40, guide_y + 40,
            arcade.color.WHITE,
            2
        )

        # Текст управления
        control_text = " ❗ ← → Движение | W/↑ Прыжок | S/↓ Вниз"
        arcade.draw_text(
            control_text,
            guide_x,
            guide_y,
            arcade.color.YELLOW,
            15,
            bold=True,
            anchor_x="center",
            anchor_y="center"
        )

        # Текст задачи
        task_text = "Соберите монеты и найдите дверь в конце!"
        arcade.draw_text(
            task_text,
            guide_x,
            guide_y - 70,
            arcade.color.LIGHT_BLUE,
            16,
            bold=True,
            anchor_x="center",
            anchor_y="center"
        )

        # Таймер игры (если игра началась)
        if self.game_start_time and not self.level_complete_view:
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
        if self.show_door_hint and self.door_hint_timer > 0:
            hint_x = SCREEN_WIDTH // 2
            hint_y = SCREEN_HEIGHT - 150

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

    def process_movement(self):
        """Обработка движения игрока"""
        if self.level_complete_view:
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
        if self.level_complete_view:
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
        if self.level_complete_view:
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
        if not self.level_complete_view:
            # Рассчитываем время игры в секундах
            if self.game_start_time:
                current_time = time.time()
                play_time_seconds = current_time - self.game_start_time
            else:
                play_time_seconds = 0.0

            # Используем громкость из БД для звука открытия двери
            self.play_sound_with_db_volume(self.door_open_sound, 'door_open')

            # Создаем экран завершения уровня
            self.level_complete_view = LevelCompleteView(
                self,
                self.player_sprite.score,
                play_time_seconds,
                self.current_level
            )
            self.player_frozen = True
            self.player_sprite.change_x = 0
            self.player_sprite.change_y = 0

    def on_update(self, delta_time):
        """ Обновление игровой логики и движения """
        if self.level_complete_view:
            self.level_complete_view.update(delta_time)
            return

        if self.show_intro:
            self.intro_timer += delta_time

            if self.intro_timer >= self.intro_duration:
                self.show_intro = False
                self.player_frozen = False

                # Запускаем таймер игры
                self.game_start_time = time.time()

                if self.intro_player:
                    self.intro_player.pause()
                    self.intro_player = None

            self.player_sprite.change_x = 0
            self.player_sprite.change_y = 0

            self.physics_engine.update()
            self.player_list.update_animation(delta_time)
            return

        # Проверяем близость к двери для показа подсказки
        if self.door and not self.level_complete_view:
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
    window = MyGame()
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()
