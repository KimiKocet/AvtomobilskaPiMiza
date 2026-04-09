import os

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivy_garden.mapview import MapMarker, MapSource, MapView

from services.gps import gps_service


class MapScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.map = None
        self.gps_marker = None
        self._update_event = None
        self.follow_mode = True
        self.has_centered_once = False
        self.min_zoom = 8
        self.max_zoom = 18

        root = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))

        header = MDCard(
            orientation="vertical",
            padding=dp(18),
            spacing=dp(10),
            radius=[dp(26)],
            elevation=0,
            md_bg_color=(0.08, 0.11, 0.16, 0.98),
            size_hint_y=None,
            height=dp(112),
        )

        title_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(36), spacing=dp(10))
        title_row.add_widget(
            MDLabel(
                text="Navigation",
                theme_text_color="Custom",
                text_color=(0.98, 0.99, 1, 1),
                bold=True,
                font_style="H5",
            )
        )
        title_row.add_widget(self._make_zoom_button("+", self.zoom_in))
        title_row.add_widget(self._make_zoom_button("-", self.zoom_out))

        self.status_label = MDLabel(
            text="Waiting for GPS...",
            theme_text_color="Custom",
            text_color=(0.55, 0.8, 0.99, 1),
        )

        header.add_widget(title_row)
        header.add_widget(self.status_label)

        self.map_card = MDCard(
            orientation="vertical",
            padding=dp(10),
            radius=[dp(30)],
            elevation=0,
            md_bg_color=(0.05, 0.08, 0.12, 1),
        )

        root.add_widget(header)
        root.add_widget(self.map_card)
        self.add_widget(root)

    def on_enter(self):
        if not self.map:
            self._build_map()
        if not self._update_event:
            self._update_event = Clock.schedule_interval(self.refresh_map, 0.2)

    def on_leave(self):
        if self._update_event:
            self._update_event.cancel()
            self._update_event = None

    def _build_map(self):
        cache_folder = os.path.join(os.path.expanduser("~"), ".map_cache")
        os.makedirs(cache_folder, exist_ok=True)

        MapSource(
            url="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
            cache_key="osm",
            tile_size=256,
            image_ext="png",
            attribution="© OpenStreetMap contributors",
            cache_dir=cache_folder,
        )

        self.map = MapView(
            zoom=14,
            lat=gps_service.lat,
            lon=gps_service.lon,
            map_source="osm",
            cache_dir=cache_folder,
        )
        self.map._scatter.do_rotation = True

        self.gps_marker = MapMarker(
            lat=gps_service.lat,
            lon=gps_service.lon,
            source="assets/car_icon.png",
            anchor_x=0.5,
            anchor_y=0.5,
        )
        self.map.add_widget(self.gps_marker)
        self.map_card.add_widget(self.map)

    def refresh_map(self, dt):
        if not self.map or not self.gps_marker:
            return

        self.status_label.text = f"{gps_service.status}   Zoom {int(self.map.zoom)}"

        if gps_service.has_fix:
            self.gps_marker.lat = gps_service.lat
            self.gps_marker.lon = gps_service.lon
            self.gps_marker.angle = 0

            if self.follow_mode or not self.has_centered_once:
                self.map.center_on(gps_service.lat, gps_service.lon)
                self.has_centered_once = True

            self.map._scatter.rotation = -gps_service.heading
        else:
            self.map._scatter.rotation = 0

    def zoom_in(self, *_):
        self._set_zoom(int(self.map.zoom) + 1)

    def zoom_out(self, *_):
        self._set_zoom(int(self.map.zoom) - 1)

    def _set_zoom(self, zoom_value):
        if not self.map:
            return
        zoom_value = max(self.min_zoom, min(self.max_zoom, zoom_value))
        self.map.set_zoom_at(zoom_value, self.map.center_x, self.map.center_y)

    def _make_zoom_button(self, text, callback):
        button = Button(
            text=text,
            size_hint=(None, None),
            size=(dp(46), dp(34)),
            background_normal="",
            background_color=(0.17, 0.4, 0.64, 1),
            color=(1, 1, 1, 1),
        )
        button.bind(on_release=callback)
        return button
