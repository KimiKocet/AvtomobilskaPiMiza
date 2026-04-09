from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDIcon, MDLabel

from pydbus import SessionBus, SystemBus

from services.theme import theme_service


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

        self.bus = None
        self.session_bus = None
        self.player = None
        self.spotify = None

        top_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30))
        self.source_label = MDLabel(
            text=self.source,
            adaptive_height=True,
            theme_text_color="Custom",
            bold=True,
        )
        self.status_chip = _Chip(text="Now Playing")
        top_row.add_widget(self.source_label)
        top_row.add_widget(self.status_chip)

        track_box = BoxLayout(orientation="vertical", spacing=dp(6))
        self.title_label = MDLabel(
            text=self.title,
            theme_text_color="Custom",
            bold=True,
            font_style="H5",
        )
        self.artist_label = MDLabel(
            text=self.artist,
            theme_text_color="Custom",
        )
        self.track_hint = MDLabel(
            text="Large controls, quick glance metadata, Bluetooth and Spotify support.",
            theme_text_color="Custom",
        )
        track_box.add_widget(self.title_label)
        track_box.add_widget(self.artist_label)
        track_box.add_widget(self.track_hint)

        controls_box = BoxLayout(
            orientation="horizontal",
            spacing=dp(12),
            size_hint_y=None,
            height=dp(92),
        )

        self.btn_prev = _ControlSurface("skip-previous")
        self.btn_prev.size_hint_x = 1
        self.btn_play = _ControlSurface("play", accent=True)
        self.btn_play.size_hint_x = 1.2
        self.btn_next = _ControlSurface("skip-next")
        self.btn_next.size_hint_x = 1

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

        theme_service.bind(mode=self._apply_theme)
        self._apply_theme()

    def _apply_theme(self, *_):
        palette = theme_service.palette
        self.md_bg_color = palette["card_alt"]
        self.source_label.text_color = palette["accent"]
        self.title_label.text_color = palette["text"]
        self.artist_label.text_color = palette["muted"]
        self.track_hint.text_color = palette["subtle"]
        self.status_chip.apply_theme()
        self.source_stat.apply_theme()
        self.state_stat.apply_theme()
        self.btn_prev.apply_theme()
        self.btn_play.apply_theme()
        self.btn_next.apply_theme()

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
            self.btn_play.set_icon("pause" if self.spotify.PlaybackStatus == "Playing" else "play")
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
                self.btn_play.set_icon("pause" if self.player.Status == "playing" else "play")
                return
        except Exception:
            self.player = None

        self.title = "No track playing"
        self.artist = "Connect Spotify or Bluetooth"
        self.source = "Idle"
        self.state = "Waiting"
        self.btn_play.set_icon("play")


class _ControlSurface(ButtonBehavior, AnchorLayout):
    def __init__(self, icon_name, accent=False, **kwargs):
        super().__init__(**kwargs)
        self.icon_name = icon_name
        self.accent = accent
        self.anchor_x = "center"
        self.anchor_y = "center"
        self.padding = dp(6)
        self.corner_radius = [dp(24)]

        with self.canvas.before:
            self.bg_color = Color(0, 0, 0, 1)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=self.corner_radius)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.icon_widget = MDIcon(
            icon=icon_name,
            halign="center",
            valign="middle",
            theme_text_color="Custom",
            font_size="42sp" if accent else "36sp",
            size_hint=(None, None),
            size=(dp(58), dp(58)),
        )
        self.icon_widget.bind(size=self._sync_icon_text)
        self.add_widget(self.icon_widget)
        theme_service.bind(mode=self.apply_theme)
        self.apply_theme()

    def _update_bg(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def _sync_icon_text(self, widget, size):
        widget.text_size = size

    def set_icon(self, icon_name):
        self.icon_name = icon_name
        self.icon_widget.icon = icon_name

    def apply_theme(self, *_):
        palette = theme_service.palette
        self.bg_color.rgba = palette["accent_strong"] if self.accent else palette["card_soft"]
        self.icon_widget.text_color = palette["button_text"] if self.accent else palette["text"]
        self._update_bg()


class _Chip(MDCard):
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(118), dp(30))
        self.radius = [dp(15)]
        self.elevation = 0
        self.padding = (dp(12), 0)
        self.label = MDLabel(
            text=text,
            halign="center",
            theme_text_color="Custom",
        )
        self.add_widget(self.label)
        theme_service.bind(mode=self.apply_theme)
        self.apply_theme()

    def apply_theme(self, *_):
        palette = theme_service.palette
        self.md_bg_color = palette["chip"]
        self.label.text_color = palette["muted"]


class _MiniStat(MDCard):
    def __init__(self, title, value, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = dp(10)
        self.spacing = dp(2)
        self.radius = [dp(18)]
        self.elevation = 0
        self.title_label = MDLabel(
            text=title,
            adaptive_height=True,
            theme_text_color="Custom",
        )
        self.value_label = MDLabel(
            text=value,
            adaptive_height=True,
            theme_text_color="Custom",
            bold=True,
        )
        self.add_widget(self.title_label)
        self.add_widget(self.value_label)
        theme_service.bind(mode=self.apply_theme)
        self.apply_theme()

    def set_value(self, value):
        self.value_label.text = value

    def apply_theme(self, *_):
        palette = theme_service.palette
        self.md_bg_color = palette["card_soft"]
        self.title_label.text_color = palette["subtle"]
        self.value_label.text_color = palette["text"]
