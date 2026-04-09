import threading
import time

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
    has_fix = BooleanProperty(False)
    connected = BooleanProperty(False)
    status = StringProperty("GPS idle")
    port_name = StringProperty("/dev/ttyACM0")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.running = False
        self.ser = None
        self.thread = None

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
            self.status = f"Searching for satellites on {port}..."
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

    def _apply_fix(self, lat, lon, satellites):
        self.lat = lat
        self.lon = lon
        self.satellites = satellites
        self.has_fix = True
        self.connected = True
        self.status = f"GPS fixed ({satellites} sats)"
        route_service.update_position(lat, lon)

    def _apply_motion(self, lat, lon, speed, heading):
        self.lat = lat
        self.lon = lon
        self.speed_kmh = speed
        self.heading = heading
        self.has_fix = True
        self.connected = True
        self.status = f"GPS fixed ({self.satellites} sats)"
        route_service.update_position(lat, lon)

    def _apply_speed_heading(self, speed, heading):
        self.speed_kmh = speed
        self.heading = heading

    def _apply_no_fix(self, satellites):
        self.has_fix = False
        self.satellites = satellites
        self.speed_kmh = 0
        self.status = f"Searching for satellites ({satellites} visible)"

    def _apply_error(self, message):
        self.has_fix = False
        self.connected = False
        self.speed_kmh = 0
        self.status = f"GPS read error: {message}"


gps_service = GPSService()
