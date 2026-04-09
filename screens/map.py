import os

from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.metrics import dp
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivy_garden.mapview import MapLayer, MapMarker, MapSource, MapView

from services.gps import gps_service
from services.route import route_service


class MapScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.map = None
        self.gps_marker = None
        self.destination_marker = None
        self.route_layer = None
        self._update_event = None
        self.follow_mode = True
        self.has_centered_once = False

        root = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))

        header = MDCard(
            orientation="vertical",
            padding=dp(18),
            spacing=dp(12),
            radius=[dp(26)],
            elevation=0,
            md_bg_color=(0.08, 0.11, 0.16, 0.98),
            size_hint_y=None,
            height=dp(146),
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
        title_row.add_widget(self._make_action_button("Demo Route", self.load_demo_route))
        title_row.add_widget(self._make_action_button("Clear", self.clear_route))
        title_row.add_widget(self._make_action_button("Center", self.recenter_map))

        self.status_label = MDLabel(
            text="Waiting for GPS...",
            theme_text_color="Custom",
            text_color=(0.55, 0.8, 0.99, 1),
        )
        self.nav_label = MDLabel(
            text="No route selected",
            theme_text_color="Custom",
            text_color=(0.89, 0.91, 0.95, 1),
        )

        header.add_widget(title_row)
        header.add_widget(self.status_label)
        header.add_widget(self.nav_label)

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

        route_service.bind(route_points=self._on_route_points)

    def on_enter(self):
        if not self.map:
            self._build_map()
        if not self._update_event:
            self._update_event = Clock.schedule_interval(self.refresh_map, 0.25)

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
        self.route_layer = RouteLineLayer()
        self.map.add_layer(self.route_layer, mode="window")

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

        self.status_label.text = gps_service.status

        if gps_service.has_fix:
            self.gps_marker.lat = gps_service.lat
            self.gps_marker.lon = gps_service.lon
            self.gps_marker.angle = gps_service.heading

            if self.follow_mode or not self.has_centered_once:
                self.map.center_on(gps_service.lat, gps_service.lon)
                self.has_centered_once = True

        self._refresh_route_ui()

    def _refresh_route_ui(self):
        if route_service.active:
            self.nav_label.text = f"{route_service.next_instruction}   {route_service.distance_to_next_m} m"
        elif route_service.next_instruction == "Arrived":
            self.nav_label.text = "Arrived"
        else:
            self.nav_label.text = "No route selected"

        if self.route_layer:
            self.route_layer.set_points(route_service.route_points)

        if route_service.route_points:
            dest_lat, dest_lon = route_service.route_points[-1]
            if not self.destination_marker:
                self.destination_marker = MapMarker(lat=dest_lat, lon=dest_lon, anchor_x=0.5, anchor_y=0.0)
                self.map.add_widget(self.destination_marker)
            else:
                self.destination_marker.lat = dest_lat
                self.destination_marker.lon = dest_lon
        elif self.destination_marker:
            self.map.remove_widget(self.destination_marker)
            self.destination_marker = None

    def load_demo_route(self, *_):
        origin_lat = gps_service.lat if gps_service.has_fix else self.map.lat
        origin_lon = gps_service.lon if gps_service.has_fix else self.map.lon
        route_service.load_demo_route(origin_lat, origin_lon)
        self.follow_mode = True
        self._refresh_route_ui()

    def clear_route(self, *_):
        route_service.clear()
        self._refresh_route_ui()

    def recenter_map(self, *_):
        self.follow_mode = True
        if gps_service.has_fix:
            self.map.center_on(gps_service.lat, gps_service.lon)
        elif self.map:
            self.map.center_on(self.map.lat, self.map.lon)

    def _make_action_button(self, text, callback):
        button = Button(
            text=text,
            size_hint=(None, None),
            size=(dp(104), dp(34)),
            background_normal="",
            background_color=(0.17, 0.4, 0.64, 1),
            color=(1, 1, 1, 1),
        )
        button.bind(on_release=callback)
        return button

    def _on_route_points(self, *_):
        if self.route_layer:
            self.route_layer.set_points(route_service.route_points)


class RouteLineLayer(MapLayer):
    route_points = ListProperty([])

    def set_points(self, points):
        self.route_points = list(points)
        self.reposition()

    def reposition(self):
        self.canvas.clear()

        mapview = self.parent
        if not mapview or len(self.route_points) < 2:
            return

        route_pixels = []
        for lat, lon in self.route_points:
            x, y = mapview.get_window_xy_from(lat, lon, mapview.zoom)
            route_pixels.extend((x, y))

        with self.canvas:
            Color(0.03, 0.07, 0.11, 0.85)
            Line(points=route_pixels, width=dp(8), joint="round", cap="round")
            Color(0.22, 0.72, 0.99, 0.95)
            Line(points=route_pixels, width=dp(4.8), joint="round", cap="round")
