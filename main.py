import arcade
import arcade.gui as gui
import os
import sqlite3

# Настройки экрана
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
SCREEN_TITLE = "Приключения Джо: Platformer"

# Пути к файлам
MENU_BG = "assets/images/3858.jpg"
MUSIC_FILE = "assets/sounds/Music.mp3"
CLICK_SOUND_FILE = "assets/sounds/click_button.mp3"
LEVEL_1_FILE = "levels/level_1.py"
LEVEL_2_FILE = "levels/level_2.py"
LEVEL_3_FILE = "levels/level_3.py"
SOUNDS_DB = "sounds.db"
GAME_STATS_DB = "game_stats.db"

# Константы игры
GRAVITY = 1.0
PLAYER_SPEED = 5
PLAYER_JUMP = 15


# Система базы данных звуков
class SoundDatabase:
    def __init__(self, db_file=SOUNDS_DB):
        self.db_file = db_file
        self.init_database()

    def init_database(self):
        """Инициализирует базу данных звуков"""
        conn = sqlite3.connect(self.db_file)
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
        conn = sqlite3.connect(self.db_file)
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

        conn = sqlite3.connect(self.db_file)
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
        conn = sqlite3.connect(self.db_file)
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


# Система базы данных игровой статистики
class GameStatsDatabase:
    def __init__(self, db_file=GAME_STATS_DB):
        self.db_file = db_file
        self.init_database()

    def init_database(self):
        """Инициализирует базу данных игровой статистики"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Создаем таблицу для прогресса игроков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL UNIQUE,
                unlocked_levels INTEGER DEFAULT 1,
                total_coins INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        # Вставляем начального игрока, если его нет
        cursor.execute('''
            INSERT OR IGNORE INTO player_progress (player_id, unlocked_levels, total_coins)
            VALUES (?, 1, 0)
        ''', ("player_1",))

        conn.commit()
        conn.close()

    def is_level_completed(self, player_id, level_number):
        """Проверяет, пройден ли уровень"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) FROM level_results 
            WHERE player_id = ? AND level_number = ? AND completed = 1
        ''', (player_id, level_number))

        result = cursor.fetchone()
        conn.close()

        return result[0] > 0 if result else False

    def get_completed_levels_count(self, player_id="player_1"):
        """Получает количество пройденных уровней"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(DISTINCT level_number) 
            FROM level_results 
            WHERE player_id = ? AND completed = 1
        ''', (player_id,))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else 0

    def update_level_result(self, player_id, level_number, score, play_time_seconds, completed=True):
        """Обновляет результат прохождения уровня"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Обновляем или вставляем результат уровня
        cursor.execute('''
            INSERT OR REPLACE INTO level_results 
            (player_id, level_number, score, completed, play_time_seconds, completed_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (player_id, level_number, score, 1 if completed else 0, play_time_seconds))

        conn.commit()
        conn.close()

    def get_level_score(self, player_id, level_number):
        """Получает лучший счет для уровня"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT MAX(score) FROM level_results 
            WHERE player_id = ? AND level_number = ?
        ''', (player_id, level_number))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result and result[0] else 0

    def reset_progress(self, player_id="player_1"):
        """Сбрасывает весь прогресс игрока"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Удаляем все результаты уровней
        cursor.execute('''
            DELETE FROM level_results WHERE player_id = ?
        ''', (player_id,))

        # Сбрасываем прогресс игрока
        cursor.execute('''
            UPDATE player_progress 
            SET unlocked_levels = 1, total_coins = 0, last_updated = CURRENT_TIMESTAMP
            WHERE player_id = ?
        ''', (player_id,))

        conn.commit()
        conn.close()


# Система сохранения прогресса
class GameProgress:
    def __init__(self):
        self.sound_db = SoundDatabase()
        self.stats_db = GameStatsDatabase()
        self.player_id = "player_1"

    def is_level_completed(self, level_number):
        """Проверяет, пройден ли уровень"""
        return self.stats_db.is_level_completed(self.player_id, level_number)

    def get_completed_levels(self):
        """Возвращает количество пройденных уровней"""
        return self.stats_db.get_completed_levels_count(self.player_id)

    def update_level_score(self, level_number, score, play_time_seconds):
        """Обновляет лучший счет для уровня"""
        self.stats_db.update_level_result(
            self.player_id,
            level_number,
            score,
            play_time_seconds,
            completed=True
        )

    def get_level_score(self, level_number):
        """Получает лучший счет для уровня"""
        return self.stats_db.get_level_score(self.player_id, level_number)

    def get_settings(self):
        """Получает настройки звуков из БД"""
        return self.sound_db.get_all_settings()

    def update_settings(self, sound_type, volume):
        """Обновляет настройки звуков в БД"""
        self.sound_db.set_volume(sound_type, volume)

    def reset_progress(self):
        """Сбрасывает весь прогресс"""
        self.stats_db.reset_progress(self.player_id)


# Главное меню
class MainMenuView(arcade.View):
    def __init__(self, progress_manager, music_player=None, music_stream=None, click_sound=None):
        super().__init__()
        self.progress = progress_manager
        self.background_list = arcade.SpriteList()
        self.ui_manager = gui.UIManager()
        self.music_player = music_player
        self.music_stream = music_stream
        self.click_sound = click_sound
        self.settings = self.progress.get_settings()

    def on_show_view(self):
        self.ui_manager.enable()

        # Фон
        self.background_list = arcade.SpriteList()
        if os.path.exists(MENU_BG):
            try:
                bg = arcade.load_texture(MENU_BG)
                bg_sprite = arcade.Sprite()
                bg_sprite.texture = bg
                bg_sprite.center_x = SCREEN_WIDTH / 2
                bg_sprite.center_y = SCREEN_HEIGHT / 2
                bg_sprite.width = SCREEN_WIDTH
                bg_sprite.height = SCREEN_HEIGHT
                self.background_list.append(bg_sprite)
            except:
                pass

        # Запуск музыки если нужно
        music_volume = self.settings.get('music', {}).get('volume', 0.5)
        if self.music_player and not self.music_stream and music_volume > 0:
            self.music_stream = self.music_player.play(
                volume=music_volume,
                loop=True
            )

        # UI элементы
        anchor = gui.UIAnchorLayout()
        v_box = gui.UIBoxLayout(space_between=15)

        # Заголовок
        title_label = gui.UILabel(
            text="Joe's Adventures",
            font_size=40,
            text_color=arcade.color.AUBURN,
            font_name="Arial"
        )
        v_box.add(title_label)

        # Отступ
        v_box.add(gui.UIBoxLayout(height=30))

        # Кнопки
        play_button = gui.UIFlatButton(
            text="PLAY",
            width=300,
            height=50
        )
        settings_button = gui.UIFlatButton(
            text="SETTINGS",
            width=300,
            height=50
        )
        exit_button = gui.UIFlatButton(
            text="EXIT",
            width=300,
            height=50
        )

        v_box.add(play_button)
        v_box.add(settings_button)
        v_box.add(exit_button)

        # Отступ
        v_box.add(gui.UIBoxLayout(height=20))

        # Информация о прогрессе
        completed_levels = self.progress.get_completed_levels()
        progress_text = f"Progress: {completed_levels}/3 levels"
        progress_label = gui.UILabel(
            text=progress_text,
            font_size=20,
            text_color=arcade.color.LIGHT_GRAY
        )
        v_box.add(progress_label)

        # Обработчики кнопок
        @play_button.event("on_click")
        def on_play_click(event):
            self._play_click_sound()
            level_select_view = LevelSelectView(
                self.progress,
                self.music_player,
                self.music_stream,
                self.click_sound
            )
            self.window.show_view(level_select_view)

        @settings_button.event("on_click")
        def on_settings_click(event):
            self._play_click_sound()
            settings_view = SettingsView(
                self.progress,
                self,
                self.music_player,
                self.music_stream,
                self.click_sound
            )
            self.window.show_view(settings_view)

        @exit_button.event("on_click")
        def on_exit_click(event):
            self._play_click_sound()
            arcade.exit()

        anchor.add(child=v_box, anchor_x="center_x", anchor_y="center_y")
        self.ui_manager.add(anchor)

    def on_hide_view(self):
        self.ui_manager.disable()

    def on_draw(self):
        self.clear()
        self.background_list.draw()
        self.ui_manager.draw()

    def _play_click_sound(self):
        """Проигрывает звук клика"""
        if self.click_sound:
            sound_volume = self.settings.get('ui_click', {}).get('volume', 0.8)
            if sound_volume > 0:
                try:
                    self.click_sound.play(volume=sound_volume)
                except:
                    pass


# Выбор уровня
class LevelSelectView(arcade.View):
    def __init__(self, progress_manager, music_player=None, music_stream=None, click_sound=None):
        super().__init__()
        self.progress = progress_manager
        self.background_list = arcade.SpriteList()
        self.ui_manager = gui.UIManager()
        self.music_player = music_player
        self.music_stream = music_stream
        self.click_sound = click_sound
        self.settings = self.progress.get_settings()

    def on_show_view(self):
        self.ui_manager.enable()

        # Фон
        self.background_list = arcade.SpriteList()
        if os.path.exists(MENU_BG):
            try:
                bg = arcade.load_texture(MENU_BG)
                bg_sprite = arcade.Sprite()
                bg_sprite.texture = bg
                bg_sprite.center_x = SCREEN_WIDTH / 2
                bg_sprite.center_y = SCREEN_HEIGHT / 2
                bg_sprite.width = SCREEN_WIDTH
                bg_sprite.height = SCREEN_HEIGHT
                self.background_list.append(bg_sprite)
            except:
                pass

        # UI
        anchor = gui.UIAnchorLayout()
        v_box = gui.UIBoxLayout(space_between=10)

        # Заголовок
        title = gui.UILabel(
            text="SELECT LEVEL",
            font_size=36,
            text_color=arcade.color.WHITE
        )
        v_box.add(title)
        v_box.add(gui.UIBoxLayout(height=30))

        # Стандартные стили для кнопок
        normal_style = {
            "normal": {
                "bg_color": (50, 100, 200),
                "font_color": arcade.color.WHITE
            },
            "hover": {
                "bg_color": (80, 130, 230),
                "font_color": arcade.color.WHITE
            },
            "press": {
                "bg_color": (100, 160, 255),
                "font_color": arcade.color.WHITE
            }
        }

        completed_style = {
            "normal": {
                "bg_color": (0, 100, 0),
                "font_color": arcade.color.WHITE
            },
            "hover": {
                "bg_color": (0, 150, 0),
                "font_color": arcade.color.WHITE
            },
            "press": {
                "bg_color": (0, 200, 0),
                "font_color": arcade.color.WHITE
            }
        }

        # Кнопка уровня 1
        level1_text = "LEVEL 1"
        if self.progress.is_level_completed(1):
            level1_text += " ✓"
            level1_style = completed_style
        else:
            level1_style = normal_style

        level1_button = gui.UIFlatButton(
            text=level1_text,
            width=250,
            height=60,
            style=level1_style
        )

        @level1_button.event("on_click")
        def on_level1_click(event):
            self._play_click_sound()
            self.launch_level(1)

        v_box.add(level1_button)

        # Кнопка уровня 2 (всегда доступна)
        level2_text = "LEVEL 2"
        if self.progress.is_level_completed(2):
            level2_text += " ✓"
            level2_style = completed_style
        else:
            level2_style = normal_style

        level2_button = gui.UIFlatButton(
            text=level2_text,
            width=250,
            height=60,
            style=level2_style
        )

        @level2_button.event("on_click")
        def on_level2_click(event):
            self._play_click_sound()
            self.launch_level(2)

        v_box.add(level2_button)

        # Кнопка уровня 3 (всегда доступна)
        level3_text = "LEVEL 3"
        if self.progress.is_level_completed(3):
            level3_text += " ✓"
            level3_style = completed_style
        else:
            level3_style = normal_style

        level3_button = gui.UIFlatButton(
            text=level3_text,
            width=250,
            height=60,
            style=level3_style
        )

        @level3_button.event("on_click")
        def on_level3_click(event):
            self._play_click_sound()
            self.launch_level(3)

        v_box.add(level3_button)

        # Отступ
        v_box.add(gui.UIBoxLayout(height=30))

        # Кнопка назад
        back_button_style = {
            "normal": {
                "bg_color": (100, 100, 100),
                "font_color": arcade.color.WHITE
            },
            "hover": {
                "bg_color": (130, 130, 130),
                "font_color": arcade.color.WHITE
            },
            "press": {
                "bg_color": (160, 160, 160),
                "font_color": arcade.color.WHITE
            }
        }

        back_button = gui.UIFlatButton(
            text="BACK TO MENU",
            width=250,
            height=50,
            style=back_button_style
        )
        v_box.add(back_button)

        @back_button.event("on_click")
        def on_back_click(event):
            self._play_click_sound()
            menu_view = MainMenuView(
                self.progress,
                self.music_player,
                self.music_stream,
                self.click_sound
            )
            self.window.show_view(menu_view)

        anchor.add(child=v_box, anchor_x="center_x", anchor_y="center_y")
        self.ui_manager.add(anchor)

    def launch_level(self, level_number):
        """Запускает указанный уровень"""
        print(f"Запуск уровня {level_number}...")

        # Получаем текущую громкость из БД
        music_volume = self.progress.sound_db.get_volume('music')

        # Скрываем окно меню и выключаем звук
        self.window.set_visible(False)
        if self.music_stream:
            try:
                self.music_stream.volume = 0
            except:
                print("Не удалось выключить звук")

        # Пауза
        import time
        time.sleep(0.1)

        # Запускаем уровень
        try:
            import subprocess
            level_files = {
                1: "levels/level_1.py",
                2: "levels/level_2.py",
                3: "levels/level_3.py"
            }

            if level_number in level_files:
                level_file = level_files[level_number]
                if os.path.exists(level_file):
                    process = subprocess.Popen(["python", level_file])
                    process.wait()
                    print(f"Уровень {level_number} завершен с кодом: {process.returncode}")
                else:
                    print(f"Файл уровня {level_number} не найден: {level_file}")
                    self.window.set_visible(True)
            else:
                print(f"Уровень {level_number} не найден")
                self.window.set_visible(True)

        except Exception as e:
            print(f"Ошибка при запуске уровня {level_number}: {e}")

        # Возвращаем видимость
        self.window.set_visible(True)

        # Включаем звук с сохраненной громкостью из БД
        if self.music_stream:
            try:
                # Получаем актуальную громкость из БД
                current_music_volume = self.progress.sound_db.get_volume('music')
                self.music_stream.volume = current_music_volume
                print(f"Включен звук с громкостью: {current_music_volume * 100}%")
            except Exception as e:
                print(f"Не удалось включить звук: {e}")
        else:
            # Если музыки нет, пробуем запустить
            if self.music_player:
                current_music_volume = self.progress.sound_db.get_volume('music')
                if current_music_volume > 0:
                    self.music_stream = self.music_player.play(
                        volume=current_music_volume,
                        loop=True
                    )

    def on_hide_view(self):
        self.ui_manager.disable()

    def on_draw(self):
        self.clear()
        self.background_list.draw()
        self.ui_manager.draw()

    def _play_click_sound(self):
        """Проигрывает звук клика"""
        if self.click_sound:
            click_volume = self.settings.get('ui_click', {}).get('volume', 0.8)
            if click_volume > 0:
                try:
                    self.click_sound.play(volume=click_volume)
                except:
                    pass


# Настройки
class SettingsView(arcade.View):
    def __init__(self, progress_manager, menu_view, music_player=None, music_stream=None, click_sound=None):
        super().__init__()
        self.progress = progress_manager
        self.menu_view = menu_view
        self.background_list = arcade.SpriteList()
        self.ui_manager = gui.UIManager()
        self.music_player = music_player
        self.music_stream = music_stream
        self.click_sound = click_sound
        self.settings = self.progress.get_settings()

    def on_show_view(self):
        self.ui_manager.enable()

        # Фон
        if os.path.exists(MENU_BG):
            try:
                bg = arcade.load_texture(MENU_BG)
                bg_sprite = arcade.Sprite()
                bg_sprite.texture = bg
                bg_sprite.center_x = SCREEN_WIDTH / 2
                bg_sprite.center_y = SCREEN_HEIGHT / 2
                bg_sprite.width = SCREEN_WIDTH
                bg_sprite.height = SCREEN_HEIGHT
                self.background_list.append(bg_sprite)
            except:
                pass

        # UI
        anchor = gui.UIAnchorLayout()
        v_box = gui.UIBoxLayout(space_between=15)

        title = gui.UILabel(
            text="SOUND SETTINGS",
            font_size=36,
            text_color=arcade.color.WHITE
        )
        v_box.add(title)
        v_box.add(gui.UIBoxLayout(height=20))

        # Громкость музыки
        music_volume = self.progress.sound_db.get_volume('music')
        music_label = gui.UILabel(
            text=f"Music Volume: {int(music_volume * 100)}%",
            font_size=24,
            text_color=arcade.color.WHITE
        )
        v_box.add(music_label)

        volume_hbox = gui.UIBoxLayout(vertical=False, space_between=10)

        button_style = {
            "normal": {
                "bg_color": (70, 70, 70),
                "font_color": arcade.color.WHITE
            },
            "hover": {
                "bg_color": (100, 100, 100),
                "font_color": arcade.color.WHITE
            },
            "press": {
                "bg_color": (130, 130, 130),
                "font_color": arcade.color.WHITE
            }
        }

        minus_btn = gui.UIFlatButton(text="-", width=50, height=40, style=button_style)
        plus_btn = gui.UIFlatButton(text="+", width=50, height=40, style=button_style)

        volume_hbox.add(minus_btn)
        volume_hbox.add(plus_btn)
        v_box.add(volume_hbox)

        def update_music_volume(change):
            self._play_click_sound()
            current_volume = self.progress.sound_db.get_volume('music')
            new_volume = max(0, min(1, current_volume + change))

            # Обновляем в БД
            self.progress.update_settings('music', new_volume)

            # Обновляем метку
            music_label.text = f"Music Volume: {int(new_volume * 100)}%"

            # Обновляем текущий поток музыки
            if self.music_stream:
                self.music_stream.volume = new_volume

        @minus_btn.event("on_click")
        def on_minus(event):
            update_music_volume(-0.1)

        @plus_btn.event("on_click")
        def on_plus(event):
            update_music_volume(0.1)

        v_box.add(gui.UIBoxLayout(height=20))

        # Громкость кликов UI
        ui_click_volume = self.progress.sound_db.get_volume('ui_click')
        ui_label = gui.UILabel(
            text=f"UI Click Sounds: {int(ui_click_volume * 100)}%",
            font_size=24,
            text_color=arcade.color.WHITE
        )
        v_box.add(ui_label)

        ui_hbox = gui.UIBoxLayout(vertical=False, space_between=10)
        ui_minus_btn = gui.UIFlatButton(text="-", width=50, height=40, style=button_style)
        ui_plus_btn = gui.UIFlatButton(text="+", width=50, height=40, style=button_style)

        ui_hbox.add(ui_minus_btn)
        ui_hbox.add(ui_plus_btn)
        v_box.add(ui_hbox)

        def update_ui_click_volume(change):
            self._play_click_sound()
            current_volume = self.progress.sound_db.get_volume('ui_click')
            new_volume = max(0, min(1, current_volume + change))

            # Обновляем в БД
            self.progress.update_settings('ui_click', new_volume)

            # Обновляем метку
            ui_label.text = f"UI Click Sounds: {int(new_volume * 100)}%"

        @ui_minus_btn.event("on_click")
        def on_ui_minus(event):
            update_ui_click_volume(-0.1)

        @ui_plus_btn.event("on_click")
        def on_ui_plus(event):
            update_ui_click_volume(0.1)

        v_box.add(gui.UIBoxLayout(height=20))

        # Кнопка сброса прогресса
        reset_btn_style = {
            "normal": {
                "bg_color": (150, 0, 0),
                "font_color": arcade.color.WHITE
            },
            "hover": {
                "bg_color": (200, 0, 0),
                "font_color": arcade.color.WHITE
            },
            "press": {
                "bg_color": (255, 0, 0),
                "font_color": arcade.color.WHITE
            }
        }

        reset_btn = gui.UIFlatButton(
            text="RESET PROGRESS",
            width=250,
            height=50,
            style=reset_btn_style
        )

        @reset_btn.event("on_click")
        def on_reset_click(event):
            self._play_click_sound()
            # Сбрасываем прогресс в БД
            self.progress.reset_progress()

            # Сбрасываем настройки звуков в БД
            self.progress.sound_db.init_database()

            # Обновляем громкость музыки
            if self.music_stream:
                default_music_volume = self.progress.sound_db.get_volume('music')
                self.music_stream.volume = default_music_volume

        v_box.add(reset_btn)

        v_box.add(gui.UIBoxLayout(height=20))

        # Кнопка назад
        back_btn_style = {
            "normal": {
                "bg_color": (50, 100, 200),
                "font_color": arcade.color.WHITE
            },
            "hover": {
                "bg_color": (80, 130, 230),
                "font_color": arcade.color.WHITE
            },
            "press": {
                "bg_color": (100, 160, 255),
                "font_color": arcade.color.WHITE
            }
        }

        back_btn = gui.UIFlatButton(
            text="BACK",
            width=250,
            height=50,
            style=back_btn_style
        )

        @back_btn.event("on_click")
        def on_back_click(event):
            self._play_click_sound()
            self.window.show_view(self.menu_view)

        v_box.add(back_btn)

        anchor.add(child=v_box, anchor_x="center_x", anchor_y="center_y")
        self.ui_manager.add(anchor)

    def on_hide_view(self):
        self.ui_manager.disable()

    def on_draw(self):
        self.clear()
        self.background_list.draw()
        self.ui_manager.draw()

    def _play_click_sound(self):
        """Проигрывает звук клика"""
        if self.click_sound:
            click_volume = self.progress.sound_db.get_volume('ui_click')
            if click_volume > 0:
                try:
                    self.click_sound.play(volume=click_volume)
                except:
                    pass


# Главное окно
class GameWindow(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        # Менеджер прогресса (теперь без JSON)
        self.progress_manager = GameProgress()

        # Загружаем музыку
        self.music_player = None
        self.music_stream = None
        if os.path.exists(MUSIC_FILE):
            try:
                self.music_player = arcade.load_sound(MUSIC_FILE)
            except:
                print(f"Не удалось загрузить музыку: {MUSIC_FILE}")

        # Загружаем звук клика
        self.click_sound = None
        if os.path.exists(CLICK_SOUND_FILE):
            try:
                self.click_sound = arcade.load_sound(CLICK_SOUND_FILE)
            except:
                print(f"Не удалось загрузить звук клика: {CLICK_SOUND_FILE}")
        else:
            print(f"Файл звука клика не найден: {CLICK_SOUND_FILE}")

        # Запускаем главное меню
        menu_view = MainMenuView(
            self.progress_manager,
            self.music_player,
            self.music_stream,
            self.click_sound
        )
        self.show_view(menu_view)


# Запуск игры
def main():
    window = GameWindow()
    arcade.run()


if __name__ == "__main__":
    main()
