from kivy.uix.screenmanager import Screen
from kivy_garden.mapview import MapView, MapMarker, MapSource
from kivy.clock import Clock
from threading import Thread
import serial
import pynmea2
import time
import os

class MapScreen(Screen):
    def on_enter(self):
        self.current_lat = 46.0569
        self.current_lon = 14.5058

        # Tile cache folder
        cache_folder = os.path.join(os.path.expanduser("~"), ".map_cache")
        os.makedirs(cache_folder, exist_ok=True)

        osm_source = MapSource(
            url="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
            cache_key="osm",
            tile_size=256,
            image_ext="png",
            attribution="© OpenStreetMap contributors",
            cache_dir=cache_folder
        )

        self.map = MapView(zoom=14, lat=self.current_lat, lon=self.current_lon, map_source="osm", cache_dir="/home/admin/.cache")
        self.add_widget(self.map)

        # Car marker
        self.gps_marker = MapMarker(lat=self.current_lat, lon=self.current_lon, source="assets/car_icon.png", anchor_x=0.5, anchor_y=0.5)
        self.map.add_widget(self.gps_marker)


        # Start GPS thread
        self.gps_thread_running = True
        self.ser = serial.Serial("/dev/ttyACM0", 9600, timeout=1)
        Thread(target=self.read_gps, daemon=True).start()

        # Update marker every second
        Clock.schedule_interval(self.update_marker, 1)

    def read_gps(self):
        while self.gps_thread_running:
            try:
                line = self.ser.readline().decode('ascii', errors='replace').strip()
                if line.startswith('$GPGGA'):
                    msg = pynmea2.parse(line)
                    if msg.gps_qual > 0:
                        self.current_lat = msg.latitude
                        self.current_lon = msg.longitude
                        # Clock.schedule_once(lambda dt: self.path_layer.add_point(self.current_lat, self.current_lon))
                elif line.startswith('$GPVTG'):
                    msg = pynmea2.parse(line)
                    try:
                        self.gps_heading = float(msg.true_track)
                    except:
                        self.gps_heading = 0
            except Exception as e:
                print("GPS read error:", e)
            time.sleep(0.1)

    def update_marker(self, dt):
        self.gps_marker.lat = self.current_lat
        self.gps_marker.lon = self.current_lon
        if hasattr(self, 'gps_heading'):
            self.gps_marker.angle = self.gps_heading
        self.map.center_on(self.current_lat, self.current_lon)

    def on_leave(self):
        self.gps_thread_running = False
        self.ser.close()