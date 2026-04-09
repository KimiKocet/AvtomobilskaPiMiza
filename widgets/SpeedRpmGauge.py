import math

from kivy.graphics import Color, Ellipse, Line
from kivy.metrics import dp
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label


class SpeedRpmGauge(FloatLayout):
    speed = NumericProperty(0)
    rpm = NumericProperty(0)
    max_rpm = NumericProperty(8000)
    gear_label = StringProperty("1")

    start_angle = 220
    sweep_angle = -260

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.center_top = self._make_label("GEAR 1", dp(20), (0.88, 0.9, 0.95, 1), size=(dp(220), dp(36)))
        self.center_value = self._make_label("0.0", dp(108), (1, 1, 1, 1), bold=True, size=(dp(260), dp(120)))
        self.center_bottom = self._make_label("RPM x1000", dp(18), (0.78, 0.81, 0.87, 1), size=(dp(220), dp(34)))

        self.scale_labels = []
        for value in range(9):
            label = self._make_label(str(value), dp(28), (0.94, 0.96, 0.98, 1), size=(dp(44), dp(34)))
            self.scale_labels.append(label)

        self.bind(pos=self.redraw, size=self.redraw, rpm=self._update_values, gear_label=self._update_values)
        self._update_values()

    def _make_label(self, text, font_size, color, size, bold=False):
        label = Label(
            text=text,
            font_size=font_size,
            color=color,
            bold=bold,
            size_hint=(None, None),
            size=size,
            halign="center",
            valign="middle",
        )
        label.bind(size=lambda inst, value: setattr(inst, "text_size", value))
        self.add_widget(label)
        return label

    def _update_values(self, *args):
        self.center_top.text = f"GEAR {self.gear_label}"
        self.center_value.text = f"{max(self.rpm, 0) / 1000:.1f}"
        self.redraw()

    def redraw(self, *args):
        self.canvas.before.clear()
        self.canvas.clear()

        cx, cy = self.center_x, self.center_y
        outer_radius = min(self.width, self.height) * 0.45
        face_radius = outer_radius * 0.97
        inner_radius = outer_radius * 0.56
        tick_outer = outer_radius * 0.89
        label_radius = outer_radius * 0.73
        rpm_value = min(max(self.rpm / 1000.0, 0), self.max_rpm / 1000.0)

        with self.canvas.before:
            Color(0.02, 0.03, 0.05, 0.7)
            Ellipse(
                pos=(cx - outer_radius * 1.04, cy - outer_radius * 1.04),
                size=(outer_radius * 2.08, outer_radius * 2.08),
            )

        with self.canvas:
            Color(0.12, 0.15, 0.21, 1)
            Ellipse(pos=(cx - face_radius, cy - face_radius), size=(face_radius * 2, face_radius * 2))

            Color(0.21, 0.57, 0.96, 0.95)
            Line(circle=(cx, cy, outer_radius), width=dp(2))

            Color(0.94, 0.25, 0.2, 0.18)
            Line(points=self._arc_points(cx, cy, outer_radius * 0.78, 135, -95, 56), width=dp(34), cap="round")

            Color(0.08, 0.1, 0.15, 1)
            Ellipse(pos=(cx - inner_radius, cy - inner_radius), size=(inner_radius * 2, inner_radius * 2))

            Color(0.21, 0.57, 0.96, 0.9)
            Line(circle=(cx, cy, inner_radius * 1.02), width=dp(2))

            self._draw_ticks(cx, cy, tick_outer)
            self._draw_needle(cx, cy, outer_radius * 0.82, outer_radius * 0.14, rpm_value)

        self._layout_labels(cx, cy, label_radius, inner_radius)

    def _layout_labels(self, cx, cy, label_radius, inner_radius):
        self.center_top.center = (cx, cy + inner_radius * 0.46)
        self.center_value.center = (cx, cy + inner_radius * 0.02)
        self.center_bottom.center = (cx, cy - inner_radius * 0.67)

        for value, label in enumerate(self.scale_labels):
            angle = math.radians(self._value_to_angle(value))
            x = cx + label_radius * math.cos(angle)
            y = cy + label_radius * math.sin(angle)
            label.center = (x, y)

    def _draw_ticks(self, cx, cy, tick_outer):
        total_ticks = 41
        for index in range(total_ticks):
            ratio = index / (total_ticks - 1)
            value = ratio * 8.0
            angle = math.radians(self._value_to_angle(value))

            is_major = index % 5 == 0
            outer = tick_outer
            inner = tick_outer - (dp(26) if is_major else dp(12))

            x1 = cx + inner * math.cos(angle)
            y1 = cy + inner * math.sin(angle)
            x2 = cx + outer * math.cos(angle)
            y2 = cy + outer * math.sin(angle)

            if value <= 1.2 or value >= 7.0:
                Color(0.96, 0.29, 0.24, 0.95 if is_major else 0.85)
            else:
                Color(0.96, 0.97, 0.99, 0.95 if is_major else 0.7)

            Line(points=[x1, y1, x2, y2], width=dp(2.2) if is_major else dp(1.25), cap="round")

    def _draw_needle(self, cx, cy, length, tail_length, rpm_value):
        angle = math.radians(self._value_to_angle(rpm_value))

        tip_x = cx + length * math.cos(angle)
        tip_y = cy + length * math.sin(angle)
        tail_x = cx - tail_length * math.cos(angle)
        tail_y = cy - tail_length * math.sin(angle)

        Color(1, 0.73, 0.34, 0.95)
        Line(points=[tail_x, tail_y, cx, cy], width=dp(4.5), cap="round")

        Color(1, 1, 1, 1)
        Line(points=[cx, cy, tip_x, tip_y], width=dp(5), cap="round")

        Color(0.98, 0.62, 0.25, 1)
        Ellipse(pos=(cx - dp(11), cy - dp(11)), size=(dp(22), dp(22)))

        Color(0.08, 0.1, 0.15, 1)
        Ellipse(pos=(cx - dp(6), cy - dp(6)), size=(dp(12), dp(12)))

    def _value_to_angle(self, value):
        clamped = min(max(value / 8.0, 0), 1)
        return self.start_angle + (self.sweep_angle * clamped)

    @staticmethod
    def _arc_points(cx, cy, radius, start_deg, sweep_deg, segments):
        points = []
        for index in range(segments + 1):
            ratio = index / segments
            angle = math.radians(start_deg + (sweep_deg * ratio))
            points.extend((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
        return points
