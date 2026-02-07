import os
import sqlite3
import threading
import pygame
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk
from yt_dlp import YoutubeDL
from mutagen.mp3 import MP3
import requests
import time
import random
import glob
import json
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

# --- AYARLAR VE PATHLER ---
BASE_DIR = os.path.join(os.getcwd(), "WexPlayer_Pro_v12")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "Music")
THUMB_DIR = os.path.join(BASE_DIR, "Covers")
CACHE_DIR = os.path.join(BASE_DIR, "Cache")
DB_PATH = os.path.join(BASE_DIR, "wex_library_v12.db")
PLAYLIST_DIR = os.path.join(BASE_DIR, "Playlists")
SETTINGS_PATH = os.path.join(BASE_DIR, "settings.json")
ICON_PATH = os.path.join(BASE_DIR, "wexplayer_icon.ico")

for folder in [BASE_DIR, DOWNLOAD_DIR, THUMB_DIR, CACHE_DIR, PLAYLIST_DIR]:
    os.makedirs(folder, exist_ok=True)


# --- ICON OLUŞTUR ---
def create_icon():
    if os.path.exists(ICON_PATH):
        return
    try:
        size = 32
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([2, 2, 30, 30], fill='#1DB954')
        draw.ellipse([10, 18, 18, 26], fill='white')
        draw.rectangle([17, 8, 19, 19], fill='white')
        draw.polygon([(19, 8), (19, 12), (24, 10)], fill='white')
        img.save(ICON_PATH, format='ICO')
    except Exception as e:
        print(f"Icon oluşturma hatası: {e}")


create_icon()


# --- AYARLAR YÖNETİMİ ---
class Settings:
    def __init__(self):
        self.default_settings = {
            "theme": "green",
            "auto_dark_mode": False,
            "show_lyrics": True,
            "notifications": True,
            "crossfade": 0,
            "volume": 0.7,
            "equalizer": {
                "60Hz": 0, "170Hz": 0, "310Hz": 0, "600Hz": 0,
                "1kHz": 0, "3kHz": 0, "6kHz": 0, "12kHz": 0, "14kHz": 0, "16kHz": 0
            },
            "search_history": []
        }
        self.settings = self.load()

    def load(self):
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Yeni ayarları ekle, eskilerini koru
                    return {**self.default_settings, **loaded}
            except Exception as e:
                print(f"Ayar yükleme hatası: {e}")
                return self.default_settings.copy()
        return self.default_settings.copy()

    def save(self):
        try:
            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ayar kaydetme hatası: {e}")

    def get(self, key):
        return self.settings.get(key, self.default_settings.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save()


# --- BAŞLANGIÇ TEMİZLİĞİ ---
def clean_cache():
    try:
        cache_files = glob.glob(os.path.join(CACHE_DIR, "stream_*.*"))
        for f in cache_files:
            try:
                if os.path.isfile(f):
                    os.remove(f)
            except Exception as e:
                print(f"Cache temizleme hatası ({f}): {e}")
    except Exception as e:
        print(f"Cache temizleme genel hatası: {e}")


clean_cache()


# --- VERİTABANI ---
class WexDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()
        self._init_tables()

    def _init_tables(self):
        with self.lock:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, 
                artist TEXT, 
                path TEXT UNIQUE NOT NULL, 
                duration INTEGER DEFAULT 0, 
                thumb_path TEXT,
                is_favorite INTEGER DEFAULT 0,
                album_id INTEGER DEFAULT 0,
                is_online INTEGER DEFAULT 0,
                play_count INTEGER DEFAULT 0,
                last_played TIMESTAMP,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                lyrics TEXT,
                genre TEXT DEFAULT 'Unknown')''')

            self.cursor.execute('''CREATE TABLE IF NOT EXISTS albums (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL, 
                cover_path TEXT,
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            self.cursor.execute('''CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            self.cursor.execute('''CREATE TABLE IF NOT EXISTS playlist_songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER NOT NULL,
                song_id INTEGER NOT NULL,
                position INTEGER DEFAULT 0,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
                UNIQUE(playlist_id, song_id))''')

            self.cursor.execute('''CREATE TABLE IF NOT EXISTS listening_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                song_id INTEGER NOT NULL,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_listened INTEGER DEFAULT 0,
                FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE)''')

            self.conn.commit()

    def add_song(self, title, artist, path, duration, thumb_path, is_online=0, genre="Unknown"):
        with self.lock:
            try:
                self.cursor.execute(
                    "INSERT INTO songs (title, artist, path, duration, thumb_path, is_favorite, is_online, genre) VALUES (?,?,?,?,?,0,?,?)",
                    (title, artist, path, duration, thumb_path, is_online, genre))
                self.conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            except Exception as e:
                print(f"Şarkı ekleme hatası: {e}")
                return False

    def get_all(self):
        with self.lock:
            try:
                self.cursor.execute("SELECT * FROM songs ORDER BY date_added DESC")
                return self.cursor.fetchall()
            except Exception as e:
                print(f"Tüm şarkıları getirme hatası: {e}")
                return []

    def search_songs(self, query):
        with self.lock:
            try:
                query_param = f"%{query}%"
                self.cursor.execute(
                    "SELECT * FROM songs WHERE title LIKE ? OR artist LIKE ? OR genre LIKE ? ORDER BY play_count DESC",
                    (query_param, query_param, query_param))
                return self.cursor.fetchall()
            except Exception as e:
                print(f"Şarkı arama hatası: {e}")
                return []

    def get_favorites(self):
        with self.lock:
            try:
                self.cursor.execute("SELECT * FROM songs WHERE is_favorite=1 ORDER BY date_added DESC")
                return self.cursor.fetchall()
            except Exception as e:
                print(f"Favorileri getirme hatası: {e}")
                return []

    def get_albums(self):
        with self.lock:
            try:
                self.cursor.execute("SELECT * FROM albums ORDER BY date_created DESC")
                return self.cursor.fetchall()
            except Exception as e:
                print(f"Albümleri getirme hatası: {e}")
                return []

    def create_album(self, name, cover):
        with self.lock:
            try:
                self.cursor.execute("INSERT INTO albums (name, cover_path) VALUES (?,?)", (name, cover))
                self.conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            except Exception as e:
                print(f"Albüm oluşturma hatası: {e}")
                return False

    def add_to_album(self, song_id, album_id):
        with self.lock:
            try:
                self.cursor.execute("UPDATE songs SET album_id=? WHERE id=?", (album_id, song_id))
                self.conn.commit()
            except Exception as e:
                print(f"Albüme ekleme hatası: {e}")

    def get_album_songs(self, album_id):
        with self.lock:
            try:
                self.cursor.execute("SELECT * FROM songs WHERE album_id=? ORDER BY title", (album_id,))
                return self.cursor.fetchall()
            except Exception as e:
                print(f"Albüm şarkılarını getirme hatası: {e}")
                return []

    def toggle_fav(self, song_id, current_status):
        with self.lock:
            try:
                new_status = 0 if current_status == 1 else 1
                self.cursor.execute("UPDATE songs SET is_favorite=? WHERE id=?", (new_status, song_id))
                self.conn.commit()
                return new_status
            except Exception as e:
                print(f"Favori değiştirme hatası: {e}")
                return current_status

    def delete_song(self, song_id):
        with self.lock:
            try:
                self.cursor.execute("DELETE FROM songs WHERE id=?", (song_id,))
                self.conn.commit()
            except Exception as e:
                print(f"Şarkı silme hatası: {e}")

    def increment_play_count(self, song_id):
        with self.lock:
            try:
                self.cursor.execute(
                    "UPDATE songs SET play_count = play_count + 1, last_played = CURRENT_TIMESTAMP WHERE id=?",
                    (song_id,))
                self.cursor.execute(
                    "INSERT INTO listening_history (song_id, duration_listened) VALUES (?, 0)",
                    (song_id,))
                self.conn.commit()
            except Exception as e:
                print(f"Play count artırma hatası: {e}")

    def get_most_played(self, limit=20):
        with self.lock:
            try:
                self.cursor.execute(
                    "SELECT * FROM songs WHERE play_count > 0 ORDER BY play_count DESC LIMIT ?",
                    (limit,))
                return self.cursor.fetchall()
            except Exception as e:
                print(f"En çok dinlenenleri getirme hatası: {e}")
                return []

    def get_recently_added(self, limit=10):
        with self.lock:
            try:
                self.cursor.execute("SELECT * FROM songs ORDER BY date_added DESC LIMIT ?", (limit,))
                return self.cursor.fetchall()
            except Exception as e:
                print(f"Son eklenenleri getirme hatası: {e}")
                return []

    def get_recently_played(self, limit=10):
        with self.lock:
            try:
                self.cursor.execute(
                    "SELECT * FROM songs WHERE last_played IS NOT NULL ORDER BY last_played DESC LIMIT ?",
                    (limit,))
                return self.cursor.fetchall()
            except Exception as e:
                print(f"Son dinlenenleri getirme hatası: {e}")
                return []

    def get_listening_stats(self, days=7):
        with self.lock:
            try:
                self.cursor.execute('''
                    SELECT DATE(played_at) as day, COUNT(*) as count 
                    FROM listening_history 
                    WHERE played_at >= datetime('now', '-' || ? || ' days')
                    GROUP BY day ORDER BY day
                ''', (days,))
                return self.cursor.fetchall()
            except Exception as e:
                print(f"İstatistik getirme hatası: {e}")
                return []

    def get_genre_distribution(self):
        with self.lock:
            try:
                self.cursor.execute(
                    "SELECT genre, COUNT(*) as count FROM songs GROUP BY genre ORDER BY count DESC")
                return self.cursor.fetchall()
            except Exception as e:
                print(f"Tür dağılımı getirme hatası: {e}")
                return []

    def create_playlist(self, name, description=""):
        with self.lock:
            try:
                self.cursor.execute("INSERT INTO playlists (name, description) VALUES (?,?)", (name, description))
                self.conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            except Exception as e:
                print(f"Playlist oluşturma hatası: {e}")
                return False

    def get_playlists(self):
        with self.lock:
            try:
                self.cursor.execute("SELECT * FROM playlists ORDER BY date_created DESC")
                return self.cursor.fetchall()
            except Exception as e:
                print(f"Playlistleri getirme hatası: {e}")
                return []

    def add_to_playlist(self, playlist_id, song_id):
        with self.lock:
            try:
                self.cursor.execute("SELECT MAX(position) FROM playlist_songs WHERE playlist_id=?", (playlist_id,))
                result = self.cursor.fetchone()[0]
                position = (result or 0) + 1
                self.cursor.execute(
                    "INSERT INTO playlist_songs (playlist_id, song_id, position) VALUES (?,?,?)",
                    (playlist_id, song_id, position))
                self.conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            except Exception as e:
                print(f"Playlist'e ekleme hatası: {e}")
                return False

    def get_playlist_songs(self, playlist_id):
        with self.lock:
            try:
                self.cursor.execute('''SELECT s.* FROM songs s 
                                     JOIN playlist_songs ps ON s.id = ps.song_id 
                                     WHERE ps.playlist_id = ? 
                                     ORDER BY ps.position''', (playlist_id,))
                return self.cursor.fetchall()
            except Exception as e:
                print(f"Playlist şarkılarını getirme hatası: {e}")
                return []

    def delete_playlist(self, playlist_id):
        with self.lock:
            try:
                self.cursor.execute("DELETE FROM playlist_songs WHERE playlist_id=?", (playlist_id,))
                self.cursor.execute("DELETE FROM playlists WHERE id=?", (playlist_id,))
                self.conn.commit()
            except Exception as e:
                print(f"Playlist silme hatası: {e}")

    def update_lyrics(self, song_id, lyrics):
        with self.lock:
            try:
                self.cursor.execute("UPDATE songs SET lyrics=? WHERE id=?", (lyrics, song_id))
                self.conn.commit()
            except Exception as e:
                print(f"Şarkı sözü güncelleme hatası: {e}")

    def get_song_by_id(self, song_id):
        with self.lock:
            try:
                self.cursor.execute("SELECT * FROM songs WHERE id=?", (song_id,))
                return self.cursor.fetchone()
            except Exception as e:
                print(f"Şarkı getirme hatası: {e}")
                return None


# --- YARDIMCI FONKSİYONLAR ---
def format_time(seconds):
    if not seconds or seconds < 0:
        return "00:00"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02}:{secs:02}"


def get_yt_info(query_or_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'ignoreerrors': True,
        'no_warnings': True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            if "http" in query_or_url or "youtu" in query_or_url:
                try:
                    info = ydl.extract_info(query_or_url, download=False)
                    return [info] if info else []
                except Exception as e:
                    print(f"URL bilgi çekme hatası: {e}")
                    return []
            else:
                try:
                    res = ydl.extract_info(f"ytsearch15:{query_or_url}", download=False)
                    return res.get('entries', []) if res else []
                except Exception as e:
                    print(f"Arama hatası: {e}")
                    return []
    except Exception as e:
        print(f"YouTube bilgi çekme genel hatası: {e}")
        return []


def fetch_lyrics(artist, title):
    """Lyrics API ile şarkı sözü getir"""
    try:
        url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('lyrics', None)
        return None
    except Exception as e:
        print(f"Lyrics getirme hatası: {e}")
        return None


# --- TEMA RENK PALETLERİ ---
THEMES = {
    "green": {"primary": "#1DB954", "dark": "#191414", "darker": "#000000", "light": "#282828"},
    "blue": {"primary": "#1E90FF", "dark": "#0A0E27", "darker": "#000000", "light": "#1A1F3A"},
    "purple": {"primary": "#9D4EDD", "dark": "#10002B", "darker": "#000000", "light": "#240046"},
    "red": {"primary": "#DC143C", "dark": "#1A0000", "darker": "#000000", "light": "#330000"},
    "orange": {"primary": "#FF8C00", "dark": "#1A0F00", "darker": "#000000", "light": "#331E00"}
}


# --- ANA UYGULAMA ---
class WexPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Pencere ayarları
        self.title("WexPlayer Pro - Ultimate Edition")
        self.geometry("1400x900")

        # Icon ayarla
        try:
            self.iconbitmap(ICON_PATH)
        except Exception as e:
            print(f"Icon yükleme hatası: {e}")

        # Veritabanı ve ayarlar
        self.db = WexDB()
        self.settings = Settings()

        # Pygame mixer başlat
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception as e:
            print(f"Pygame mixer başlatma hatası: {e}")
            messagebox.showerror("Hata", "Ses sistemi başlatılamadı!")

        # Tema uygula
        self.current_theme = self.settings.get("theme")
        self.theme_colors = THEMES.get(self.current_theme, THEMES["green"])
        self.configure(fg_color=self.theme_colors["darker"])

        # Player Değişkenleri
        self.current_path = None
        self.current_song_id = None
        self.is_playing = False
        self.music_loaded = False
        self.song_duration = 0
        self.current_pos = 0

        self.is_shuffle = False
        self.is_repeat = False

        self.playlist = []
        self.current_index = -1

        self.is_dragging_slider = False

        # Stream lock
        self.stream_lock = threading.Lock()
        self.current_stream_id = None

        # Sleep timer
        self.sleep_timer_active = False
        self.sleep_timer_end = None

        # UI değişkenleri
        self.player_bar = None

        self._setup_layout()
        self._setup_keyboard_shortcuts()
        self.show_dashboard()
        self.after(1000, self.update_progress)

        # Başlangıç bildirimi
        if self.settings.get("notifications"):
            self.show_notification("WexPlayer Başladı", "Müziğin keyfini çıkar!")

    def show_notification(self, title, message):
        """Basit bildirim"""
        print(f"[NOTIFICATION] {title}: {message}")

    def _setup_keyboard_shortcuts(self):
        """Klavye kısayolları"""
        self.bind("<space>", lambda e: self.toggle_play())
        self.bind("<Right>", lambda e: self.skip_forward())
        self.bind("<Left>", lambda e: self.skip_backward())
        self.bind("<Up>", lambda e: self.volume_up())
        self.bind("<Down>", lambda e: self.volume_down())
        self.bind("<Control-f>", lambda e: self.show_search_page())
        self.bind("<Control-l>", lambda e: self.show_library_page())
        self.bind("<Control-n>", lambda e: self.next_song())
        self.bind("<Control-p>", lambda e: self.prev_song())

    def skip_forward(self):
        if self.music_loaded and self.song_duration > 0:
            new_pos = min(self.current_pos + 10, self.song_duration)
            try:
                pygame.mixer.music.play(start=new_pos)
                self.current_pos = new_pos
            except Exception as e:
                print(f"İleri atlama hatası: {e}")

    def skip_backward(self):
        if self.music_loaded and self.song_duration > 0:
            new_pos = max(self.current_pos - 10, 0)
            try:
                pygame.mixer.music.play(start=new_pos)
                self.current_pos = new_pos
            except Exception as e:
                print(f"Geri atlama hatası: {e}")

    def volume_up(self):
        try:
            current = pygame.mixer.music.get_volume()
            new_vol = min(current + 0.1, 1.0)
            pygame.mixer.music.set_volume(new_vol)
            self.settings.set("volume", new_vol)
        except Exception as e:
            print(f"Ses artırma hatası: {e}")

    def volume_down(self):
        try:
            current = pygame.mixer.music.get_volume()
            new_vol = max(current - 0.1, 0.0)
            pygame.mixer.music.set_volume(new_vol)
            self.settings.set("volume", new_vol)
        except Exception as e:
            print(f"Ses azaltma hatası: {e}")

    def _setup_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # SIDEBAR
        self.sidebar = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color=self.theme_colors["dark"])
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(pady=30)
        ctk.CTkLabel(logo_frame, text="🎵", font=("Arial", 40)).pack()
        ctk.CTkLabel(logo_frame, text="WEXPLAYER", font=("Impact", 28),
                     text_color=self.theme_colors["primary"]).pack()
        ctk.CTkLabel(logo_frame, text="Ultimate Edition", font=("Arial", 10),
                     text_color="#888").pack()

        # Navigation
        self._btn_nav("🏠  Ana Sayfa", self.show_dashboard)
        self._btn_nav("🔍  Müzik Ara", self.show_search_page)
        self._btn_nav("📚  Kitaplık", self.show_library_page)
        self._btn_nav("💿  Albümler", self.show_albums_page)
        self._btn_nav("❤️  Favoriler", self.show_favorites_page)
        self._btn_nav("📋  Playlistler", self.show_playlists_page)
        self._btn_nav("🔥  En Çok Dinlenen", self.show_most_played_page)
        self._btn_nav("📊  İstatistikler", self.show_stats_page)
        self._btn_nav("⚙️  Ayarlar", self.show_settings_page)

        # Alt bilgi
        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_frame.pack(side="bottom", pady=20)
        ctk.CTkLabel(bottom_frame, text="v12.0 Ultimate", font=("Arial", 9),
                     text_color="#444").pack()

        # MAIN AREA
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color=self.theme_colors["light"])
        self.main_area.grid(row=0, column=1, sticky="nsew")

        self.scroll = ctk.CTkScrollableFrame(self.main_area, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=0, pady=0)

    def _btn_nav(self, text, cmd):
        btn = ctk.CTkButton(self.sidebar, text=text, fg_color="transparent", text_color="#DDD",
                            hover_color=self.theme_colors["light"], anchor="w",
                            font=("Segoe UI", 14, "bold"), height=45, command=cmd)
        btn.pack(fill="x", padx=10, pady=2)

    def _clear(self):
        for w in self.scroll.winfo_children():
            w.destroy()

    # --- ANA SAYFA ---
    def show_dashboard(self):
        self._clear()

        # HERO BANNER
        hero = ctk.CTkFrame(self.scroll, height=280, fg_color=self.theme_colors["primary"], corner_radius=0)
        hero.pack(fill="x", pady=0)
        hero.pack_propagate(False)

        h_content = ctk.CTkFrame(hero, fg_color="transparent")
        h_content.pack(fill="both", expand=True, padx=50, pady=50)

        greeting = self._get_greeting()
        ctk.CTkLabel(h_content, text=greeting, font=("Segoe UI", 42, "bold"),
                     text_color="white", anchor="w").pack(anchor="w")
        ctk.CTkLabel(h_content, text="Favori şarkılarını ara, indir ve çevrimdışı dinle.",
                     font=("Segoe UI", 16), text_color="#F0F0F0", anchor="w").pack(anchor="w", pady=8)

        btn_frame = ctk.CTkFrame(h_content, fg_color="transparent")
        btn_frame.pack(anchor="w", pady=15)
        ctk.CTkButton(btn_frame, text="🔍 Şimdi Keşfet", font=("Segoe UI", 14, "bold"),
                      fg_color="black", text_color="white", width=150, height=45,
                      corner_radius=25, command=self.show_search_page).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📊 İstatistiklerim", font=("Segoe UI", 14, "bold"),
                      fg_color="transparent", border_width=2, border_color="white",
                      text_color="white", width=150, height=45, corner_radius=25,
                      command=self.show_stats_page).pack(side="left", padx=5)

        # İSTATİSTİK KARTLARI
        stats_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        stats_frame.pack(fill="x", padx=30, pady=30)

        songs_count = len(self.db.get_all())
        fav_count = len(self.db.get_favorites())
        alb_count = len(self.db.get_albums())
        pl_count = len(self.db.get_playlists())

        self._stat_card(stats_frame, "Toplam Şarkı", str(songs_count), "🎵", "#1a1a1a")
        self._stat_card(stats_frame, "Favorilerim", str(fav_count), "❤️", "#1a1a1a")
        self._stat_card(stats_frame, "Albümler", str(alb_count), "💿", "#1a1a1a")
        self._stat_card(stats_frame, "Playlistler", str(pl_count), "📋", "#1a1a1a")

        # SON DİNLENENLER
        recent_played = self.db.get_recently_played(5)
        if recent_played:
            ctk.CTkLabel(self.scroll, text="Son Dinlenenler", font=("Segoe UI", 24, "bold"),
                         text_color="white").pack(anchor="w", padx=30, pady=(20, 10))
            self._list_items(recent_played, is_search=False, compact=True)

        # SON EKLENENLER
        recent = self.db.get_recently_added(5)
        if recent:
            ctk.CTkLabel(self.scroll, text="Son Eklenenler", font=("Segoe UI", 24, "bold"),
                         text_color="white").pack(anchor="w", padx=30, pady=(20, 10))
            self._list_items(recent, is_search=False, compact=True)

    def _get_greeting(self):
        hour = datetime.now().hour
        if hour < 12:
            return "🌅 Günaydın!"
        elif hour < 18:
            return "☀️ İyi Günler!"
        else:
            return "🌙 İyi Akşamlar!"

    def _stat_card(self, parent, title, value, icon, color):
        card = ctk.CTkFrame(parent, width=220, height=110, fg_color=color, corner_radius=15)
        card.pack(side="left", padx=10, fill="y")
        card.pack_propagate(False)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(expand=True, fill="both", padx=20, pady=15)

        ctk.CTkLabel(content, text=icon, font=("Arial", 35)).pack(anchor="w")
        ctk.CTkLabel(content, text=value, font=("Segoe UI", 28, "bold"),
                     text_color="white").pack(anchor="w")
        ctk.CTkLabel(content, text=title, font=("Segoe UI", 12),
                     text_color="#AAA").pack(anchor="w")

    # --- ARAMA SAYFASI ---
    def show_search_page(self):
        self._clear()

        header = ctk.CTkFrame(self.scroll, fg_color="transparent")
        header.pack(fill="x", pady=25, padx=30)
        ctk.CTkLabel(header, text="Keşfet & Dinle 🎵", font=("Segoe UI", 32, "bold"),
                     text_color="white").pack(side="left")

        # Arama kutusu
        search_box = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=30, height=70)
        search_box.pack(fill="x", padx=30, pady=15)
        search_box.pack_propagate(False)

        self.entry = ctk.CTkEntry(search_box, placeholder_text="🔍 Şarkı, sanatçı veya albüm ara...",
                                  border_width=0, fg_color="transparent", text_color="white",
                                  font=("Segoe UI", 16), height=70)
        self.entry.pack(side="left", fill="both", expand=True, padx=25)
        self.entry.bind("<Return>", lambda e: self.do_search())

        ctk.CTkButton(search_box, text="🔍 ARA", width=120, height=50, corner_radius=25,
                      fg_color=self.theme_colors["primary"], text_color="black",
                      font=("Segoe UI", 14, "bold"),
                      command=self.do_search).pack(side="right", padx=15)

        # Kütüphane araması
        lib_search_box = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=30, height=70)
        lib_search_box.pack(fill="x", padx=30, pady=10)
        lib_search_box.pack_propagate(False)

        self.lib_entry = ctk.CTkEntry(lib_search_box, placeholder_text="📚 Kütüphanemde ara...",
                                      border_width=0, fg_color="transparent", text_color="white",
                                      font=("Segoe UI", 16), height=70)
        self.lib_entry.pack(side="left", fill="both", expand=True, padx=25)
        self.lib_entry.bind("<Return>", lambda e: self.search_library())

        ctk.CTkButton(lib_search_box, text="📚 KÜTÜPHANE", width=120, height=50, corner_radius=25,
                      fg_color="#333", text_color="white", font=("Segoe UI", 14, "bold"),
                      command=self.search_library).pack(side="right", padx=15)

        self.res_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.res_frame.pack(fill="both", expand=True, pady=20, padx=10)

    def search_library(self):
        query = self.lib_entry.get().strip()
        if not query:
            messagebox.showwarning("Uyarı", "Lütfen arama terimi girin!")
            return

        for w in self.res_frame.winfo_children():
            w.destroy()

        results = self.db.search_songs(query)

        if results:
            ctk.CTkLabel(self.res_frame, text=f"Kütüphanede {len(results)} sonuç bulundu:",
                         font=("Segoe UI", 16, "bold"), text_color="white").pack(anchor="w", pady=10, padx=5)
            self._list_items(results, is_search=False)
        else:
            ctk.CTkLabel(self.res_frame, text="Kütüphanede sonuç bulunamadı.",
                         text_color="#888", font=("Segoe UI", 14)).pack(pady=30)

    def do_search(self):
        q = self.entry.get().strip()
        if not q:
            messagebox.showwarning("Uyarı", "Lütfen arama terimi girin!")
            return

        for w in self.res_frame.winfo_children():
            w.destroy()

        loader = ctk.CTkLabel(self.res_frame, text="🔍 Youtube'da aranıyor...",
                              text_color=self.theme_colors["primary"], font=("Segoe UI", 16))
        loader.pack(pady=30)

        def task():
            results = get_yt_info(q)
            self.after(0, loader.destroy)
            if results:
                self.after(0, lambda: ctk.CTkLabel(self.res_frame,
                                                   text=f"🎵 {len(results)} sonuç bulundu:",
                                                   font=("Segoe UI", 16, "bold"), text_color="white").pack(anchor="w",
                                                                                                           pady=10,
                                                                                                           padx=5))
                self.after(0, lambda: self._list_items(results, is_search=True))
            else:
                self.after(0, lambda: ctk.CTkLabel(self.res_frame,
                                                   text="Sonuç bulunamadı veya bağlantı hatası.", text_color="#888",
                                                   font=("Segoe UI", 14)).pack(pady=30))

        threading.Thread(target=task, daemon=True).start()

    # --- DİĞER SAYFALAR ---
    def show_library_page(self):
        self._clear()
        header = ctk.CTkFrame(self.scroll, fg_color="transparent")
        header.pack(fill="x", pady=25, padx=30)
        ctk.CTkLabel(header, text="Kütüphanem 📚", font=("Segoe UI", 32, "bold"),
                     text_color="white").pack(side="left")

        all_songs = self.db.get_all()
        if all_songs:
            ctk.CTkLabel(self.scroll, text=f"Toplam {len(all_songs)} şarkı",
                         font=("Segoe UI", 14), text_color="#888").pack(anchor="w", padx=30, pady=5)
            self._list_items(all_songs, is_search=False)
        else:
            empty_frame = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=15)
            empty_frame.pack(fill="x", padx=30, pady=50)
            ctk.CTkLabel(empty_frame, text="Kütüphanende henüz şarkı yok.\n\nArama yap ve şarkı ekle!",
                         text_color="#888", font=("Segoe UI", 14), justify="center").pack(pady=40)

    def show_favorites_page(self):
        self._clear()
        ctk.CTkLabel(self.scroll, text="Favoriler ❤️", font=("Segoe UI", 32, "bold"),
                     text_color="white").pack(anchor="w", pady=25, padx=30)
        favs = self.db.get_favorites()
        if favs:
            self._list_items(favs, is_search=False)
        else:
            empty_frame = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=15)
            empty_frame.pack(fill="x", padx=30, pady=50)
            ctk.CTkLabel(empty_frame, text="Henüz favori şarkın yok.\n\n❤️ ile şarkıları favorilere ekleyebilirsin!",
                         text_color="#888", font=("Segoe UI", 14), justify="center").pack(pady=40)

    def show_most_played_page(self):
        self._clear()
        ctk.CTkLabel(self.scroll, text="En Çok Dinlenen 🔥", font=("Segoe UI", 32, "bold"),
                     text_color="white").pack(anchor="w", pady=25, padx=30)
        most_played = self.db.get_most_played(30)
        if most_played:
            self._list_items(most_played, is_search=False, show_play_count=True)
        else:
            empty_frame = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=15)
            empty_frame.pack(fill="x", padx=30, pady=50)
            ctk.CTkLabel(empty_frame, text="Henüz hiç şarkı dinlemediniz.\n\nŞarkıları dinledikçe burada görünecek!",
                         text_color="#888", font=("Segoe UI", 14), justify="center").pack(pady=40)

    # --- İSTATİSTİKLER SAYFASI ---
    def show_stats_page(self):
        self._clear()
        ctk.CTkLabel(self.scroll, text="İstatistiklerim 📊", font=("Segoe UI", 32, "bold"),
                     text_color="white").pack(anchor="w", pady=25, padx=30)

        # Dinleme grafikleri
        stats = self.db.get_listening_stats(30)
        if stats:
            chart_frame = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=15)
            chart_frame.pack(fill="x", padx=30, pady=20)

            ctk.CTkLabel(chart_frame, text="Son 30 Gün Dinleme Geçmişi",
                         font=("Segoe UI", 18, "bold"), text_color="white").pack(pady=15)

            # Basit bar chart
            max_count = max([s[1] for s in stats]) if stats else 1
            display_stats = stats[-7:] if len(stats) > 7 else stats

            for day, count in display_stats:
                bar_frame = ctk.CTkFrame(chart_frame, fg_color="transparent")
                bar_frame.pack(fill="x", padx=20, pady=5)

                try:
                    date_obj = datetime.strptime(day, '%Y-%m-%d')
                    day_name = date_obj.strftime('%d %b')
                except:
                    day_name = day[:10]

                ctk.CTkLabel(bar_frame, text=day_name, width=80,
                             font=("Segoe UI", 12), text_color="#AAA").pack(side="left")

                bar_width = max(int((count / max_count) * 500), 30)
                bar = ctk.CTkFrame(bar_frame, width=bar_width, height=30,
                                   fg_color=self.theme_colors["primary"], corner_radius=5)
                bar.pack(side="left", padx=10)
                bar.pack_propagate(False)

                ctk.CTkLabel(bar, text=str(count), font=("Segoe UI", 12, "bold"),
                             text_color="white").pack(expand=True)

        # Tür dağılımı
        genres = self.db.get_genre_distribution()
        if genres:
            genre_frame = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=15)
            genre_frame.pack(fill="x", padx=30, pady=20)

            ctk.CTkLabel(genre_frame, text="Müzik Tür Dağılımı",
                         font=("Segoe UI", 18, "bold"), text_color="white").pack(pady=15)

            total = sum([g[1] for g in genres])
            if total > 0:
                display_genres = genres[:5]
                for genre, count in display_genres:
                    g_frame = ctk.CTkFrame(genre_frame, fg_color="transparent")
                    g_frame.pack(fill="x", padx=20, pady=8)

                    percentage = int((count / total) * 100)
                    ctk.CTkLabel(g_frame, text=f"{genre}", width=120,
                                 font=("Segoe UI", 13, "bold"), text_color="white",
                                 anchor="w").pack(side="left")

                    prog_bar = ctk.CTkProgressBar(g_frame, width=300, height=20,
                                                  progress_color=self.theme_colors["primary"])
                    prog_bar.pack(side="left", padx=10)
                    prog_bar.set(percentage / 100)

                    ctk.CTkLabel(g_frame, text=f"{percentage}% ({count})",
                                 font=("Segoe UI", 12), text_color="#AAA").pack(side="left")

    # --- AYARLAR SAYFASI ---
    def show_settings_page(self):
        self._clear()
        ctk.CTkLabel(self.scroll, text="Ayarlar ⚙️", font=("Segoe UI", 32, "bold"),
                     text_color="white").pack(anchor="w", pady=25, padx=30)

        # Tema seçimi
        theme_frame = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=15)
        theme_frame.pack(fill="x", padx=30, pady=15)

        ctk.CTkLabel(theme_frame, text="🎨 Tema Rengi", font=("Segoe UI", 18, "bold"),
                     text_color="white").pack(anchor="w", padx=20, pady=15)

        theme_btn_frame = ctk.CTkFrame(theme_frame, fg_color="transparent")
        theme_btn_frame.pack(fill="x", padx=20, pady=15)

        for theme_name, colors in THEMES.items():
            ctk.CTkButton(theme_btn_frame, text=theme_name.capitalize(),
                          fg_color=colors["primary"], text_color="white",
                          width=100, height=40, corner_radius=10,
                          command=lambda t=theme_name: self.change_theme(t)).pack(side="left", padx=5)

        # Equalizer (Görsel)
        eq_frame = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=15)
        eq_frame.pack(fill="x", padx=30, pady=15)

        ctk.CTkLabel(eq_frame, text="🎚️ Equalizer (Görsel)", font=("Segoe UI", 18, "bold"),
                     text_color="white").pack(anchor="w", padx=20, pady=15)

        eq_controls = ctk.CTkFrame(eq_frame, fg_color="transparent")
        eq_controls.pack(fill="x", padx=20, pady=15)

        eq_bands = ["60Hz", "170Hz", "310Hz", "600Hz", "1kHz", "3kHz", "6kHz", "12kHz"]
        for band in eq_bands:
            band_frame = ctk.CTkFrame(eq_controls, fg_color="transparent")
            band_frame.pack(side="left", padx=10)

            ctk.CTkSlider(band_frame, from_=-10, to=10, orientation="vertical",
                          height=150, width=20, progress_color=self.theme_colors["primary"]).pack()
            ctk.CTkLabel(band_frame, text=band, font=("Segoe UI", 9),
                         text_color="#AAA").pack(pady=5)

        # Sleep Timer
        sleep_frame = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=15)
        sleep_frame.pack(fill="x", padx=30, pady=15)

        ctk.CTkLabel(sleep_frame, text="⏱️ Uyku Zamanlayıcı", font=("Segoe UI", 18, "bold"),
                     text_color="white").pack(anchor="w", padx=20, pady=15)

        sleep_btns = ctk.CTkFrame(sleep_frame, fg_color="transparent")
        sleep_btns.pack(fill="x", padx=20, pady=15)

        for minutes in [15, 30, 45, 60]:
            ctk.CTkButton(sleep_btns, text=f"{minutes} dk", width=80, height=35,
                          fg_color="#333", hover_color=self.theme_colors["primary"],
                          command=lambda m=minutes: self.set_sleep_timer(m)).pack(side="left", padx=5)

        ctk.CTkButton(sleep_btns, text="❌ İptal", width=80, height=35,
                      fg_color="#FF4444", command=self.cancel_sleep_timer).pack(side="left", padx=5)

        # Diğer ayarlar
        other_frame = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=15)
        other_frame.pack(fill="x", padx=30, pady=15)

        ctk.CTkLabel(other_frame, text="🔧 Diğer Ayarlar", font=("Segoe UI", 18, "bold"),
                     text_color="white").pack(anchor="w", padx=20, pady=15)

        options = [
            ("🔔 Bildirimler", "notifications"),
            ("🎤 Şarkı Sözlerini Göster", "show_lyrics"),
            ("🌙 Otomatik Karanlık Mod", "auto_dark_mode")
        ]

        for label, key in options:
            opt_frame = ctk.CTkFrame(other_frame, fg_color="transparent")
            opt_frame.pack(fill="x", padx=20, pady=10)

            ctk.CTkLabel(opt_frame, text=label, font=("Segoe UI", 14),
                         text_color="white", anchor="w").pack(side="left")

            switch = ctk.CTkSwitch(opt_frame, text="",
                                   fg_color="#333", progress_color=self.theme_colors["primary"],
                                   command=lambda k=key: self.toggle_setting(k))
            if self.settings.get(key):
                switch.select()
            switch.pack(side="right", padx=20)

    def change_theme(self, theme_name):
        self.settings.set("theme", theme_name)
        messagebox.showinfo("Tema Değiştirildi",
                            f"{theme_name.capitalize()} teması uygulandı!\nYeniden başlatın.")

    def set_sleep_timer(self, minutes):
        self.sleep_timer_active = True
        self.sleep_timer_end = datetime.now() + timedelta(minutes=minutes)
        messagebox.showinfo("Uyku Zamanlayıcı", f"{minutes} dakika sonra müzik duracak.")

    def cancel_sleep_timer(self):
        self.sleep_timer_active = False
        self.sleep_timer_end = None
        messagebox.showinfo("Uyku Zamanlayıcı", "Zamanlayıcı iptal edildi.")

    def toggle_setting(self, key):
        current = self.settings.get(key)
        self.settings.set(key, not current)

    # --- ALBÜMLER ---
    def show_albums_page(self):
        self._clear()
        header = ctk.CTkFrame(self.scroll, fg_color="transparent")
        header.pack(fill="x", pady=25, padx=30)
        ctk.CTkLabel(header, text="Albümlerim 💿", font=("Segoe UI", 32, "bold"),
                     text_color="white").pack(side="left")
        ctk.CTkButton(header, text="+ Yeni Albüm", fg_color=self.theme_colors["primary"],
                      text_color="black", font=("Segoe UI", 14, "bold"),
                      width=140, height=45, corner_radius=25,
                      command=self.create_album_dialog).pack(side="right")

        grid = ctk.CTkFrame(self.scroll, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=30, pady=20)

        albums = self.db.get_albums()
        if albums:
            for i, alb in enumerate(albums):
                f = ctk.CTkFrame(grid, width=180, height=220, fg_color="#1a1a1a", corner_radius=15)
                f.grid(row=i // 5, column=i % 5, padx=15, pady=15, sticky="n")
                f.pack_propagate(False)

                if alb[2] and os.path.exists(alb[2]):
                    try:
                        img = ctk.CTkImage(Image.open(alb[2]), size=(140, 140))
                        ctk.CTkLabel(f, image=img, text="").pack(pady=15)
                    except Exception as e:
                        print(f"Albüm kapağı yükleme hatası: {e}")
                        ctk.CTkLabel(f, text="💿", font=("Arial", 60)).pack(pady=30)
                else:
                    ctk.CTkLabel(f, text="💿", font=("Arial", 60)).pack(pady=30)

                album_name = str(alb[1])[:20]
                ctk.CTkLabel(f, text=album_name, font=("Segoe UI", 13, "bold"),
                             text_color="white").pack()
                ctk.CTkButton(f, text="Aç", height=30, width=120, corner_radius=15,
                              fg_color=self.theme_colors["primary"], text_color="black",
                              command=lambda n=alb[1], aid=alb[0]: self.show_album_songs(n, aid)).pack(pady=10)
        else:
            empty_frame = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=15)
            empty_frame.pack(fill="x", padx=30, pady=50)
            ctk.CTkLabel(empty_frame,
                         text="Henüz albüm oluşturmadınız.\n\n💿 Yeni albüm oluşturmak için yukarıdaki butona tıklayın!",
                         text_color="#888", font=("Segoe UI", 14), justify="center").pack(pady=40)

    def create_album_dialog(self):
        d = ctk.CTkToplevel(self)
        d.geometry("450x350")
        d.title("Yeni Albüm Oluştur")
        d.grab_set()

        try:
            d.iconbitmap(ICON_PATH)
        except:
            pass

        ctk.CTkLabel(d, text="📀 Yeni Albüm", font=("Segoe UI", 24, "bold")).pack(pady=20)

        ctk.CTkLabel(d, text="Albüm Adı:", font=("Segoe UI", 14)).pack(pady=10)
        ent = ctk.CTkEntry(d, width=350, height=40, font=("Segoe UI", 14))
        ent.pack(pady=5)

        path_v = tk.StringVar(value="")
        path_label = ctk.CTkLabel(d, text="Kapak seçilmedi", text_color="#888")
        path_label.pack(pady=10)

        def select_cover():
            file = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.bmp")])
            if file:
                path_v.set(file)
                path_label.configure(text=f"✓ {os.path.basename(file)}",
                                     text_color=self.theme_colors["primary"])

        ctk.CTkButton(d, text="🖼️ Kapak Seç", width=200, height=40,
                      fg_color="#333", command=select_cover).pack(pady=15)

        def save():
            album_name = ent.get().strip()
            cover_path = path_v.get()

            if not album_name:
                messagebox.showwarning("Uyarı", "Albüm adı boş olamaz!", parent=d)
                return

            if not cover_path:
                messagebox.showwarning("Uyarı", "Lütfen bir kapak resmi seçin!", parent=d)
                return

            if self.db.create_album(album_name, cover_path):
                messagebox.showinfo("Başarılı", f"'{album_name}' albümü oluşturuldu!", parent=d)
                d.destroy()
                self.show_albums_page()
            else:
                messagebox.showerror("Hata", "Bu isimde bir albüm zaten var!", parent=d)

        ctk.CTkButton(d, text="💾 Kaydet", command=save, width=200, height=45,
                      fg_color=self.theme_colors["primary"], text_color="black",
                      font=("Segoe UI", 14, "bold")).pack(pady=20)

    def show_album_songs(self, name, aid):
        self._clear()
        header = ctk.CTkFrame(self.scroll, fg_color="transparent")
        header.pack(fill="x", pady=25, padx=30)
        ctk.CTkLabel(header, text=f"💿 {name}", font=("Segoe UI", 32, "bold"),
                     text_color="white").pack(side="left")
        ctk.CTkButton(header, text="← Geri", fg_color="#333", width=100, height=40,
                      command=self.show_albums_page).pack(side="right")

        songs = self.db.get_album_songs(aid)
        if songs:
            self._list_items(songs, is_search=False)
        else:
            empty_frame = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=15)
            empty_frame.pack(fill="x", padx=30, pady=50)
            ctk.CTkLabel(empty_frame,
                         text="Bu albümde henüz şarkı yok.\n\n📚 Kütüphanenden sağ tık ile şarkı ekleyebilirsin!",
                         text_color="#888", font=("Segoe UI", 14), justify="center").pack(pady=40)

    # --- PLAYLISTLER ---
    def show_playlists_page(self):
        self._clear()
        header = ctk.CTkFrame(self.scroll, fg_color="transparent")
        header.pack(fill="x", pady=25, padx=30)
        ctk.CTkLabel(header, text="Playlistlerim 📋", font=("Segoe UI", 32, "bold"),
                     text_color="white").pack(side="left")
        ctk.CTkButton(header, text="+ Yeni Playlist", fg_color=self.theme_colors["primary"],
                      text_color="black", font=("Segoe UI", 14, "bold"),
                      width=140, height=45, corner_radius=25,
                      command=self.create_playlist_dialog).pack(side="right")

        playlists = self.db.get_playlists()
        if playlists:
            for pl in playlists:
                card = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", height=90, corner_radius=15)
                card.pack(fill="x", pady=8, padx=30)
                card.pack_propagate(False)

                icon_label = ctk.CTkLabel(card, text="📋", font=("Arial", 40))
                icon_label.pack(side="left", padx=20)

                info = ctk.CTkFrame(card, fg_color="transparent")
                info.pack(side="left", fill="both", expand=True, pady=20)

                ctk.CTkLabel(info, text=pl[1], font=("Segoe UI", 18, "bold"),
                             text_color="white", anchor="w").pack(anchor="w")
                desc = pl[2] if pl[2] else "Açıklama yok"
                ctk.CTkLabel(info, text=desc, font=("Segoe UI", 12),
                             text_color="#888", anchor="w").pack(anchor="w")

                btns = ctk.CTkFrame(card, fg_color="transparent")
                btns.pack(side="right", padx=15)

                ctk.CTkButton(btns, text="▶ Aç", width=80, height=40, corner_radius=20,
                              fg_color=self.theme_colors["primary"], text_color="black",
                              command=lambda pid=pl[0], pname=pl[1]: self.show_playlist_songs(pid, pname)).pack(
                    side="left", padx=5)
                ctk.CTkButton(btns, text="🗑️", width=45, height=40, corner_radius=20,
                              fg_color="#FF4444", text_color="white",
                              command=lambda pid=pl[0]: self.delete_playlist_action(pid)).pack(side="left")
        else:
            empty_frame = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=15)
            empty_frame.pack(fill="x", padx=30, pady=50)
            ctk.CTkLabel(empty_frame,
                         text="Henüz playlist oluşturmadınız.\n\n📋 Yeni playlist oluşturmak için yukarıdaki butona tıklayın!",
                         text_color="#888", font=("Segoe UI", 14), justify="center").pack(pady=40)

    def create_playlist_dialog(self):
        d = ctk.CTkToplevel(self)
        d.geometry("450x300")
        d.title("Yeni Playlist")
        d.grab_set()

        try:
            d.iconbitmap(ICON_PATH)
        except:
            pass

        ctk.CTkLabel(d, text="📋 Yeni Playlist", font=("Segoe UI", 24, "bold")).pack(pady=20)

        ctk.CTkLabel(d, text="Playlist Adı:", font=("Segoe UI", 14)).pack(pady=10)
        name_ent = ctk.CTkEntry(d, width=350, height=40, font=("Segoe UI", 14))
        name_ent.pack(pady=5)

        ctk.CTkLabel(d, text="Açıklama:", font=("Segoe UI", 14)).pack(pady=10)
        desc_ent = ctk.CTkEntry(d, width=350, height=40, font=("Segoe UI", 14))
        desc_ent.pack(pady=5)

        def save():
            pl_name = name_ent.get().strip()
            pl_desc = desc_ent.get().strip()

            if not pl_name:
                messagebox.showwarning("Uyarı", "Playlist adı boş olamaz!", parent=d)
                return

            if self.db.create_playlist(pl_name, pl_desc):
                messagebox.showinfo("Başarılı", f"'{pl_name}' playlist'i oluşturuldu!", parent=d)
                d.destroy()
                self.show_playlists_page()
            else:
                messagebox.showerror("Hata", "Bu isimde bir playlist zaten var!", parent=d)

        ctk.CTkButton(d, text="💾 Oluştur", command=save, width=200, height=45,
                      fg_color=self.theme_colors["primary"], text_color="black",
                      font=("Segoe UI", 14, "bold")).pack(pady=20)

    def show_playlist_songs(self, pid, pname):
        self._clear()
        header = ctk.CTkFrame(self.scroll, fg_color="transparent")
        header.pack(fill="x", pady=25, padx=30)
        ctk.CTkLabel(header, text=f"📋 {pname}", font=("Segoe UI", 32, "bold"),
                     text_color="white").pack(side="left")
        ctk.CTkButton(header, text="← Geri", fg_color="#333", width=100, height=40,
                      command=self.show_playlists_page).pack(side="right")

        songs = self.db.get_playlist_songs(pid)
        if songs:
            self._list_items(songs, is_search=False)
        else:
            empty_frame = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=15)
            empty_frame.pack(fill="x", padx=30, pady=50)
            ctk.CTkLabel(empty_frame,
                         text="Bu playlist'te henüz şarkı yok.\n\n📚 Kütüphanenden sağ tık ile şarkı ekleyebilirsin!",
                         text_color="#888", font=("Segoe UI", 14), justify="center").pack(pady=40)

    def delete_playlist_action(self, pid):
        if messagebox.askyesno("Emin misiniz?", "Bu playlist'i silmek istediğinizden emin misiniz?"):
            self.db.delete_playlist(pid)
            messagebox.showinfo("Silindi", "Playlist silindi.")
            self.show_playlists_page()

    # --- LİSTELEME ---
    def _list_items(self, items, is_search, compact=False, show_play_count=False):
        target = self.res_frame if is_search else self.scroll
        if not items:
            ctk.CTkLabel(target, text="Liste boş.", text_color="#555",
                         font=("Segoe UI", 14)).pack(pady=30)
            return

        for idx, item in enumerate(items):
            if is_search:
                title = item.get('title', 'Unknown')
                artist = item.get('uploader', 'Unknown')
                path = item.get('url', '')
                thumb = item.get('thumbnail', '')
                duration = item.get('duration', 0)
                is_fav = 0
                s_id = None
                is_online = 1
                play_count = 0
            else:
                if len(item) < 10:
                    continue
                s_id = item[0]
                title = item[1]
                artist = item[2]
                path = item[3]
                duration = item[4]
                thumb = item[5]
                is_fav = item[6]
                is_online = item[8]
                play_count = item[9]

            card = ctk.CTkFrame(target, fg_color="#1a1a1a",
                                height=65 if compact else 80, corner_radius=12)
            card.pack(fill="x", pady=4 if compact else 6, padx=5)
            card.pack_propagate(False)

            if not is_search:
                card.bind("<Button-3>", lambda e, sid=s_id, p=path: self._show_context_menu(e, sid, p))
                card.bind("<Double-Button-1>",
                          lambda e, sid=s_id, p=path, t=title, th=thumb, on=is_online, pl=items, ix=idx:
                          self.play_manager(sid, p, t, th, on, pl, ix))

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", padx=20, fill="y", pady=12)

            title_text = str(title)[:60]
            if show_play_count:
                title_text = f"🔥 {play_count}x  |  {title_text}"

            ctk.CTkLabel(info, text=title_text, font=("Segoe UI", 14 if compact else 15, "bold"),
                         text_color="white", anchor="w").pack(anchor="w")
            ctk.CTkLabel(info, text=str(artist)[:40], font=("Segoe UI", 11 if compact else 12),
                         text_color="#999", anchor="w").pack(anchor="w")

            btns = ctk.CTkFrame(card, fg_color="transparent")
            btns.pack(side="right", padx=15)

            if is_search:
                ctk.CTkButton(btns, text="❤️", width=45, height=35, corner_radius=18,
                              fg_color="#333", hover_color="#FF4444",
                              command=lambda t=title, a=artist, p=path, d=duration, th=thumb:
                              self.quick_add_fav(t, a, p, d, th)).pack(side="right", padx=4)

                ctk.CTkButton(btns, text="💾 İndir", width=80, height=35, corner_radius=18,
                              fg_color="#444", hover_color=self.theme_colors["primary"],
                              command=lambda u=path, t=title, a=artist, th=thumb:
                              self.download_song(u, t, a, th)).pack(side="right", padx=4)

                ctk.CTkButton(btns, text="▶ Dinle", width=80, height=35, corner_radius=18,
                              fg_color=self.theme_colors["primary"], text_color="black",
                              font=("Segoe UI", 12, "bold"),
                              command=lambda u=path, t=title, th=thumb, pl=items, ix=idx:
                              self.play_online_stream(u, t, th, pl, ix)).pack(side="right", padx=4)
            else:
                fav_col = "#FF4444" if is_fav else "#555"
                ctk.CTkButton(btns, text="❤", width=45, height=35, corner_radius=18,
                              fg_color="transparent", text_color=fav_col, font=("Arial", 18),
                              hover_color="#333",
                              command=lambda sid=s_id, f=is_fav: self.toggle_fav_action(sid, f)).pack(side="right",
                                                                                                      padx=4)

                if self.settings.get("show_lyrics"):
                    ctk.CTkButton(btns, text="🎤", width=45, height=35, corner_radius=18,
                                  fg_color="#444", hover_color="#666",
                                  command=lambda sid=s_id, t=title, a=artist:
                                  self.show_lyrics(sid, t, a)).pack(side="right", padx=4)

                play_text = "🌐" if is_online else "▶"
                play_col = self.theme_colors["primary"] if not is_online else "#4488FF"

                ctk.CTkButton(btns, text=play_text, width=50, height=40, corner_radius=20,
                              fg_color=play_col, text_color="black", font=("Arial", 18),
                              command=lambda sid=s_id, p=path, t=title, th=thumb, on=is_online, pl=items, ix=idx:
                              self.play_manager(sid, p, t, th, on, pl, ix)).pack(side="right", padx=4)

    def show_lyrics(self, song_id, title, artist):
        """Şarkı sözlerini göster"""
        d = ctk.CTkToplevel(self)
        d.geometry("600x700")
        d.title(f"🎤 {title}")
        d.grab_set()

        try:
            d.iconbitmap(ICON_PATH)
        except:
            pass

        header = ctk.CTkFrame(d, fg_color=self.theme_colors["primary"], height=80)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text=title[:40], font=("Segoe UI", 20, "bold"),
                     text_color="white").pack(pady=10)
        ctk.CTkLabel(header, text=artist, font=("Segoe UI", 14),
                     text_color="#EEE").pack()

        lyrics_frame = ctk.CTkScrollableFrame(d, fg_color="#1a1a1a")
        lyrics_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Sözleri yükle
        loading = ctk.CTkLabel(lyrics_frame, text="Şarkı sözleri yükleniyor...",
                               text_color="#888", font=("Segoe UI", 14))
        loading.pack(pady=50)

        def load_lyrics():
            lyrics = fetch_lyrics(artist, title)
            d.after(0, loading.destroy)

            if lyrics:
                lyrics_text = ctk.CTkTextbox(lyrics_frame, font=("Segoe UI", 13),
                                             text_color="white", fg_color="#0a0a0a",
                                             wrap="word", height=500)
                lyrics_text.pack(fill="both", expand=True, pady=10)
                lyrics_text.insert("1.0", lyrics)
                lyrics_text.configure(state="disabled")

                if song_id:
                    self.db.update_lyrics(song_id, lyrics)
            else:
                d.after(0, lambda: ctk.CTkLabel(lyrics_frame,
                                                text="😔 Şarkı sözleri bulunamadı.\n\nFarklı bir kaynak deneyebilirsiniz.",
                                                text_color="#888", font=("Segoe UI", 14),
                                                justify="center").pack(pady=50))

        threading.Thread(target=load_lyrics, daemon=True).start()

    def _show_context_menu(self, event, song_id, path):
        m = tk.Menu(self, tearoff=0, bg="#1a1a1a", fg="white",
                    activebackground=self.theme_colors["primary"], activeforeground="black",
                    font=("Segoe UI", 11))

        m.add_command(label="🗑️ Sil", command=lambda: self.delete_song_action(song_id, path))
        m.add_separator()

        albums = self.db.get_albums()
        if albums:
            alb_m = tk.Menu(m, tearoff=0, bg="#1a1a1a", fg="white",
                            activebackground=self.theme_colors["primary"], activeforeground="black")
            for alb in albums:
                alb_m.add_command(label=alb[1],
                                  command=lambda sid=song_id, aid=alb[0], aname=alb[1]:
                                  self.add_song_to_album(sid, aid, aname))
            m.add_cascade(label="➕ Albüme Ekle", menu=alb_m)

        playlists = self.db.get_playlists()
        if playlists:
            pl_m = tk.Menu(m, tearoff=0, bg="#1a1a1a", fg="white",
                           activebackground=self.theme_colors["primary"], activeforeground="black")
            for pl in playlists:
                pl_m.add_command(label=pl[1],
                                 command=lambda sid=song_id, pid=pl[0], pname=pl[1]:
                                 self.add_song_to_playlist(sid, pid, pname))
            m.add_cascade(label="📋 Playlist'e Ekle", menu=pl_m)

        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def add_song_to_album(self, song_id, album_id, album_name):
        self.db.add_to_album(song_id, album_id)
        if self.settings.get("notifications"):
            self.show_notification("Albüme Eklendi", f"'{album_name}' albümüne eklendi!")
        messagebox.showinfo("Başarılı", f"Şarkı '{album_name}' albümüne eklendi!")

    def add_song_to_playlist(self, song_id, playlist_id, playlist_name):
        if self.db.add_to_playlist(playlist_id, song_id):
            if self.settings.get("notifications"):
                self.show_notification("Playlist'e Eklendi", f"'{playlist_name}' playlist'ine eklendi!")
            messagebox.showinfo("Başarılı", f"Şarkı '{playlist_name}' playlist'ine eklendi!")
        else:
            messagebox.showinfo("Bilgi", "Bu şarkı zaten playlist'te!")

    def delete_song_action(self, s_id, path):
        if messagebox.askyesno("Emin misiniz?", "Bu şarkıyı silmek istediğinizden emin misiniz?"):
            self.db.delete_song(s_id)
            if os.path.exists(path) and "http" not in path:
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Dosya silme hatası: {e}")
            messagebox.showinfo("Silindi", "Şarkı kütüphaneden silindi.")
            self.show_library_page()

    def quick_add_fav(self, t, a, url, d, th):
        if self.db.add_song(t, a, url, d, th, is_online=1):
            res = self.db.cursor.execute("SELECT id FROM songs WHERE path=?", (url,)).fetchone()
            if res:
                self.db.toggle_fav(res[0], 0)
            messagebox.showinfo("WexPlayer", "Şarkı favorilere eklendi!")
        else:
            messagebox.showinfo("WexPlayer", "Bu şarkı zaten kütüphanede!")

    def toggle_fav_action(self, s_id, current):
        new_status = self.db.toggle_fav(s_id, current)
        # Sayfayı yenile
        self.after(100, self.show_library_page)

    def download_song(self, url, title, artist, thumb_url):
        def run():
            try:
                safe = "".join(x for x in title if x.isalnum() or x in " -_").strip()
                if not safe:
                    safe = "download"

                f_path = os.path.join(DOWNLOAD_DIR, f"{safe}.mp3")
                t_path = os.path.join(THUMB_DIR, f"{safe}.jpg")

                # Thumbnail indir
                if thumb_url:
                    try:
                        response = requests.get(thumb_url, timeout=5)
                        if response.status_code == 200:
                            with open(t_path, 'wb') as f:
                                f.write(response.content)
                    except Exception as e:
                        print(f"Thumbnail indirme hatası: {e}")
                        t_path = ""

                # Şarkıyı indir
                opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': f_path.replace('.mp3', ''),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192'
                    }],
                    'quiet': True,
                    'no_warnings': True
                }

                with YoutubeDL(opts) as ydl:
                    ydl.download([url])

                # Duration bul
                try:
                    dur = int(MP3(f_path).info.length)
                except:
                    dur = 0

                self.db.add_song(title, artist, f_path, dur, t_path, is_online=0)

                if self.settings.get("notifications"):
                    self.after(0, lambda: self.show_notification("İndirme Tamamlandı", f"{title} kütüphaneye eklendi!"))

                self.after(0, lambda: messagebox.showinfo("Başarılı", f"{title} indirildi ve kütüphaneye eklendi!"))
                self.after(0, self.show_library_page)

            except Exception as e:
                print(f"İndirme hatası: {e}")
                self.after(0, lambda: messagebox.showerror("Hata", f"İndirme hatası: {str(e)}"))

        threading.Thread(target=run, daemon=True).start()
        messagebox.showinfo("İndirme", f"{title} indiriliyor...")

    # --- OYNATMA ---
    def _unload_music(self):
        self.music_loaded = False
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            time.sleep(0.05)
        except Exception as e:
            print(f"Music unload hatası: {e}")

    def play_online_stream(self, url, title, thumb, pl=None, ix=-1, song_id=None):
        stream_id = f"{int(time.time())}_{random.randint(1000, 9999)}"

        with self.stream_lock:
            self.current_stream_id = stream_id

        self._create_pro_player()
        self.p_title.configure(text=f"⏳ {title[:30]}...")
        self.music_loaded = False

        if pl:
            self.playlist = pl
            self.current_index = ix

        def streamer():
            try:
                with self.stream_lock:
                    if self.current_stream_id != stream_id:
                        return

                self._unload_music()
                time.sleep(0.1)

                unique_name = f"stream_{stream_id}"
                temp_path = os.path.join(CACHE_DIR, f"{unique_name}.mp3")
                temp_thumb = os.path.join(CACHE_DIR, f"{unique_name}.jpg")

                # Thumbnail indir
                if thumb:
                    try:
                        response = requests.get(thumb, timeout=3)
                        if response.status_code == 200:
                            with open(temp_thumb, 'wb') as f:
                                f.write(response.content)
                    except Exception as e:
                        print(f"Stream thumb hatası: {e}")
                        temp_thumb = ""

                # Şarkıyı indir
                opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': temp_path.replace('.mp3', ''),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '128'
                    }],
                    'quiet': True,
                    'no_warnings': True
                }

                with YoutubeDL(opts) as ydl:
                    ydl.download([url])

                with self.stream_lock:
                    if self.current_stream_id != stream_id:
                        try:
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                            if temp_thumb and os.path.exists(temp_thumb):
                                os.remove(temp_thumb)
                        except:
                            pass
                        return

                self.after(0, lambda: self.play_manager(song_id, temp_path, title, temp_thumb,
                                                        is_online=0, force_local=True))
                self.after(3000, lambda: clean_cache())

            except Exception as e:
                print(f"Stream hatası: {e}")
                with self.stream_lock:
                    if self.current_stream_id == stream_id:
                        self.after(0, lambda: self.p_title.configure(text="❌ Hata"))

        threading.Thread(target=streamer, daemon=True).start()

    def play_manager(self, song_id, path, title, thumb, is_online=0, pl=None, ix=-1, force_local=False):
        if is_online == 1 and not force_local:
            self.play_online_stream(path, title, thumb, pl, ix, song_id)
            return

        if not os.path.exists(path):
            messagebox.showerror("Hata", "Dosya bulunamadı!")
            return

        self._create_pro_player()
        if pl is not None:
            self.playlist = pl
            self.current_index = ix

        try:
            self._unload_music()
            time.sleep(0.1)

            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            pygame.mixer.music.set_volume(self.settings.get("volume"))

            self.music_loaded = True
            self.current_path = path
            self.current_song_id = song_id
            self.is_playing = True
            self.current_pos = 0

            if song_id:
                self.db.increment_play_count(song_id)

            self.p_title.configure(text=title[:40])
            self.p_artist.configure(text="")
            self.play_btn.configure(text="⏸")

            try:
                self.song_duration = MP3(path).info.length
                self.lbl_total.configure(text=format_time(self.song_duration))
            except Exception as e:
                print(f"Duration okuma hatası: {e}")
                self.song_duration = 0

            if thumb and os.path.exists(thumb):
                try:
                    img = ctk.CTkImage(Image.open(thumb), size=(70, 70))
                    self.p_thumb.configure(image=img)
                    self.p_thumb.image = img
                except Exception as e:
                    print(f"Kapak resmi yükleme hatası: {e}")
                    self.p_thumb.configure(image=None, text="🎵", font=("Arial", 30))
            else:
                self.p_thumb.configure(image=None, text="🎵", font=("Arial", 30))

            if self.settings.get("notifications"):
                self.show_notification("Çalıyor", title[:50])

        except Exception as e:
            print(f"Player hatası: {e}")
            self.music_loaded = False
            messagebox.showerror("Hata", f"Oynatma hatası: {str(e)}")

    # --- PLAYER UI ---
    def _create_pro_player(self):
        if self.player_bar:
            return

        self.player_bar = ctk.CTkFrame(self, height=130, fg_color="#0a0a0a",
                                       border_width=2, border_color=self.theme_colors["primary"],
                                       corner_radius=0)
        self.player_bar.grid(row=1, column=1, sticky="ew")
        self.player_bar.grid_propagate(False)
        self.player_bar.columnconfigure(1, weight=1)

        # SOL - Şarkı Bilgisi
        left = ctk.CTkFrame(self.player_bar, fg_color="transparent", width=300)
        left.grid(row=0, column=0, padx=25, pady=15, sticky="w")
        left.grid_propagate(False)

        self.p_thumb = ctk.CTkLabel(left, text="", width=70, height=70, fg_color="#1a1a1a",
                                    corner_radius=10)
        self.p_thumb.pack(side="left")

        info = ctk.CTkFrame(left, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=15)

        self.p_title = ctk.CTkLabel(info, text="", font=("Segoe UI", 15, "bold"),
                                    text_color="white", anchor="w")
        self.p_title.pack(anchor="w")

        self.p_artist = ctk.CTkLabel(info, text="", font=("Segoe UI", 12),
                                     text_color="#AAA", anchor="w")
        self.p_artist.pack(anchor="w")

        # ORTA - Kontroller
        center = ctk.CTkFrame(self.player_bar, fg_color="transparent")
        center.grid(row=0, column=1, sticky="ew", padx=30)

        # Kontrol butonları
        ctrls = ctk.CTkFrame(center, fg_color="transparent")
        ctrls.pack(pady=8)

        self.btn_shuf = ctk.CTkButton(ctrls, text="🔀", width=35, height=35, corner_radius=18,
                                      fg_color="transparent", text_color="#666", font=("Arial", 16),
                                      hover_color="#333", command=self.toggle_shuffle)
        self.btn_shuf.pack(side="left", padx=8)

        ctk.CTkButton(ctrls, text="⏮", width=45, height=45, corner_radius=23,
                      fg_color="transparent", text_color="white", font=("Arial", 20),
                      hover_color="#333", command=self.prev_song).pack(side="left", padx=5)

        self.play_btn = ctk.CTkButton(ctrls, text="⏸", width=60, height=60, corner_radius=30,
                                     fg_color="white", text_color="black", font=("Arial", 26),
                                     hover_color="#DDD", command=self.toggle_play)
        self.play_btn.pack(side="left", padx=15)

        ctk.CTkButton(ctrls, text="⏭", width=45, height=45, corner_radius=23,
                     fg_color="transparent", text_color="white", font=("Arial", 20),
                     hover_color="#333", command=self.next_song).pack(side="left", padx=5)

        self.btn_rep = ctk.CTkButton(ctrls, text="🔁", width=35, height=35, corner_radius=18,
                                    fg_color="transparent", text_color="#666", font=("Arial", 16),
                                    hover_color="#333", command=self.toggle_repeat)
        self.btn_rep.pack(side="left", padx=8)

        # Progress bar
        time_f = ctk.CTkFrame(center, fg_color="transparent")
        time_f.pack(fill="x", pady=8)

        self.lbl_curr = ctk.CTkLabel(time_f, text="00:00", font=("Segoe UI", 11, "bold"),
                                    text_color="#BBB", width=50)
        self.lbl_curr.pack(side="left")

        self.slider = ctk.CTkSlider(time_f, from_=0, to=100, height=18,
                                   progress_color=self.theme_colors["primary"],
                                   button_color="white", button_hover_color="#DDD")
        self.slider.pack(side="left", fill="x", expand=True, padx=15)
        self.slider.bind("<Button-1>", self.slider_click)
        self.slider.bind("<ButtonRelease-1>", self.slider_release)
        self.slider.set(0)

        self.lbl_total = ctk.CTkLabel(time_f, text="00:00", font=("Segoe UI", 11, "bold"),
                                     text_color="#BBB", width=50)
        self.lbl_total.pack(side="right")

        # SAĞ - Ses Kontrolü
        right = ctk.CTkFrame(self.player_bar, fg_color="transparent")
        right.grid(row=0, column=2, padx=25, sticky="e")

        ctk.CTkLabel(right, text="🔊", font=("Arial", 18), text_color="white").pack(side="left", padx=5)

        vol_sl = ctk.CTkSlider(right, width=100, from_=0, to=1, height=18,
                              progress_color=self.theme_colors["primary"],
                              command=lambda v: self.set_volume(v))
        vol_sl.set(self.settings.get("volume"))
        vol_sl.pack(side="left", padx=10)

        ctk.CTkButton(right, text="❌", width=40, height=40, corner_radius=20,
                     fg_color="transparent", text_color="#FF4444", font=("Arial", 18),
                     hover_color="#333", command=self.close_player).pack(side="left", padx=10)

    def set_volume(self, value):
        try:
            pygame.mixer.music.set_volume(value)
            self.settings.set("volume", value)
        except Exception as e:
            print(f"Ses ayarlama hatası: {e}")

    def toggle_play(self):
        if not self.music_loaded:
            return
        try:
            if self.is_playing:
                pygame.mixer.music.pause()
                self.play_btn.configure(text="▶")
            else:
                pygame.mixer.music.unpause()
                self.play_btn.configure(text="⏸")
            self.is_playing = not self.is_playing
        except Exception as e:
            print(f"Toggle play hatası: {e}")

    def toggle_shuffle(self):
        self.is_shuffle = not self.is_shuffle
        self.btn_shuf.configure(text_color=self.theme_colors["primary"] if self.is_shuffle else "#666")

    def toggle_repeat(self):
        self.is_repeat = not self.is_repeat
        self.btn_rep.configure(text_color=self.theme_colors["primary"] if self.is_repeat else "#666")

    def next_song(self):
        if not self.playlist:
            return
        if self.is_shuffle:
            idx = random.randint(0, len(self.playlist) - 1)
        else:
            idx = (self.current_index + 1) % len(self.playlist)
        self.load_from_playlist(idx)

    def prev_song(self):
        if not self.playlist:
            return
        idx = (self.current_index - 1) % len(self.playlist)
        self.load_from_playlist(idx)

    def load_from_playlist(self, idx):
        self.current_index = idx
        item = self.playlist[idx]
        if isinstance(item, dict):
            title = item.get('title', 'Unknown')
            path = item.get('url', '')
            thumb = item.get('thumbnail', '')
            self.play_online_stream(path, title, thumb, self.playlist, idx)
        else:
            if len(item) < 9:
                return
            s_id = item[0]
            is_online = item[8]
            self.play_manager(s_id, item[3], item[1], item[5], is_online, self.playlist, idx)

    def slider_click(self, e):
        self.is_dragging_slider = True

    def slider_release(self, e):
        if not self.music_loaded or not self.current_path:
            self.is_dragging_slider = False
            self.slider.set(0)
            return

        try:
            val = self.slider.get()
            new_pos = (val / 100) * self.song_duration

            pygame.mixer.music.play(start=new_pos)
            self.current_pos = new_pos
            self.is_playing = True
            self.play_btn.configure(text="⏸")
        except Exception as err:
            print(f"Slider hatası: {err}")

        self.is_dragging_slider = False

    def update_progress(self):
        # Sleep timer kontrolü
        if self.sleep_timer_active and self.sleep_timer_end:
            if datetime.now() >= self.sleep_timer_end:
                self.close_player()
                self.sleep_timer_active = False
                if self.settings.get("notifications"):
                    self.show_notification("Uyku Zamanlayıcı", "Müzik durduruldu.")

        if self.is_playing and self.music_loaded and not self.is_dragging_slider:
            try:
                if pygame.mixer.music.get_busy():
                    played = pygame.mixer.music.get_pos() / 1000
                    if played < 0:
                        played = 0
                    total_curr = self.current_pos + played

                    if self.song_duration > 0:
                        progress = min((total_curr / self.song_duration) * 100, 100)
                        self.slider.set(progress)
                        self.lbl_curr.configure(text=format_time(total_curr))

                        if total_curr >= self.song_duration - 1:
                            if self.is_repeat:
                                pygame.mixer.music.play()
                                self.current_pos = 0
                            else:
                                self.next_song()
            except Exception as e:
                print(f"Progress update hatası: {e}")

        self.after(500, self.update_progress)

    def close_player(self):
        self._unload_music()
        if self.player_bar:
            self.player_bar.grid_forget()
            self.player_bar.destroy()
            self.player_bar = None
        self.is_playing = False
        self.playlist = []
        self.current_index = -1
        self.current_song_id = None


if __name__ == "__main__":
    try:
        app = WexPlayer()
        app.mainloop()
    except Exception as e:
        print(f"Uygulama başlatma hatası: {e}")
        messagebox.showerror("Kritik Hata", f"Uygulama başlatılamadı: {str(e)}")