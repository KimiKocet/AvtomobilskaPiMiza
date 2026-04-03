# ---------- Python ----------
import math

# ---------- Kivy ----------
from kivy.uix.screenmanager import Screen
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.metrics import dp

# ---------- KivyMD ----------
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton

# ---------- DBus ----------
from pydbus import SystemBus, SessionBus

class MusicScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ---------------- DBUS ----------------
        try:
            self.sys_bus = SystemBus()
            self.sess_bus = SessionBus()
        except:
            self.sys_bus = None
            self.sess_bus = None

        self.spotify = None
        self.bt_player = None

        # ---------------- UI ----------------
        root = AnchorLayout(anchor_x="center", anchor_y="center")

        card = MDCard(
            orientation="vertical",
            size_hint=(0.75, 0.7),
            padding=30,
            spacing=20,
            radius=[25],
            elevation=4,
            theme_bg_color="Custom",
            md_bg_color=(0.15, 0.15, 0.18, 1)
        )

        self.title_label = MDLabel(text="No track", halign="center", theme_text_color="Custom", text_color=(1, 1, 1, 1), bold=True, font_style="Headline", role="medium")
        self.artist_label = MDLabel(text="", halign="center", theme_text_color="Custom", text_color=(1, 1, 1, 1))
        self.album_label = MDLabel(text="", halign="center", theme_text_color="Custom", text_color=(1, 1, 1, 1))
        self.dev_label = MDLabel(text="No device", halign="center", theme_text_color="Custom", text_color=(1, 1, 1, 1))

        card.add_widget(self.title_label)
        card.add_widget(self.artist_label)
        card.add_widget(self.album_label)
        card.add_widget(self.dev_label)

        controls = BoxLayout(size_hint_y=None, height=dp(80), spacing=40)

        self.btn_play = MDIconButton(icon="play-circle", font_size=dp(48))
        self.btn_next = MDIconButton(icon="skip-next", font_size=dp(48))

        self.btn_play.bind(on_press=self.toggle_play)
        self.btn_next.bind(on_press=self.next_track)

        controls.add_widget(self.btn_play)
        controls.add_widget(self.btn_next)
        card.add_widget(controls)

        root.add_widget(card)
        self.add_widget(root)

        Clock.schedule_interval(self.update_metadata, 1)

    # =====================================================
    # CONTROLS
    # =====================================================

    def toggle_play(self, *args):
        try:
            if self.spotify:
                status = self.spotify.PlaybackStatus
                if status == "Playing":
                    self.spotify.Pause()
                else:
                    self.spotify.Play()

            elif self.bt_player:
                if self.bt_player.Status == "playing":
                    self.bt_player.Pause()
                else:
                    self.bt_player.Play()

        except Exception as e:
            print("Play error:", e)

    def next_track(self, *args):
        try:
            if self.spotify:
                self.spotify.Next()
            elif self.bt_player:
                self.bt_player.Next()
        except Exception as e:
            print("Next error:", e)

    # =====================================================
    # METADATA
    # =====================================================

    def update_metadata(self, dt):

        # ---------- SPOTIFY ----------
        try:
            self.spotify = self.sess_bus.get(
                "org.mpris.MediaPlayer2.spotify",
                "/org/mpris/MediaPlayer2"
            )

            metadata = self.spotify.Metadata

            self.title_label.text = metadata.get('xesam:title', 'No track')
            self.artist_label.text = metadata.get('xesam:artist', ['Unknown'])[0]
            self.album_label.text = metadata.get('xesam:album', '')
            self.dev_label.text = "Spotify"

            status = self.spotify.PlaybackStatus
            self.btn_play.icon = "pause-circle" if status == "Playing" else "play-circle"

            return

        except:
            self.spotify = None

        # ---------- BLUETOOTH ----------
        try:
            mngr = self.sys_bus.get('org.bluez', '/')
            objects = mngr.GetManagedObjects()

            for path, interfaces in objects.items():

                if 'org.bluez.MediaPlayer1' not in interfaces:
                    continue

                self.bt_player = self.sys_bus.get('org.bluez', path)
                track = self.bt_player.Track

                self.title_label.text = track.get('Title', 'No track')
                self.artist_label.text = track.get('Artist', 'Unknown')
                self.album_label.text = track.get('Album', '')
                self.dev_label.text = "Bluetooth"

                status = self.bt_player.Status
                self.btn_play.icon = "pause-circle" if status == "playing" else "play-circle"

                return

        except:
            pass

        # ---------- NOTHING ----------
        self.title_label.text = "No track"
        self.artist_label.text = ""
        self.album_label.text = ""
        self.dev_label.text = "No device"
        self.btn_play.icon = "play-circle"