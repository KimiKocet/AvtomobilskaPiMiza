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
        self.date_card = StatCard("Date", strftime("%d %B %Y"), strftime("%A"))
        self.clock_card = StatCard("Time", strftime("%H:%M"), "Local time")
        info_grid.add_widget(self.date_card)
        info_grid.add_widget(self.clock_card)
        right_panel.add_widget(info_grid)

        content.add_widget(left_panel)
        content.add_widget(right_panel)
        root.add_widget(content)
        self.add_widget(root)

        self.demo_rpm = 1200
        self.demo_gear = 1
        self.demo_state = "start_fall"
        self.demo_state_time = 0.0
        Clock.schedule_interval(self.refresh_dashboard, 1.0 / 20.0)
        Clock.schedule_interval(self.refresh_clock, 1)

    def _sync_background(self, instance, *_):
        self.background.pos = instance.pos
        self.background.size = instance.size

    def refresh_dashboard(self, dt):
        if obd_service.connected:
            rpm = max(float(obd_service.rpm or 0), 0)
            speed = max(float(obd_service.speed or 0), 0)
            gear = self._gear_for_speed(speed)
        else:
            rpm, speed, gear = self._advance_demo_powertrain(dt)

        self.gauge.rpm = rpm
        self.gauge.speed = speed
        self.gauge.gear_label = gear

    def refresh_clock(self, dt):
        self.clock_card.set_value(strftime("%H:%M"), "Local time")
        self.date_card.set_value(strftime("%d %B %Y"), strftime("%A"))

    @staticmethod
    def _gear_for_speed(speed):
        if speed < 5:
            return "P"
        if speed < 20:
            return "1"
        if speed < 35:
            return "2"
        if speed < 55:
            return "3"
        if speed < 80:
            return "4"
        if speed < 110:
            return "5"
        return "6"

    def _advance_demo_powertrain(self, dt):
        self.demo_state_time += dt

        if self.demo_state == "start_fall":
            progress = min(self.demo_state_time / 3.0, 1.0)
            self.demo_rpm = 1200 - (300 * progress)
            if progress >= 1.0:
                self._set_demo_state("upshift_run")
                self.demo_rpm = 900
                self.demo_gear = 1
            return self.demo_rpm, 0, "P"

        if self.demo_state == "upshift_run":
            ramp_rate = max(920 - (self.demo_gear * 65), 520)
            self.demo_rpm += ramp_rate * dt

            if self.demo_rpm >= 5000:
                if self.demo_gear < 6:
                    self.demo_gear += 1
                    self.demo_rpm = 3300 - ((self.demo_gear - 2) * 120)
                    if self.demo_gear == 6:
                        self._set_demo_state("downshift_run")

            speed = self._demo_speed_from_powertrain(self.demo_rpm, self.demo_gear)
            return self.demo_rpm, speed, str(self.demo_gear)

        if self.demo_state == "downshift_run":
            self.demo_rpm -= 300 * dt
            if self.demo_gear > 1 and self.demo_rpm <= 3000:
                self.demo_gear -= 1
                self.demo_rpm = min(3600 + (self.demo_gear * 70), 3900)

            if self.demo_gear == 1 and self.demo_rpm <= 1000:
                self.demo_rpm = 1000
                self._set_demo_state("idle_hold")
                return self.demo_rpm, 0, "P"

            speed = self._demo_speed_from_powertrain(self.demo_rpm, self.demo_gear)
            return self.demo_rpm, speed, str(self.demo_gear)

        if self.demo_state == "idle_hold":
            self.demo_rpm = 1000
            if self.demo_state_time >= 3.0:
                self._set_demo_state("engine_off")
            return self.demo_rpm, 0, "P"

        if self.demo_state == "engine_off":
            progress = min(self.demo_state_time / 1.2, 1.0)
            self.demo_rpm = max(1000 * (1.0 - progress), 0)
            if progress >= 1.0:
                self.demo_rpm = 0
                self._set_demo_state("off_pause")
            return self.demo_rpm, 0, "P"

        if self.demo_state == "off_pause":
            self.demo_rpm = 0
            if self.demo_state_time >= 1.8:
                self.demo_rpm = 1200
                self.demo_gear = 1
                self._set_demo_state("start_fall")
            return self.demo_rpm, 0, "P"

        return self.demo_rpm, 0, "P"

    def _set_demo_state(self, state):
        self.demo_state = state
        self.demo_state_time = 0.0

    @staticmethod
    def _demo_speed_from_powertrain(rpm, gear):
        gear_ratio = {
            1: 95,
            2: 72,
            3: 58,
            4: 47,
            5: 39,
            6: 33,
        }
        return max(rpm / gear_ratio.get(gear, 33), 0)


class StatCard(MDCard):
    def __init__(self, title, value, hint, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = dp(18)
        self.spacing = dp(8)
        self.radius = [dp(24)]
        self.elevation = 0
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
            font_style="H5",
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
