import sys
import os
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QListWidget, QSlider, QLabel
from PyQt5.QtCore import Qt, QTimer, QSettings
from PyQt5.QtGui import QPixmap, QColor, QFont
from pygame import mixer
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC

class MusicPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Player")
        self.setGeometry(100, 100, 600, 400)
        self.init_ui()
        
        mixer.init()
        self.current_song_path = None
        self.is_playing = False
        self.is_paused = False
        self.is_looping = False  # Flag to indicate if looping is enabled

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(1000)  # Update every second

        self.cover_thread = None  # Thread for cover art loading
        self.cover_cache = {}  # Cache for cover art images

        # Initialize QSettings for saving/loading folder path
        self.settings = QSettings("MyCompany", "MusicPlayer")
        self.last_folder_path = self.settings.value("last_folder_path", "")

        if self.last_folder_path and os.path.exists(self.last_folder_path):
            self.load_songs(self.last_folder_path)

    def init_ui(self):
        self.main_layout = QHBoxLayout()
        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()
        
        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.clicked.connect(self.open_folder)
        
        self.song_list = QListWidget()
        self.song_list.itemDoubleClicked.connect(self.play_selected_song)

        self.play_button = QPushButton("Play")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        self.loop_button = QPushButton("Loop")  # Added loop button

        self.play_button.clicked.connect(self.play_song)
        self.pause_button.clicked.connect(self.pause_resume_song)
        self.stop_button.clicked.connect(self.stop_song)
        self.loop_button.clicked.connect(self.toggle_loop)

        self.volume_label = QLabel("Volume")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(70)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #3c3c3c;
                height: 8px;
                background: #3c3c3c;
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: red;
                border: 1px solid #3c3c3c;
                width: 10px;
                margin: -2px 0;
                border-radius: 5px;
            }
        """)
        self.volume_slider.valueChanged.connect(self.set_volume)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(100)
        self.progress_slider.sliderMoved.connect(self.seek_song)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #3c3c3c;
                height: 8px;
                background: #3c3c3c;
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: red;
                border: 1px solid #3c3c3c;
                width: 10px;
                margin: -2px 0;
                border-radius: 5px;
            }
        """)
        
        self.progress_label = QLabel("0:00 / 0:00")
        self.progress_label.setStyleSheet("color: white;")

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(200, 200)
        self.cover_label.setStyleSheet("background-color: #333; border: 1px solid #444;")
        
        self.title_label = QLabel("Musically mine")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: red; font-size: 16px;")

        self.theme_button = QPushButton("Dark Mode")
        self.theme_button.clicked.connect(self.toggle_theme)
        self.dark_mode = True
        self.apply_dark_theme()

        self.made_by_label = QLabel("Made By DeLL")
        self.made_by_label.setAlignment(Qt.AlignCenter)
        self.made_by_label.setStyleSheet("color: red; font-size: 12px;")

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.loop_button)  # Added loop button

        self.left_layout.addWidget(self.title_label)
        self.left_layout.addWidget(self.cover_label)
        self.left_layout.addWidget(self.theme_button)

        self.right_layout.addWidget(self.open_folder_button)
        self.right_layout.addWidget(self.song_list)
        self.right_layout.addLayout(button_layout)
        self.right_layout.addWidget(self.volume_label)
        self.right_layout.addWidget(self.volume_slider)
        self.right_layout.addWidget(self.progress_slider)
        self.right_layout.addWidget(self.progress_label)
        self.right_layout.addWidget(self.made_by_label)  # Moved made_by_label here

        self.main_layout.addLayout(self.left_layout)
        self.main_layout.addLayout(self.right_layout)
        self.setLayout(self.main_layout)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QListWidget, QSlider, QLabel, QPushButton {
                background-color: #3c3c3c;
                border: 1px solid #555555;
            }
            QPushButton {
                background-color: #555555;
                border: 1px solid #666666;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)

    def apply_light_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                color: #000000;
            }
            QListWidget, QSlider, QLabel, QPushButton {
                background-color: #ffffff;
                border: 1px solid #cccccc;
            }
            QPushButton {
                background-color: #dddddd;
                border: 1px solid #bbbbbb;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #cccccc;
            }
        """)

    def toggle_theme(self):
        if self.dark_mode:
            self.apply_light_theme()
            self.theme_button.setText("Dark Mode")
        else:
            self.apply_dark_theme()
            self.theme_button.setText("Light Mode")
        self.dark_mode = not self.dark_mode

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", self.last_folder_path)
        if folder_path:
            self.load_songs(folder_path)
            self.settings.setValue("last_folder_path", folder_path)

    def load_songs(self, folder_path):
        self.song_list.clear()
        for file_name in os.listdir(folder_path):
            if file_name.endswith('.mp3'):
                self.song_list.addItem(os.path.join(folder_path, file_name))

    def play_selected_song(self, item):
        self.play_song(item.text())

    def play_song(self, song_path=None):
        if song_path:
            self.current_song_path = song_path
        else:
            item = self.song_list.currentItem()
            if item:
                self.current_song_path = item.text()

        if self.current_song_path:
            mixer.music.load(self.current_song_path)
            mixer.music.play()
            self.is_playing = True
            self.is_paused = False  # Reset paused state
            self.update_progress()  # Immediately update the progress bar
            self.load_cover_art()

    def pause_resume_song(self):
        if self.is_playing and not self.is_paused:
            mixer.music.pause()
            self.is_paused = True
        elif self.is_paused:
            mixer.music.unpause()
            self.is_paused = False

    def stop_song(self):
        mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.progress_slider.setValue(0)
        self.progress_label.setText("0:00 / 0:00")

    def set_volume(self, value):
        mixer.music.set_volume(value / 100.0)

    def update_progress(self):
        if self.is_playing and not self.is_paused and mixer.music.get_busy():
            current_pos = mixer.music.get_pos() // 1000
            song_length = MP3(self.current_song_path).info.length
            self.progress_slider.setMaximum(int(song_length))
            self.progress_slider.setValue(current_pos)

            current_time = self.format_time(current_pos)
            total_time = self.format_time(song_length)
            self.progress_label.setText(f"{current_time} / {total_time}")

            # If looping is enabled and song has ended, replay the song
            if self.is_looping and current_pos >= song_length:
                mixer.music
    def seek_song(self, position):
        if self.current_song_path and (self.is_playing or self.is_paused):
            mixer.music.load(self.current_song_path)
            mixer.music.play(start=position)
            mixer.music.set_pos(position)

    def format_time(self, seconds):
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}:{seconds:02}"

    def load_cover_art(self):
        if self.cover_thread and self.cover_thread.is_alive():
            return

        self.cover_thread = threading.Thread(target=self.load_cover_art_thread)
        self.cover_thread.start()

    def load_cover_art_thread(self):
        try:
            audio = MP3(self.current_song_path, ID3=ID3)
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    cover_data = tag.data
                    pixmap = QPixmap()
                    pixmap.loadFromData(cover_data)
                    self.cover_label.setPixmap(pixmap.scaled(self.cover_label.size(), Qt.KeepAspectRatio))
                    return
            self.cover_label.clear()
        except Exception as e:
            print(f"Error loading cover art: {e}")
            self.cover_label.clear()

    def toggle_loop(self):
        self.is_looping = not self.is_looping
        if self.is_looping:
            self.loop_button.setStyleSheet("background-color: red;")
        else:
            self.loop_button.setStyleSheet("")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = MusicPlayer()
    player.show()
    sys.exit(app.exec_())