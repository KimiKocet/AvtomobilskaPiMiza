from kivy.config import Config

# Touchscreens can expose both a multitouch provider and a mouse-emulated
# provider. Discard the mouse event when real touch activity exists so a
# single tap does not trigger button releases twice.
Config.set("input", "mouse", "mouse,disable_on_activity,disable_multitouch")
Config.set("graphics", "width", "1024")
Config.set("graphics", "height", "600")
Config.set("graphics", "fullscreen", "0")

from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import ScreenManager
from kivymd.app import MDApp
from kivymd.uix.label import MDIcon, MDLabel

from screens.home import HomeScreen
from screens.map import MapScreen
from screens.music import MusicScreen
from screens.settings import SettingsScreen
from services.gps import gps_service
from services.theme import theme_service

Window.top = True


def on_focus(window, focus):
    if not focus:
        Window.raise_window()


Window.bind(on_focus=on_focus)

Window.size = (1024, 600)


class MainScreen(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            self.bg_color = Color(0.01, 0.02, 0.05, 1)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size)
            self.glow_left_color = Color(0.09, 0.29, 0.46, 0.22)
            self.glow_left = Ellipse(size=(dp(420), dp(420)))
            self.glow_right_color = Color(0.9, 0.37, 0.18, 0.12)
            self.glow_right = Ellipse(size=(dp(360), dp(360)))
        self.bind(pos=self._update_background, size=self._update_background)

        shell = BoxLayout(
            orientation="horizontal",
            spacing=dp(18),
            padding=(dp(16), dp(16), dp(16), dp(16)),
        )

        self.menu_layout = BoxLayout(
            orientation="vertical",
            size_hint=(None, 1),
            width=dp(148),
            padding=(dp(14), dp(18), dp(14), dp(18)),
            spacing=dp(16),
        )
        with self.menu_layout.canvas.before:
            self.menu_bg_color = Color(0.06, 0.09, 0.14, 0.98)
            self.menu_bg = RoundedRectangle(radius=[dp(30)])
        self.menu_layout.bind(pos=self._update_menu_bg, size=self._update_menu_bg)

        brand_box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(96), spacing=dp(2))
        self.brand_title = MDLabel(
            text="Drive",
            theme_text_color="Custom",
            text_color=(0.98, 0.99, 1, 1),
            bold=True,
            font_style="H4",
        )
        self.brand_subtitle = MDLabel(
            text="Media + telemetry",
            theme_text_color="Custom",
            text_color=(0.45, 0.77, 1, 1),
        )
        brand_box.add_widget(self.brand_title)
        brand_box.add_widget(self.brand_subtitle)
        self.menu_layout.add_widget(brand_box)

        self.nav_buttons = {}
        for icon, label, name in [
            ("home-variant", "Home", "home"),
            ("music-note", "Music", "music"),
            ("map", "Map", "maps"),
            ("cog", "Setup", "settings"),
        ]:
            button = NavButton(icon_name=icon, label_text=label)
            button.bind(on_release=lambda _, screen=name: self.change_screen(screen))
            self.nav_buttons[name] = button
            self.menu_layout.add_widget(button)

        self.menu_layout.add_widget(BoxLayout())
        self.layout_label = MDLabel(
            text="BMW 116i",
            size_hint_y=None,
            height=dp(28),
            halign="center",
            theme_text_color="Custom",
            text_color=(0.36, 0.43, 0.51, 1),
        )
        self.menu_layout.add_widget(self.layout_label)

        content_shell = BoxLayout(orientation="vertical")
        with content_shell.canvas.before:
            self.content_bg_color = Color(0.05, 0.07, 0.11, 0.72)
            self.content_bg = RoundedRectangle(radius=[dp(34)])
        content_shell.bind(pos=self._update_content_bg, size=self._update_content_bg)

        self.sm = ScreenManager()
        self.sm.add_widget(HomeScreen(name="home"))
        self.sm.add_widget(MusicScreen(name="music"))
        self.sm.add_widget(MapScreen(name="maps"))
        self.sm.add_widget(SettingsScreen(name="settings"))
        content_shell.add_widget(self.sm)

        shell.add_widget(self.menu_layout)
        shell.add_widget(content_shell)
        self.add_widget(shell)

        theme_service.bind(mode=self._apply_theme)
        self._apply_theme()
        self.change_screen("home")

    def _update_background(self, *_):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.glow_left.pos = (self.x - dp(120), self.top - dp(320))
        self.glow_right.pos = (self.right - dp(260), self.y - dp(120))

    def _update_menu_bg(self, *_):
        self.menu_bg.pos = self.menu_layout.pos
        self.menu_bg.size = self.menu_layout.size

    def _update_content_bg(self, instance, *_):
        self.content_bg.pos = instance.pos
        self.content_bg.size = instance.size

    def change_screen(self, name):
        self.sm.current = name
        for screen_name, button in self.nav_buttons.items():
            button.set_active(screen_name == name)

    def _apply_theme(self, *_):
        palette = theme_service.palette
        self.bg_color.rgba = palette["app_bg"]
        self.glow_left_color.rgba = palette["glow_blue"]
        self.glow_right_color.rgba = palette["glow_warm"]
        self.menu_bg_color.rgba = palette["menu_bg"]
        self.content_bg_color.rgba = palette["content_bg"]
        self.brand_title.text_color = palette["text"]
        self.brand_subtitle.text_color = palette["accent"]
        self.layout_label.text_color = palette["subtle"]
        for button in self.nav_buttons.values():
            button.apply_theme()


class NavButton(ButtonBehavior, AnchorLayout):
    def __init__(self, icon_name, label_text, **kwargs):
        super().__init__(**kwargs)
        self.active = False
        self.anchor_x = "center"
        self.anchor_y = "center"
        self.size_hint_y = None
        self.height = dp(104)

        with self.canvas.before:
            self.bg_color = Color(0.1, 0.13, 0.18, 1)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(24)])
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.content = BoxLayout(
            orientation="vertical",
            size_hint=(1, 1),
            spacing=dp(6),
            padding=(0, 0),
        )
        
        icon_anchor = AnchorLayout(anchor_x="center", anchor_y="center", size_hint=(1, 0.6))
        self.icon = MDIcon(
            icon=icon_name,
            theme_text_color="Custom",
            size_hint=(None, None),
            size=(dp(40), dp(40)),
        )
        self.icon.font_size = dp(36)
        self.icon.text_color = (0.57, 0.65, 0.75, 1)
        icon_anchor.add_widget(self.icon)
        
        label_anchor = AnchorLayout(anchor_x="center", anchor_y="center", size_hint=(1, 0.4))
        self.label = MDLabel(
            text=label_text,
            theme_text_color="Custom",
            text_color=(0.57, 0.65, 0.75, 1),
            bold=True,
            size_hint_y=None,
            height=dp(16),
        )
        label_anchor.add_widget(self.label)
        
        self.content.add_widget(icon_anchor)
        self.content.add_widget(label_anchor)
        self.add_widget(self.content)
        theme_service.bind(mode=self.apply_theme)
        self.apply_theme()

    def _update_bg(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def set_active(self, active):
        self.active = active
        self.apply_theme()

    def apply_theme(self, *_):
        palette = theme_service.palette
        self.bg_color.rgba = palette["nav_active"] if self.active else palette["nav_bg"]
        self.icon.text_color = palette["text"] if self.active else palette["subtle"]
        self.label.text_color = palette["text"] if self.active else palette["subtle"]
        self._update_bg()


class CarPCApp(MDApp):
    def build(self):
        self.set_theme_mode(theme_service.mode)
        Window.fullscreen = True
        gps_service.start("/dev/ttyACM0")
        return MainScreen()

    def on_stop(self):
        gps_service.stop()

    def set_theme_mode(self, mode):
        theme_service.set_mode(mode)
        self.theme_cls.theme_style = "Light" if theme_service.mode == "light" else "Dark"


if __name__ == "__main__":
    CarPCApp().run()
