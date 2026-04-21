import threading
import time
import urllib.parse
import urllib.request
import json
import math

from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, NumericProperty, StringProperty

from services.route import route_service

try:
    import pynmea2
except Exception:
    pynmea2 = None

try:
    import serial
except Exception:
    serial = None


class GPSService(EventDispatcher):
    lat = NumericProperty(46.0569)
    lon = NumericProperty(14.5058)
    speed_kmh = NumericProperty(0)
    heading = NumericProperty(0)
    satellites = NumericProperty(0)
    satellites_in_view = NumericProperty(0)
    has_fix = BooleanProperty(False)
    connected = BooleanProperty(False)
    status = StringProperty("GPS idle")
    port_name = StringProperty("/dev/ttyACM0")
    road_name = StringProperty("")
    town_name = StringProperty("")
    location_label = StringProperty("Waiting for GPS...")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.running = False
        self.ser = None
        self.thread = None
        self._lookup_in_flight = False
        self._last_lookup_time = 0.0
        self._last_lookup_coords = None

    def start(self, port="/dev/ttyACM0", baudrate=9600):
        if self.running:
            return True

        self.port_name = port

        if serial is None or pynmea2 is None:
            self.status = "GPS unavailable: install pyserial and pynmea2"
            return False

        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.running = True
            self.connected = True
            self.status = "GPS connected, waiting for fix..."
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            return True
        except Exception as exc:
            self.connected = False
            self.status = f"GPS device unavailable on {port}: {exc}"
            return False

    def stop(self):
        self.running = False
        self.connected = False
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None

    def _read_loop(self):
        while self.running:
            try:
                raw = self.ser.readline()
                if not raw:
                    continue
                line = raw.decode("ascii", errors="replace").strip()
                if not line:
                    continue

                if line.startswith(("$GPGGA", "$GNGGA")):
                    self._handle_gga(line)
                elif line.startswith(("$GPRMC", "$GNRMC")):
                    self._handle_rmc(line)
                elif line.startswith(("$GPVTG", "$GNVTG")):
                    self._handle_vtg(line)
                elif line.startswith(("$GPGSV", "$GNGSV")):
                    self._handle_gsv(line)
            except Exception as exc:
                Clock.schedule_once(lambda dt, message=str(exc): self._apply_error(message))
                time.sleep(0.2)

    def _handle_gga(self, line):
        msg = pynmea2.parse(line)
        quality = int(msg.gps_qual or 0)
        satellites = int(msg.num_sats or 0)
        lat = float(msg.latitude or 0)
        lon = float(msg.longitude or 0)

        if quality > 0:
            Clock.schedule_once(
                lambda dt, lat=lat, lon=lon, satellites=satellites: self._apply_fix(lat, lon, satellites)
            )
        else:
            Clock.schedule_once(lambda dt, satellites=satellites: self._apply_no_fix(satellites))

    def _handle_rmc(self, line):
        msg = pynmea2.parse(line)
        if msg.status != "A":
            Clock.schedule_once(lambda dt: self._apply_no_fix(self.satellites))
            return

        lat = float(msg.latitude or 0)
        lon = float(msg.longitude or 0)
        speed = float(msg.spd_over_grnd or 0) * 1.852
        heading = float(msg.true_course or 0) if msg.true_course else 0
        Clock.schedule_once(
            lambda dt, lat=lat, lon=lon, speed=speed, heading=heading: self._apply_motion(lat, lon, speed, heading)
        )

    def _handle_vtg(self, line):
        msg = pynmea2.parse(line)
        speed = float(msg.spd_over_grnd_kmph or 0) if msg.spd_over_grnd_kmph else 0
        heading = float(msg.true_track or 0) if msg.true_track else 0
        Clock.schedule_once(lambda dt, speed=speed, heading=heading: self._apply_speed_heading(speed, heading))

    def _handle_gsv(self, line):
        msg = pynmea2.parse(line)
        satellites_in_view = int(msg.num_sv_in_view or 0)
        Clock.schedule_once(lambda dt, total=satellites_in_view: self._apply_satellites_in_view(total))

    def _apply_fix(self, lat, lon, satellites):
        self.lat = lat
        self.lon = lon
        self.satellites = satellites
        self.has_fix = True
        self.connected = True
        self.status = self._format_fix_status()
        route_service.update_position(lat, lon)
        self._maybe_reverse_lookup(lat, lon)

    def _apply_motion(self, lat, lon, speed, heading):
        self.lat = lat
        self.lon = lon
        self.speed_kmh = speed
        self.heading = heading
        self.has_fix = True
        self.connected = True
        self.status = self._format_fix_status()
        route_service.update_position(lat, lon)
        self._maybe_reverse_lookup(lat, lon)

    def _apply_speed_heading(self, speed, heading):
        self.speed_kmh = speed
        self.heading = heading

    def _apply_satellites_in_view(self, satellites_in_view):
        self.satellites_in_view = satellites_in_view
        if not self.has_fix:
            self.status = self._format_search_status()

    def _apply_no_fix(self, satellites):
        self.has_fix = False
        self.satellites = satellites
        self.speed_kmh = 0
        self.status = self._format_search_status()
        if not self.road_name and not self.town_name:
            self.location_label = "Waiting for GPS..."

    def _apply_error(self, message):
        self.has_fix = False
        self.connected = False
        self.speed_kmh = 0
        self.satellites = 0
        self.satellites_in_view = 0
        self.status = f"GPS read error: {message}"

    def _format_fix_status(self):
        if self.satellites_in_view:
            return f"GPS fixed ({self.satellites}/{self.satellites_in_view} sats)"
        if self.satellites:
            return f"GPS fixed ({self.satellites} sats)"
        return "GPS fixed"

    def _format_search_status(self):
        if self.satellites_in_view:
            return f"GPS connected, no fix yet (0/{self.satellites_in_view} sats)"
        return "GPS connected, waiting for satellites..."

    def _maybe_reverse_lookup(self, lat, lon):
        now = time.monotonic()
        if self._lookup_in_flight:
            return
        if self._last_lookup_coords and self._distance_m(lat, lon, *self._last_lookup_coords) < 80:
            return
        if now - self._last_lookup_time < 12:
            return

        self._lookup_in_flight = True
        self._last_lookup_time = now
        self._last_lookup_coords = (lat, lon)
        threading.Thread(target=self._reverse_lookup_worker, args=(lat, lon), daemon=True).start()

    def _reverse_lookup_worker(self, lat, lon):
        try:
            params = urllib.parse.urlencode(
                {
                    "format": "jsonv2",
                    "lat": lat,
                    "lon": lon,
                    "addressdetails": 1,
                    "zoom": 17,
                    "layer": "address",
                    "accept-language": "sl,en",
                }
            )
            request = urllib.request.Request(
                f"https://nominatim.openstreetmap.org/reverse?{params}",
                headers={"User-Agent": "DriveMediaTelemetry/1.0"},
            )
            with urllib.request.urlopen(request, timeout=4) as response:
                payload = json.loads(response.read().decode("utf-8"))

            address = payload.get("address", {})
            road = (
                address.get("road")
                or address.get("pedestrian")
                or address.get("cycleway")
                or address.get("footway")
                or address.get("path")
                or ""
            )
            town = (
                address.get("city")
                or address.get("town")
                or address.get("village")
                or address.get("municipality")
                or address.get("suburb")
                or address.get("hamlet")
                or ""
            )
            Clock.schedule_once(lambda dt, road=road, town=town: self._apply_location(road, town))
        except Exception:
            pass
        finally:
            self._lookup_in_flight = False

    def _apply_location(self, road, town):
        self.road_name = road
        self.town_name = town
        if road and town:
            self.location_label = f"{road}, {town}"
        elif road:
            self.location_label = road
        elif town:
            self.location_label = town
        elif not self.has_fix:
            self.location_label = "Waiting for GPS..."

    @staticmethod
    def _distance_m(lat1, lon1, lat2, lon2):
        earth_radius = 6371000
        p1 = math.radians(lat1)
        p2 = math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)

        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * earth_radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


gps_service = GPSService()
