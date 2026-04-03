from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.metrics import dp
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton

from pydbus import SystemBus, SessionBus

class MediaPanel(MDCard):
    title = StringProperty("No track playing")
    artist = StringProperty("Unknown Artist")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.orientation = "vertical"
        self.padding = dp(20)
        self.spacing = dp(10)
        self.size_hint = (None, None)
        self.size = (dp(400), dp(250))
        self.radius = [dp(25)]
        self.elevation = 4
        self.theme_bg_color="Custom"
        self.md_bg_color=(0.15, 0.15, 0.18, 1)

        self.bus = None
        self.session_bus = None
        self.player = None
        self.spotify = None

        # ---------- INFO ----------
        info_box = MDBoxLayout(orientation='vertical', spacing=dp(5), size_hint_y=0.6)

        self.title_label = MDLabel(
            text=self.title,
            halign="center",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            bold=True,
        )

        self.artist_label = MDLabel(
            text=self.artist,
            halign="center",
            theme_text_color="Custom",
            text_color=(0.7, 0.7, 0.7, 1),
        )

        info_box.add_widget(self.title_label)
        info_box.add_widget(self.artist_label)

        # ---------- CONTROLS ----------
        controls_box = MDBoxLayout(
            orientation='horizontal',
            spacing=dp(20),
            adaptive_size=True,
            pos_hint={'center_x': 0.5}
        )

        self.btn_prev = MDIconButton(icon="skip-previous", font_size=dp(40))
        self.btn_play = MDIconButton(icon="play-circle", font_size=dp(64))
        self.btn_next = MDIconButton(icon="skip-next", font_size=dp(40))

        self.btn_prev.bind(on_release=self.prev_track)
        self.btn_play.bind(on_release=self.toggle_play)
        self.btn_next.bind(on_release=self.next_track)

        controls_box.add_widget(self.btn_prev)
        controls_box.add_widget(self.btn_play)
        controls_box.add_widget(self.btn_next)

        self.add_widget(info_box)
        self.add_widget(controls_box)

        # ---------- DBUS ----------
        try:
            from pydbus import SystemBus, SessionBus
            self.bus = SystemBus()
            self.session_bus = SessionBus()
        except Exception as e:
            print("DBus error:", e)

        Clock.schedule_interval(self.update_metadata, 1)

        self.bind(title=lambda _, t: setattr(self.title_label, 'text', t))
        self.bind(artist=lambda _, a: setattr(self.artist_label, 'text', a))

    # -----------------------------
    # PLAYER CONTROLS
    # -----------------------------
    def toggle_play(self, *args):
        try:
            if self.spotify:
                status = self.spotify.PlaybackStatus
                if status == "Playing":
                    self.spotify.Pause()
                else:
                    self.spotify.Play()
            elif self.player:
                if self.player.Status == "playing":
                    self.player.Pause()
                else:
                    self.player.Play()
        except Exception as e:
            print("Play error:", e)

    def next_track(self, *args):
        try:
            if self.spotify:
                self.spotify.Next()
            elif self.player:
                self.player.Next()
        except Exception as e:
            print("Next error:", e)

    def prev_track(self, *args):
        try:
            if self.spotify:
                self.spotify.Previous()
            elif self.player:
                self.player.Previous()
        except Exception as e:
            print("Prev error:", e)

    # -----------------------------
    # METADATA
    # -----------------------------
    def update_metadata(self, dt):
        # Try Spotify (MPRIS)
        try:
            self.spotify = self.session_bus.get(
                "org.mpris.MediaPlayer2.spotify",
                "/org/mpris/MediaPlayer2"
            )

            metadata = self.spotify.Metadata
            self.title = metadata.get('xesam:title', 'No track')
            self.artist = metadata.get('xesam:artist', ['Unknown'])[0]

            status = self.spotify.PlaybackStatus
            self.btn_play.icon = "pause-circle" if status == "Playing" else "play-circle"
            return

        except:
            self.spotify = None

        # Try Bluetooth player
        try:
            mngr = self.bus.get('org.bluez', '/')
            objects = mngr.GetManagedObjects()

            for path, interfaces in objects.items():
                if 'org.bluez.MediaPlayer1' not in interfaces:
                    continue

                self.player = self.bus.get('org.bluez', path)
                track = self.player.Track

                self.title = track.get('Title', 'No track')
                self.artist = track.get('Artist', 'Unknown')

                status = self.player.Status
                self.btn_play.icon = "pause-circle" if status == "playing" else "play-circle"
                return

        except:
            pass

        # Nothing playing
        self.title = "No track playing"
        self.artist = "Unknown Artist"
        self.btn_play.icon = "play-circle"
