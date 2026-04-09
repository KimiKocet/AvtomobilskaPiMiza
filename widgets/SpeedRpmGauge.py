import math

from kivy.graphics import Color, Ellipse, Line
from kivy.metrics import dp
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label


class SpeedRpmGauge(FloatLayout):
    speed = NumericProperty(0)
    rpm = NumericProperty(0)
    max_rpm = NumericProperty(6500)
    redline_rpm = NumericProperty(6000)
    gear_label = StringProperty("D")

    start_angle = 216
    end_angle = -16

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.scale_values = [0, 1, 2, 3, 4, 5, 6]
        self.scale_labels = []
        for value in self.scale_values:
            color = (0.96, 0.27, 0.24, 0.88) if value >= 6 else (0.83, 0.85, 0.89, 0.78)
            label = self._make_label(str(value), dp(24), color, size=(dp(40), dp(28)), italic=True)
            self.scale_labels.append(label)

        self.gear_value = self._make_label("D", dp(64), (0.56, 0.96, 0.47, 0.92), size=(dp(110), dp(84)), bold=True, italic=True)
        self.unit_label = self._make_label("KM/H", dp(28), (0.78, 0.79, 0.81, 0.74), size=(dp(140), dp(38)), bold=True, italic=True)
        self.speed_value = self._make_label("000", dp(96), (1, 1, 1, 1), size=(dp(260), dp(96)), bold=True, italic=True, markup=True)

        self.bind(pos=self.redraw, size=self.redraw, speed=self._update_values, rpm=self.redraw, gear_label=self._update_values)
        self._update_values()

    def _make_label(self, text, font_size, color, size, bold=False, italic=False, markup=False):
        label = Label(
            text=text,
            font_size=font_size,
            color=color,
            bold=bold,
            italic=italic,
            markup=markup,
            size_hint=(None, None),
            size=size,
            halign="center",
            valign="middle",
        )
        label.bind(size=lambda inst, value: setattr(inst, "text_size", value))
        self.add_widget(label)
        return label

    def _update_values(self, *args):
        speed_text = f"{int(max(self.speed, 0)):03d}"
        self.speed_value.text = f"[color=7f8186]{speed_text[0]}[/color][color=ffffff]{speed_text[1:]}[/color]"
        self.gear_value.text = self.gear_label
        self.redraw()

    def redraw(self, *args):
        self.canvas.before.clear()
        self.canvas.clear()

        cx = self.center_x - (self.width * 0.02)
        cy = self.center_y + (self.height * 0.01)
        radius = min(self.width, self.height) * 0.42
        inner_face_radius = radius * 0.34
        rpm_ratio = min(max(self.rpm / max(self.max_rpm, 1), 0), 1)

        with self.canvas.before:
            Color(0.02, 0.03, 0.06, 0.12)
            Ellipse(
                pos=(cx - radius * 1.02, cy - radius * 1.02),
                size=(radius * 2.04, radius * 2.04),
            )

        with self.canvas:
            Color(0.16, 0.18, 0.23, 0.22)
            Ellipse(pos=(cx - radius * 0.98, cy - radius * 0.98), size=(radius * 1.96, radius * 1.96))

            Color(0.82, 0.85, 0.9, 0.24)
            Line(points=self._arc_points(cx, cy, radius, self.start_angle, self.end_angle, 120), width=dp(2.2))

            Color(0.93, 0.95, 0.98, 0.28)
            Line(points=self._arc_points(cx, cy, radius * 0.14, 156, 18, 40), width=dp(1.8))

            Color(0.14, 0.16, 0.21, 0.2)
            Ellipse(
                pos=(cx - inner_face_radius, cy - inner_face_radius),
                size=(inner_face_radius * 2, inner_face_radius * 2),
            )

            Color(0.6, 0.62, 0.66, 0.34)
            Line(points=self._arc_points(cx, cy, inner_face_radius * 1.08, 154, 24, 50), width=dp(1.8))

            Color(0.47, 0.97, 0.49, 0.9)
            Line(circle=(cx, cy, inner_face_radius * 0.68), width=dp(2.1))

            self._draw_ticks(cx, cy, radius)
            self._draw_needle(cx, cy, radius * 0.82, rpm_ratio)

        self._layout_labels(cx, cy, radius, inner_face_radius)

    def _draw_ticks(self, cx, cy, radius):
        total_ticks = 27
        for index in range(total_ticks):
            ratio = index / (total_ticks - 1)
            value = ratio * (self.max_rpm / 1000.0)
            angle = math.radians(self._angle_for_ratio(ratio))
            is_major = index % 4 == 0

            outer = radius * 0.96
            inner = outer - (dp(24) if is_major else dp(11))

            x1 = cx + inner * math.cos(angle)
            y1 = cy + inner * math.sin(angle)
            x2 = cx + outer * math.cos(angle)
            y2 = cy + outer * math.sin(angle)

            if value >= (self.redline_rpm / 1000.0):
                Color(0.97, 0.24, 0.24, 0.84 if is_major else 0.68)
            else:
                Color(0.84, 0.86, 0.9, 0.82 if is_major else 0.48)

            Line(points=[x1, y1, x2, y2], width=dp(2.3) if is_major else dp(1.25), cap="round")

    def _draw_needle(self, cx, cy, length, ratio):
        angle = math.radians(self._angle_for_ratio(ratio))
        tip_x = cx + length * math.cos(angle)
        tip_y = cy + length * math.sin(angle)

        tail_length = length * 0.18
        tail_x = cx - tail_length * math.cos(angle)
        tail_y = cy - tail_length * math.sin(angle)

        Color(0.96, 0.97, 0.99, 0.94)
        Line(points=[tail_x, tail_y, tip_x, tip_y], width=dp(4.4), cap="round")

        Color(0.58, 0.58, 0.6, 0.8)
        Ellipse(pos=(cx - dp(11), cy - dp(11)), size=(dp(22), dp(22)))

        Color(0.17, 0.18, 0.21, 0.92)
        Ellipse(pos=(cx - dp(5), cy - dp(5)), size=(dp(10), dp(10)))

    def _layout_labels(self, cx, cy, radius, inner_face_radius):
        label_radius = radius * 0.79
        max_value = self.max_rpm / 1000.0
        for value, label in zip(self.scale_values, self.scale_labels):
            angle = math.radians(self._angle_for_ratio(value / max_value))
            x = cx + label_radius * math.cos(angle)
            y = cy + label_radius * math.sin(angle)
            label.center = (x, y)

        gear_center = (cx, cy - radius * 0.06)
        self.gear_value.center = gear_center
        self.unit_label.center = (cx + radius * 0.52, cy - radius * 0.18)
        self.speed_value.center = (cx + radius * 0.44, cy - radius * 0.42)

    def _angle_for_ratio(self, ratio):
        return self.start_angle + ((self.end_angle - self.start_angle) * ratio)

    @staticmethod
    def _arc_points(cx, cy, radius, start_angle, end_angle, segments):
        points = []
        for index in range(segments + 1):
            ratio = index / segments
            angle = math.radians(start_angle + ((end_angle - start_angle) * ratio))
            points.extend((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
        return points
