from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from services.theme import theme_service
from widgets.MediaPanel import MediaPanel


class MusicScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = BoxLayout(orientation="horizontal", padding=dp(22), spacing=dp(18))

        self.left = MDCard(
            orientation="vertical",
            padding=dp(24),
            spacing=dp(10),
            radius=[dp(30)],
            elevation=0,
            size_hint=(0.42, 1),
        )
        self.title_label = MDLabel(
            text="Media",
            theme_text_color="Custom",
            bold=True,
            font_style="H4",
        )
        self.copy_label = MDLabel(
            text="Touch-friendly playback controls for quick use while driving.",
            theme_text_color="Custom",
        )
        self.left.add_widget(self.title_label)
        self.left.add_widget(self.copy_label)
        self.left.add_widget(_FeatureCard("Spotify", "Reads MPRIS metadata and transport state."))
        self.left.add_widget(_FeatureCard("Bluetooth", "Falls back to BlueZ media players automatically."))
        self.left.add_widget(_FeatureCard("Large targets", "Bigger controls make the screen easier to use in the car."))

        right = AnchorLayout(size_hint=(0.58, 1))
        right.add_widget(MediaPanel(compact=True, size_hint=(0.94, 0.78)))

        root.add_widget(self.left)
        root.add_widget(right)
        self.add_widget(root)
        theme_service.bind(mode=self._apply_theme)
        self._apply_theme()

    def _apply_theme(self, *_):
        palette = theme_service.palette
        self.left.md_bg_color = palette["card"]
        self.title_label.text_color = palette["text"]
        self.copy_label.text_color = palette["muted"]


class _FeatureCard(MDCard):
    def __init__(self, title, body, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = dp(16)
        self.spacing = dp(6)
        self.radius = [dp(24)]
        self.elevation = 0
        self.size_hint_y = None
        self.height = dp(116)
        self.title_label = MDLabel(
            text=title,
            adaptive_height=True,
            theme_text_color="Custom",
            bold=True,
        )
        self.body_label = MDLabel(
            text=body,
            theme_text_color="Custom",
        )
        self.add_widget(self.title_label)
        self.add_widget(self.body_label)
        theme_service.bind(mode=self.apply_theme)
        self.apply_theme()

    def apply_theme(self, *_):
        palette = theme_service.palette
        self.md_bg_color = palette["card_soft"]
        self.title_label.text_color = palette["accent"]
        self.body_label.text_color = palette["text"]
