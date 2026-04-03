# widgets/gauge.py

import math
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.properties import NumericProperty
from kivy.graphics import Color, Line, Ellipse
from kivy.metrics import dp

class SpeedRpmGauge(FloatLayout):
    speed = NumericProperty(0)
    rpm = NumericProperty(0)
    max_rpm = NumericProperty(7000)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Speed value
        self.speed_value = Label(
            text="0",
            font_size=dp(80),
            bold=True,
            pos_hint={"center_x": 0.5, "center_y": 0.52},
            size_hint=(None, None),
            size=(dp(200), dp(100)),
            halign="center",
            valign="middle",
            color=(1, 1, 1, 1)
        )
        self.speed_value.bind(size=lambda inst, val: setattr(inst, "text_size", val))

        # Speed unit
        self.speed_unit = Label(
            text="km/h",
            font_size=dp(20),
            pos_hint={"center_x": 0.5, "center_y": 0.42},
            size_hint=(None, None),
            size=(dp(100), dp(40)),
            halign="center",
            valign="middle",
            color=(0.7, 0.7, 0.7, 1)
        )
        self.speed_unit.bind(size=lambda inst, val: setattr(inst, "text_size", val))

        self.add_widget(self.speed_value)
        self.add_widget(self.speed_unit)

        self.bind(pos=self.redraw, size=self.redraw)
        self.bind(speed=self.update_speed)
        self.bind(rpm=self.redraw)

    def update_speed(self, *args):
        try:
            self.speed_value.text = str(int(self.speed))
        except:
            self.speed_value.text = str(self.speed)

    def redraw(self, *args):
        self.canvas.before.clear()
        self.canvas.clear()
        
        cx, cy = self.center_x, self.center_y
        radius = min(self.width, self.height) * 0.42

        start_deg = 240
        sweep_deg = -240
        num_ticks = 41

        with self.canvas:
            Color(0.2, 0.2, 0.2, 1)
            Line(circle=(cx, cy, radius), width=dp(4))

            for i in range(num_ticks):
                ratio = i / (num_ticks - 1)
                angle_deg = start_deg + (ratio * sweep_deg)
                angle = math.radians(angle_deg)
                is_major = (i % 5 == 0)
                
                inner_r = radius * (0.80 if is_major else 0.88)
                outer_r = radius * 0.98

                x1 = cx + inner_r * math.cos(angle)
                y1 = cy + inner_r * math.sin(angle)
                x2 = cx + outer_r * math.cos(angle)
                y2 = cy + outer_r * math.sin(angle)

                rpm_at_tick = ratio * self.max_rpm
                
                if rpm_at_tick <= self.rpm:
                    if rpm_at_tick >= 6000:
                        Color(1, 0.3, 0.3, 1)
                    else:
                        Color(0.3, 0.8, 1, 1)
                else:
                    if rpm_at_tick >= 6000:
                        Color(0.5, 0, 0, 0.5)
                    else:
                        Color(0.4, 0.4, 0.4, 1)

                Line(points=[x1, y1, x2, y2], width=dp(3) if is_major else dp(1.5))

            Color(0.15, 0.15, 0.15, 1)
            Ellipse(pos=(cx - radius*0.35, cy - radius*0.35), size=(radius*0.7, radius*0.7))