from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivymd.uix.button import MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from pydbus import SessionBus, SystemBus


class MediaPanel(MDCard):
    title = StringProperty("No track playing")
    artist = StringProperty("Connect Spotify or Bluetooth")
    source = StringProperty("Idle")
    state = StringProperty("Waiting")

    def __init__(self, compact=False, **kwargs):
        super().__init__(**kwargs)

        self.compact = compact
        self.orientation = "vertical"
        self.padding = dp(22)
        self.spacing = dp(14)
        self.size_hint = (1, 1) if compact else (None, None)
        self.size = (dp(360), dp(250))
        self.radius = [dp(28)]
        self.elevation = 0
        self.md_bg_color = (0.09, 0.12, 0.17, 0.96)

        self.bus = None
        self.session_bus = None
        self.player = None
        self.spotify = None

        top_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30))
        self.source_label = MDLabel(
            text=self.source,
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=(0.56, 0.78, 0.99, 1),
            bold=True,
        )
        status_chip = _Chip(text="Now Playing")
        top_row.add_widget(self.source_label)
        top_row.add_widget(status_chip)

        track_box = BoxLayout(orientation="vertical", spacing=dp(6))
        self.title_label = MDLabel(
            text=self.title,
            theme_text_color="Custom",
            text_color=(0.98, 0.99, 1, 1),
            bold=True,
            font_style="H5",
        )
        self.artist_label = MDLabel(
            text=self.artist,
            theme_text_color="Custom",
            text_color=(0.63, 0.71, 0.81, 1),
        )
        self.track_hint = MDLabel(
            text="Large controls, quick glance metadata, Bluetooth and Spotify support.",
            theme_text_color="Custom",
            text_color=(0.47, 0.54, 0.62, 1),
        )
        track_box.add_widget(self.title_label)
        track_box.add_widget(self.artist_label)
        track_box.add_widget(self.track_hint)

        controls_box = BoxLayout(
            orientation="horizontal",
            spacing=dp(14),
            size_hint_y=None,
            height=dp(78),
        )

        self.btn_prev = self._build_button("skip-previous", dp(42))
        self.btn_play = self._build_button("play-circle", dp(64), accent=True)
        self.btn_next = self._build_button("skip-next", dp(42))

        self.btn_prev.bind(on_release=self.prev_track)
        self.btn_play.bind(on_release=self.toggle_play)
        self.btn_next.bind(on_release=self.next_track)

        controls_box.add_widget(self.btn_prev)
        controls_box.add_widget(self.btn_play)
        controls_box.add_widget(self.btn_next)

        footer = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(26))
        self.source_stat = _MiniStat("SRC", self.source)
        self.state_stat = _MiniStat("STATE", self.state)
        footer.add_widget(self.source_stat)
        footer.add_widget(self.state_stat)

        self.add_widget(top_row)
        self.add_widget(track_box)
        self.add_widget(Widget())
        self.add_widget(controls_box)
        self.add_widget(footer)

        try:
            self.bus = SystemBus()
            self.session_bus = SessionBus()
        except Exception as exc:
            print("DBus error:", exc)

        Clock.schedule_interval(self.update_metadata, 1)

        self.bind(title=lambda _, value: setattr(self.title_label, "text", value))
        self.bind(artist=lambda _, value: setattr(self.artist_label, "text", value))
        self.bind(source=self._sync_source)
        self.bind(source=lambda _, value: self.source_stat.set_value(value))
        self.bind(state=lambda _, value: self.state_stat.set_value(value))

    def _build_button(self, icon_name, font_size, accent=False):
        button = MDIconButton(icon=icon_name, font_size=font_size)
        button.theme_icon_color = "Custom"
        button.icon_color = (0.96, 0.98, 1, 1) if accent else (0.78, 0.84, 0.92, 1)
        return button

    def _sync_source(self, *_):
        self.source_label.text = self.source

    def toggle_play(self, *args):
        try:
            if self.spotify:
                if self.spotify.PlaybackStatus == "Playing":
                    self.spotify.Pause()
                else:
                    self.spotify.Play()
            elif self.player:
                if self.player.Status == "playing":
                    self.player.Pause()
                else:
                    self.player.Play()
        except Exception as exc:
            print("Play error:", exc)

    def next_track(self, *args):
        try:
            if self.spotify:
                self.spotify.Next()
            elif self.player:
                self.player.Next()
        except Exception as exc:
            print("Next error:", exc)

    def prev_track(self, *args):
        try:
            if self.spotify:
                self.spotify.Previous()
            elif self.player:
                self.player.Previous()
        except Exception as exc:
            print("Prev error:", exc)

    def update_metadata(self, dt):
        try:
            self.spotify = self.session_bus.get(
                "org.mpris.MediaPlayer2.spotify",
                "/org/mpris/MediaPlayer2",
            )
            metadata = self.spotify.Metadata
            self.title = metadata.get("xesam:title", "No track")
            self.artist = metadata.get("xesam:artist", ["Unknown"])[0]
            self.source = "Spotify"
            self.state = self.spotify.PlaybackStatus
            self.btn_play.icon = "pause-circle" if self.spotify.PlaybackStatus == "Playing" else "play-circle"
            return
        except Exception:
            self.spotify = None

        try:
            manager = self.bus.get("org.bluez", "/")
            objects = manager.GetManagedObjects()
            for path, interfaces in objects.items():
                if "org.bluez.MediaPlayer1" not in interfaces:
                    continue

                self.player = self.bus.get("org.bluez", path)
                track = self.player.Track
                self.title = track.get("Title", "No track")
                self.artist = track.get("Artist", "Unknown")
                self.source = "Bluetooth"
                self.state = self.player.Status.title()
                self.btn_play.icon = "pause-circle" if self.player.Status == "playing" else "play-circle"
                return
        except Exception:
            self.player = None

        self.title = "No track playing"
        self.artist = "Connect Spotify or Bluetooth"
        self.source = "Idle"
        self.state = "Waiting"
        self.btn_play.icon = "play-circle"


class _Chip(MDCard):
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(118), dp(30))
        self.radius = [dp(15)]
        self.elevation = 0
        self.md_bg_color = (0.14, 0.18, 0.24, 1)
        self.padding = (dp(12), 0)
        self.add_widget(
            MDLabel(
                text=text,
                halign="center",
                theme_text_color="Custom",
                text_color=(0.78, 0.84, 0.92, 1),
            )
        )


class _MiniStat(MDCard):
    def __init__(self, title, value, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = dp(10)
        self.spacing = dp(2)
        self.radius = [dp(18)]
        self.elevation = 0
        self.md_bg_color = (0.12, 0.15, 0.2, 1)
        self.add_widget(
            MDLabel(
                text=title,
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=(0.45, 0.52, 0.6, 1),
            )
        )
        self.value_label = MDLabel(
            text=value,
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=(0.94, 0.97, 1, 1),
            bold=True,
        )
        self.add_widget(self.value_label)

    def set_value(self, value):
        self.value_label.text = value
