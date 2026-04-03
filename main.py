# main.py

from kivy.config import Config
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Color, RoundedRectangle
from kivymd.app import MDApp
from kivymd.uix.button import MDIconButton

# Import screens
from screens.home import HomeScreen
from screens.music import MusicScreen
from screens.map import MapScreen
from screens.settings import SettingsScreen

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen

# -----------------------------
# Keep window on top and prevent minimize
# -----------------------------
Window.top = True  # keep window above others

def on_focus(window, focus):
    if not focus:
        Window.raise_window()  # bring back if focus lost

Window.bind(on_focus=on_focus)

# Window setup
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '600')
Config.set('graphics', 'fullscreen', '0')
Window.size = (1024, 600)


# ----------------------
# MAIN SCREEN
# ----------------------
class MainScreen(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"

        # -------- LEFT MENU --------
        self.menu_layout = BoxLayout(
            orientation='vertical',
            size_hint=(None, 1),
            width=120,
            padding=10
        )

        with self.menu_layout.canvas.before:
            Color(0.3, 0.3, 0.3, 0.6)
            self.bg_rect = RoundedRectangle(radius=[20])

        self.menu_layout.bind(pos=self.update_bg, size=self.update_bg)

        def create_menu_button(icon_name, screen_name):
            btn = MDIconButton(icon=icon_name)
            btn.font_size = "64sp"
            btn.theme_icon_color = "Custom"
            btn.icon_color = (1, 1, 1, 1)
            btn.size_hint=(1, 1)
            btn.bind(on_press=lambda inst: self.change_screen(screen_name))
            return btn

        button_grid = GridLayout(cols=1, rows=4, spacing=20)

        for icon, name in [
            ("home", "home"),
            ("music-note", "music"),
            ("map", "maps"),
            ("cog", "settings")
        ]:
            button_grid.add_widget(create_menu_button(icon, name))

        self.menu_layout.add_widget(button_grid)
        self.add_widget(self.menu_layout)

        # -------- SCREEN MANAGER --------
        self.sm = ScreenManager()
        self.sm.add_widget(HomeScreen(name="home"))
        self.sm.add_widget(MusicScreen(name="music"))
        self.sm.add_widget(MapScreen(name="maps"))
        self.sm.add_widget(SettingsScreen(name="settings"))

        self.add_widget(self.sm)

    def update_bg(self, *args):
        self.bg_rect.pos = self.menu_layout.pos
        self.bg_rect.size = self.menu_layout.size

    def change_screen(self, name):
        self.sm.current = name


# ----------------------
# APP
# ----------------------
class CarPCApp(MDApp):

    def build(self):
        Window.fullscreen = True
        return MainScreen()


if __name__ == "__main__":
    CarPCApp().run()
