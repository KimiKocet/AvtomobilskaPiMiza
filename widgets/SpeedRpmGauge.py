import math

from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label


class SpeedRpmGauge(FloatLayout):
    speed = NumericProperty(0)
    rpm = NumericProperty(0)
    max_rpm = NumericProperty(7000)
    gear_label = StringProperty("D")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.speed_caption = self._build_label("RPM", dp(18), (0.64, 0.72, 0.8, 1), 0.67)
        self.speed_value = self._build_label("0", dp(132), (0.98, 0.99, 1, 1), 0.54, bold=True)
        self.speed_unit = self._build_label("rev/min", dp(24), (0.64, 0.72, 0.8, 1), 0.38)

        self.gear_title = self._build_label("GEAR", dp(16), (0.58, 0.67, 0.75, 1), 0.78, x_hint=0.84)
        self.gear_value = self._build_label("D", dp(44), (0.98, 0.99, 1, 1), 0.69, x_hint=0.84, bold=True)

        self.bind(pos=self.redraw, size=self.redraw, speed=self._update_values, rpm=self._update_values, gear_label=self._update_values)
        self._update_values()

    def _build_label(self, text, font_size, color, y_hint, x_hint=0.5, bold=False):
        label = Label(
            text=text,
            font_size=font_size,
            color=color,
            bold=bold,
            size_hint=(None, None),
            size=(dp(260), dp(70)),
            pos_hint={"center_x": x_hint, "center_y": y_hint},
            halign="center",
            valign="middle",
        )
        label.bind(size=lambda inst, value: setattr(inst, "text_size", value))
        self.add_widget(label)
        return label

    def _update_values(self, *args):
        self.speed_value.text = str(int(max(self.rpm, 0)))
        self.gear_value.text = self.gear_label
        self.redraw()

    def redraw(self, *args):
        self.canvas.before.clear()
        self.canvas.clear()

        cx, cy = self.center_x, self.center_y
        radius = min(self.width, self.height) * 0.39
        ring_width = dp(18)
        inner_radius = radius * 0.72

        panel_x = self.x + dp(6)
        panel_y = self.y + dp(6)
        panel_w = max(self.width - dp(12), 0)
        panel_h = max(self.height - dp(12), 0)

        speed_ratio = min(max(self.speed / 240.0, 0), 1)
        rpm_ratio = min(max(self.rpm / max(self.max_rpm, 1), 0), 1)
        arc_start = -25
        arc_sweep = 205
        arc_end = arc_start + arc_sweep
        redline_start_ratio = 0.83
        redline_start_angle = arc_start + (arc_sweep * redline_start_ratio)

        with self.canvas.before:
            Color(0.04, 0.06, 0.11, 1)
            RoundedRectangle(pos=(panel_x, panel_y), size=(panel_w, panel_h), radius=[dp(32)])

            Color(0.1, 0.14, 0.21, 0.9)
            RoundedRectangle(
                pos=(panel_x + dp(14), panel_y + dp(14)),
                size=(max(panel_w - dp(28), 0), max(panel_h - dp(28), 0)),
                radius=[dp(28)],
            )

        with self.canvas:
            Color(0.15, 0.18, 0.24, 1)
            Line(circle=(cx, cy, radius, arc_start, arc_end), width=ring_width, cap="round")

            Color(0.22, 0.62, 0.95, 1)
            Line(
                circle=(cx, cy, radius, arc_start, arc_start + arc_sweep * speed_ratio),
                width=ring_width,
                cap="round",
            )

            Color(0.9, 0.29, 0.26, 0.95)
            Line(
                circle=(cx, cy, radius * 0.86, arc_start, arc_start + arc_sweep * rpm_ratio),
                width=dp(10),
                cap="round",
            )

            Color(0.62, 0.16, 0.12, 1)
            Line(circle=(cx, cy, radius, redline_start_angle, arc_end), width=ring_width, cap="round")

            Color(0.06, 0.08, 0.12, 1)
            Ellipse(pos=(cx - inner_radius, cy - inner_radius), size=(inner_radius * 2, inner_radius * 2))

            Color(0.11, 0.14, 0.2, 1)
            Ellipse(
                pos=(cx - inner_radius * 0.78, cy - inner_radius * 0.78),
                size=(inner_radius * 1.56, inner_radius * 1.56),
            )

            self._draw_ticks(cx, cy, radius, arc_start, arc_sweep)

    def _draw_ticks(self, cx, cy, radius, arc_start, arc_sweep):
        for index in range(13):
            ratio = index / 12
            angle = math.radians(arc_start + (arc_sweep * ratio))
            outer_radius = radius + dp(2)
            inner_radius = radius - (dp(26) if index % 2 == 0 else dp(18))

            x1 = cx + inner_radius * math.cos(angle)
            y1 = cy + inner_radius * math.sin(angle)
            x2 = cx + outer_radius * math.cos(angle)
            y2 = cy + outer_radius * math.sin(angle)

            if ratio >= 0.8:
                Color(0.95, 0.42, 0.32, 0.95)
            else:
                Color(0.54, 0.61, 0.7, 0.85)

            Line(points=[x1, y1, x2, y2], width=dp(2.2), cap="round")
