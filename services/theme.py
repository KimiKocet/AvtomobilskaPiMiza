from kivy.event import EventDispatcher
from kivy.properties import StringProperty


DARK_PALETTE = {
    "app_bg": (0.01, 0.02, 0.05, 1),
    "glow_blue": (0.09, 0.29, 0.46, 0.22),
    "glow_warm": (0.9, 0.37, 0.18, 0.12),
    "menu_bg": (0.06, 0.09, 0.14, 0.98),
    "content_bg": (0.05, 0.07, 0.11, 0.72),
    "nav_bg": (0.1, 0.13, 0.18, 1),
    "nav_active": (0.17, 0.4, 0.64, 1),
    "card": (0.08, 0.11, 0.16, 0.98),
    "card_alt": (0.09, 0.12, 0.17, 0.96),
    "card_soft": (0.11, 0.15, 0.21, 1),
    "chip": (0.14, 0.18, 0.24, 1),
    "button_bg": (0.17, 0.4, 0.64, 1),
    "button_bg_soft": (1, 1, 1, 0.12),
    "button_text": (1, 1, 1, 1),
    "input_bg": (0.1, 0.14, 0.2, 1),
    "input_text": (0.96, 0.98, 1, 1),
    "text": (0.98, 0.99, 1, 1),
    "muted": (0.61, 0.7, 0.79, 1),
    "subtle": (0.45, 0.52, 0.6, 1),
    "accent": (0.45, 0.77, 1, 1),
    "accent_strong": (0.22, 0.62, 0.95, 1),
    "divider": (0.18, 0.22, 0.29, 1),
}

LIGHT_PALETTE = {
    "app_bg": (0.92, 0.95, 0.98, 1),
    "glow_blue": (0.3, 0.55, 0.9, 0.08),
    "glow_warm": (0.96, 0.69, 0.44, 0.08),
    "menu_bg": (0.97, 0.98, 1, 0.98),
    "content_bg": (1, 1, 1, 0.92),
    "nav_bg": (0.91, 0.94, 0.98, 1),
    "nav_active": (0.2, 0.5, 0.88, 1),
    "card": (0.98, 0.99, 1, 0.98),
    "card_alt": (0.96, 0.98, 1, 0.98),
    "card_soft": (0.93, 0.96, 0.99, 1),
    "chip": (0.9, 0.94, 0.98, 1),
    "button_bg": (0.2, 0.5, 0.88, 1),
    "button_bg_soft": (0.17, 0.4, 0.64, 0.12),
    "button_text": (1, 1, 1, 1),
    "input_bg": (0.94, 0.97, 1, 1),
    "input_text": (0.14, 0.18, 0.24, 1),
    "text": (0.12, 0.16, 0.22, 1),
    "muted": (0.33, 0.41, 0.5, 1),
    "subtle": (0.48, 0.57, 0.66, 1),
    "accent": (0.2, 0.5, 0.88, 1),
    "accent_strong": (0.12, 0.42, 0.82, 1),
    "divider": (0.84, 0.88, 0.93, 1),
}


class ThemeService(EventDispatcher):
    mode = StringProperty("dark")

    @property
    def palette(self):
        return LIGHT_PALETTE if self.mode == "light" else DARK_PALETTE

    def set_mode(self, mode):
        normalized = (mode or "dark").lower()
        self.mode = "light" if normalized == "light" else "dark"

    def toggle(self):
        self.mode = "light" if self.mode == "dark" else "dark"


theme_service = ThemeService()
