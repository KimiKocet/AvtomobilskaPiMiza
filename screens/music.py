from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from widgets.MediaPanel import MediaPanel


class MusicScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = BoxLayout(orientation="horizontal", padding=dp(22), spacing=dp(18))

        left = MDCard(
            orientation="vertical",
            padding=dp(24),
            spacing=dp(10),
            radius=[dp(30)],
            elevation=0,
            md_bg_color=(0.08, 0.11, 0.16, 0.98),
            size_hint=(0.42, 1),
        )
        left.add_widget(
            MDLabel(
                text="Media",
                theme_text_color="Custom",
                text_color=(0.98, 0.99, 1, 1),
                bold=True,
                font_style="H4",
            )
        )
        left.add_widget(
            MDLabel(
                text="Touch-friendly playback controls for quick use while driving.",
                theme_text_color="Custom",
                text_color=(0.65, 0.72, 0.8, 1),
            )
        )
        left.add_widget(_FeatureCard("Spotify", "Reads MPRIS metadata and transport state."))
        left.add_widget(_FeatureCard("Bluetooth", "Falls back to BlueZ media players automatically."))
        left.add_widget(_FeatureCard("Large targets", "Bigger controls make the screen easier to use in the car."))

        right = AnchorLayout(size_hint=(0.58, 1))
        right.add_widget(MediaPanel(compact=True, size_hint=(0.94, 0.78)))

        root.add_widget(left)
        root.add_widget(right)
        self.add_widget(root)


class _FeatureCard(MDCard):
    def __init__(self, title, body, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = dp(16)
        self.spacing = dp(6)
        self.radius = [dp(24)]
        self.elevation = 0
        self.md_bg_color = (0.11, 0.15, 0.21, 1)
        self.size_hint_y = None
        self.height = dp(116)
        self.add_widget(
            MDLabel(
                text=title,
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=(0.38, 0.78, 1, 1),
                bold=True,
            )
        )
        self.add_widget(
            MDLabel(
                text=body,
                theme_text_color="Custom",
                text_color=(0.84, 0.89, 0.95, 1),
            )
        )
