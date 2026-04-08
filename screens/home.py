from time import strftime

from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from services.obd import obd_service
from widgets.MediaPanel import MediaPanel
from widgets.SpeedRpmGauge import SpeedRpmGauge


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = FloatLayout()
        with root.canvas.before:
            Color(0.02, 0.03, 0.07, 1)
            self.background = RoundedRectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._sync_background, size=self._sync_background)

        content = BoxLayout(
            orientation="horizontal",
            spacing=dp(20),
            padding=(dp(18), dp(18), dp(18), dp(18)),
        )

        left_panel = BoxLayout(orientation="vertical", size_hint=(0.62, 1))
        self.gauge = SpeedRpmGauge()
        left_panel.add_widget(self.gauge)

        right_panel = BoxLayout(orientation="vertical", size_hint=(0.38, 1), spacing=dp(16))
        self.media_panel = MediaPanel(compact=True)
        right_panel.add_widget(self.media_panel)

        info_grid = BoxLayout(orientation="vertical", spacing=dp(14), size_hint_y=0.48)
        top_stats = BoxLayout(orientation="horizontal", spacing=dp(14))
        self.speed_card = StatCard("Vehicle Speed", "0 km/h", "Live OBD")
        self.rpm_card = StatCard("Engine RPM", "0", "Combustion")
        top_stats.add_widget(self.speed_card)
        top_stats.add_widget(self.rpm_card)

        bottom_stats = BoxLayout(orientation="horizontal", spacing=dp(14))
        self.connection_card = StatCard("OBD Link", "Demo mode", "Connect in Settings")
        self.clock_card = StatCard("Clock", strftime("%H:%M"), strftime("%A"))
        bottom_stats.add_widget(self.connection_card)
        bottom_stats.add_widget(self.clock_card)

        info_grid.add_widget(top_stats)
        info_grid.add_widget(bottom_stats)
        right_panel.add_widget(info_grid)

        content.add_widget(left_panel)
        content.add_widget(right_panel)
        root.add_widget(content)
        self.add_widget(root)

        self.demo_rpm = 900
        self.anim_dir = 1
        Clock.schedule_interval(self.refresh_dashboard, 1.0 / 20.0)
        Clock.schedule_interval(self.refresh_clock, 1)

    def _sync_background(self, instance, *_):
        self.background.pos = instance.pos
        self.background.size = instance.size

    def refresh_dashboard(self, dt):
        if obd_service.connected:
            rpm = max(float(obd_service.rpm or 0), 0)
            speed = max(float(obd_service.speed or 0), 0)
            status_value = "Connected"
            status_hint = "Live telemetry"
        else:
            if self.demo_rpm >= 4200:
                self.anim_dir = -1
            elif self.demo_rpm <= 900:
                self.anim_dir = 1

            self.demo_rpm += 50 * self.anim_dir
            rpm = self.demo_rpm
            speed = rpm / 38
            status_value = "Demo mode"
            status_hint = "Connect OBD in Settings"

        self.gauge.rpm = rpm
        self.gauge.speed = speed
        self.gauge.gear_label = self._gear_for_speed(speed)

        self.speed_card.set_value(f"{int(speed)} km/h", "Wheel speed")
        self.rpm_card.set_value(f"{int(rpm)}", "Engine load")
        self.connection_card.set_value(status_value, status_hint)

    def refresh_clock(self, dt):
        self.clock_card.set_value(strftime("%H:%M"), strftime("%A"))

    @staticmethod
    def _gear_for_speed(speed):
        if speed < 5:
            return "P"
        if speed < 20:
            return "1"
        if speed < 40:
            return "2"
        if speed < 65:
            return "3"
        if speed < 95:
            return "4"
        return "5"


class StatCard(MDCard):
    def __init__(self, title, value, hint, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = dp(18)
        self.spacing = dp(8)
        self.radius = [dp(24)]
        self.elevation = 0
        self.theme_bg_color = "Custom"
        self.md_bg_color = (0.08, 0.11, 0.16, 0.98)

        self.add_widget(
            MDLabel(
                text=title,
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=(0.49, 0.58, 0.66, 1),
            )
        )
        self.value_label = MDLabel(
            text=value,
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=(0.98, 0.99, 1, 1),
            bold=True,
            font_style="Headline",
            role="small",
        )
        self.hint_label = MDLabel(
            text=hint,
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=(0.34, 0.72, 0.98, 1),
        )
        self.add_widget(self.value_label)
        self.add_widget(self.hint_label)

    def set_value(self, value, hint):
        self.value_label.text = value
        self.hint_label.text = hint
