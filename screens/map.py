import os
import time
from threading import Thread

import pynmea2
import serial
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivy_garden.mapview import MapMarker, MapSource, MapView


class MapScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_lat = 46.0569
        self.current_lon = 14.5058
        self.gps_heading = 0
        self.gps_thread_running = False
        self.ser = None
        self.map = None
        self.gps_marker = None
        self._marker_event = None

        root = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))
        header = MDCard(
            orientation="vertical",
            padding=dp(18),
            radius=[dp(26)],
            elevation=0,
            md_bg_color=(0.08, 0.11, 0.16, 0.98),
            size_hint_y=None,
            height=dp(86),
        )
        header.add_widget(
            MDLabel(
                text="Navigation",
                theme_text_color="Custom",
                text_color=(0.98, 0.99, 1, 1),
                bold=True,
                font_style="H5",
            )
        )
        header.add_widget(
            MDLabel(
                text="Centered car marker with live GPS updates when the receiver is connected.",
                theme_text_color="Custom",
                text_color=(0.61, 0.7, 0.79, 1),
            )
        )

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
                lat=self.current_lat,
                lon=self.current_lon,
                map_source="osm",
                cache_dir=cache_folder,
            )
            self.gps_marker = MapMarker(
                lat=self.current_lat,
                lon=self.current_lon,
                source="assets/car_icon.png",
                anchor_x=0.5,
                anchor_y=0.5,
            )
            self.map.add_widget(self.gps_marker)
            self.map_card.add_widget(self.map)

        if not self.gps_thread_running:
            try:
                self.ser = serial.Serial("/dev/ttyACM0", 9600, timeout=1)
                self.gps_thread_running = True
                Thread(target=self.read_gps, daemon=True).start()
            except Exception as exc:
                print("GPS serial error:", exc)

        if not self._marker_event:
            self._marker_event = Clock.schedule_interval(self.update_marker, 1)

    def read_gps(self):
        while self.gps_thread_running:
            try:
                line = self.ser.readline().decode("ascii", errors="replace").strip()
                if line.startswith("$GPGGA"):
                    msg = pynmea2.parse(line)
                    if msg.gps_qual > 0:
                        self.current_lat = msg.latitude
                        self.current_lon = msg.longitude
                elif line.startswith("$GPVTG"):
                    msg = pynmea2.parse(line)
                    self.gps_heading = float(msg.true_track or 0)
            except Exception as exc:
                print("GPS read error:", exc)
            time.sleep(0.1)

    def update_marker(self, dt):
        if not self.gps_marker or not self.map:
            return
        self.gps_marker.lat = self.current_lat
        self.gps_marker.lon = self.current_lon
        self.gps_marker.angle = self.gps_heading
        self.map.center_on(self.current_lat, self.current_lon)

    def on_leave(self):
        self.gps_thread_running = False
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
        if self._marker_event:
            self._marker_event.cancel()
            self._marker_event = None
