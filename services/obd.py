import re
import threading
import time

from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, NumericProperty, StringProperty

try:
    import obd
except Exception:
    obd = None

try:
    import serial
    from serial.tools import list_ports
except Exception:
    serial = None
    list_ports = None


_MISSING = object()


class OBDService(EventDispatcher):
    connected = BooleanProperty(False)
    status = StringProperty("OBD idle")
    speed = NumericProperty(0)
    rpm = NumericProperty(0)
    port_name = StringProperty("")
    backend = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connection = None
        self.serial_connection = None
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
        self._elm_protocol_id = ""
        self._last_vehicle_probe_time = 0.0

    def connect(self, port=None):
        requested_port = (port or "").strip()
        self.disconnect(update_status=False)
        if requested_port:
            self._schedule_apply(status=f"Connecting to OBD on {requested_port}...", port_name=requested_port)
        else:
            self._schedule_apply(status="Scanning for OBD adapter...")

        if obd is None and serial is None:
            self._schedule_apply(status="OBD unavailable: install python-obd or pyserial")
            return False

        if serial is not None and self._connect_with_elm327(requested_port):
            return True

        if obd is not None and self._connect_with_python_obd(requested_port):
            return True

        if requested_port:
            status = f"OBD adapter not found on {requested_port}"
        else:
            status = "OBD adapter not found on detected ports"
        self._schedule_apply(status=status, connected=False, speed=0, rpm=0, backend="", port_name=requested_port)
        return False

    def autoconnect(self, preferred_port=None):
        return self.connect(preferred_port)

    def disconnect(self, update_status=True):
        self.running = False
        self._elm_protocol_id = ""
        self._last_vehicle_probe_time = 0.0

        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None

        if self.serial_connection:
            try:
                self.serial_connection.close()
            except Exception:
                pass
            self.serial_connection = None

        if self.thread and self.thread.is_alive() and self.thread is not threading.current_thread():
            self.thread.join(timeout=0.6)
        self.thread = None

        if update_status:
            self._schedule_apply(
                connected=False,
                speed=0,
                rpm=0,
                backend="",
                status="OBD disconnected",
            )
        else:
            self._schedule_apply(connected=False, speed=0, rpm=0, backend="")

    def _connect_with_python_obd(self, requested_port):
        last_error = ""
        for candidate in self._candidate_ports(requested_port):
            try:
                connection = obd.OBD(candidate, fast=False, timeout=0.25)
                if connection and connection.is_connected():
                    self.connection = connection
                    self.port_name = candidate
                    self.backend = "python-obd"
                    self.running = True
                    self.thread = threading.Thread(target=self._python_obd_loop, daemon=True)
                    self.thread.start()
                    self._schedule_apply(
                        connected=True,
                        port_name=candidate,
                        backend="python-obd",
                        status=f"OBD connected on {candidate}",
                    )
                    return True
                if connection:
                    connection.close()
            except Exception as exc:
                last_error = str(exc)

        if requested_port and last_error:
            self._schedule_apply(status=f"OBD error on {requested_port}: {last_error}")
        return False

    def _connect_with_elm327(self, requested_port):
        last_error = ""
        for candidate in self._candidate_ports(requested_port):
            for baudrate in (38400, 9600, 115200, 57600):
                try:
                    ser = serial.Serial(candidate, baudrate=baudrate, timeout=0.35, write_timeout=0.35)
                    if self._initialize_elm327(ser):
                        protocol_id = self._prime_vehicle_bus(ser)
                        self.serial_connection = ser
                        self.port_name = candidate
                        self._elm_protocol_id = protocol_id
                        protocol_suffix = f":{protocol_id}" if protocol_id else ""
                        self.backend = f"elm327@{baudrate}{protocol_suffix}"
                        self.running = True
                        self.thread = threading.Thread(target=self._elm327_loop, daemon=True)
                        self.thread.start()
                        status = (
                            f"OBD connected on {candidate}"
                            if protocol_id
                            else f"ELM327 connected on {candidate}, waiting for ECU data..."
                        )
                        self._schedule_apply(
                            connected=True,
                            port_name=candidate,
                            backend=self.backend,
                            status=status,
                        )
                        return True
                    ser.close()
                except Exception as exc:
                    last_error = str(exc)

        if requested_port and last_error:
            self._schedule_apply(status=f"OBD error on {requested_port}: {last_error}")
        return False

    def _python_obd_loop(self):
        while self.running and self.connection:
            try:
                speed_response = self.connection.query(obd.commands.SPEED)
                rpm_response = self.connection.query(obd.commands.RPM)

                speed = 0
                rpm = 0
                if speed_response and not speed_response.is_null():
                    speed = float(speed_response.value.to("km/h").magnitude)
                if rpm_response and not rpm_response.is_null():
                    rpm = float(rpm_response.value.magnitude)

                self._schedule_apply(
                    connected=True,
                    speed=speed,
                    rpm=rpm,
                    status=f"OBD connected on {self.port_name}",
                )
            except Exception as exc:
                self._schedule_apply(status=f"OBD read error: {exc}")
                break
            time.sleep(0.18)

        self._handle_worker_exit()

    def _elm327_loop(self):
        while self.running and self.serial_connection:
            try:
                if not self._elm_protocol_id and time.monotonic() - self._last_vehicle_probe_time >= 2.0:
                    protocol_id = self._prime_vehicle_bus(self.serial_connection)
                    if protocol_id:
                        self._elm_protocol_id = protocol_id
                        self.backend = re.sub(r":.*$", "", self.backend) + f":{protocol_id}"

                rpm = self._read_rpm_elm327()
                speed = self._read_speed_elm327()
                if (rpm is not None or speed is not None) and not self._elm_protocol_id:
                    self._elm_protocol_id = "auto"
                    self.backend = re.sub(r":.*$", "", self.backend) + ":auto"
                if rpm is None and speed is None:
                    self._schedule_apply(
                        connected=True,
                        speed=0,
                        rpm=0,
                        status=(
                            f"ELM327 connected on {self.port_name}, waiting for ECU data..."
                            if not self._elm_protocol_id
                            else f"OBD connected on {self.port_name}, waiting for vehicle data..."
                        ),
                        backend=self.backend,
                    )
                else:
                    self._schedule_apply(
                        connected=True,
                        speed=float(speed or 0),
                        rpm=float(rpm or 0),
                        status=f"OBD connected on {self.port_name}",
                        backend=self.backend,
                    )
            except Exception as exc:
                self._schedule_apply(status=f"OBD read error: {exc}")
                break
            time.sleep(0.15)

        self._handle_worker_exit()

    def _handle_worker_exit(self):
        if not self.running:
            return
        self.running = False
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None
        if self.serial_connection:
            try:
                self.serial_connection.close()
            except Exception:
                pass
            self.serial_connection = None
        self._schedule_apply(connected=False, speed=0, rpm=0, backend="")

    def _initialize_elm327(self, ser):
        commands = [
            ("ATZ", 1.0),
            ("ATI", 0.5),
            ("ATE0", 0.4),
            ("ATL0", 0.4),
            ("ATS0", 0.4),
            ("ATH0", 0.4),
            ("ATAT1", 0.4),
            ("ATST32", 0.4),
            ("ATSP0", 0.6),
        ]

        for command, timeout in commands:
            response = self._send_serial_command(ser, command, timeout=timeout)
            normalized = self._normalize_response(response)
            if not normalized:
                return False
            if command.startswith("AT") and "ERROR" in normalized:
                return False
        return True

    def _prime_vehicle_bus(self, ser):
        self._last_vehicle_probe_time = time.monotonic()
        for protocol_id in ("0", "6", "7", "5", "4", "3"):
            response = self._send_serial_command(ser, f"ATSP{protocol_id}", timeout=0.6)
            normalized = self._normalize_response(response)
            if not normalized or "ERROR" in normalized:
                continue

            warmup = self._send_serial_command(ser, "0100", timeout=1.2)
            normalized = self._normalize_response(warmup)
            if self._has_pid_payload(normalized, "4100"):
                return protocol_id
        return ""

    def _read_rpm_elm327(self):
        normalized = self._query_pid_elm327("010C", timeout=0.7)
        match = re.search(r"410C([0-9A-F]{4})", normalized)
        if not match:
            return None
        raw = match.group(1)
        return ((int(raw[:2], 16) * 256) + int(raw[2:], 16)) / 4

    def _read_speed_elm327(self):
        normalized = self._query_pid_elm327("010D", timeout=0.7)
        match = re.search(r"410D([0-9A-F]{2})", normalized)
        if not match:
            return None
        return int(match.group(1), 16)

    def _query_pid_elm327(self, command, timeout=0.7):
        for _ in range(2):
            response = self._send_serial_command(self.serial_connection, command, timeout=timeout)
            normalized = self._normalize_response(response)
            if self._has_elm_error(normalized):
                continue
            return normalized
        return ""

    def _send_serial_command(self, ser, command, timeout=0.5):
        with self._lock:
            ser.reset_input_buffer()
            ser.write(f"{command}\r".encode("ascii"))
            ser.flush()

            deadline = time.monotonic() + timeout
            response = ""
            while time.monotonic() < deadline:
                chunk = ser.read(ser.in_waiting or 1).decode("ascii", errors="ignore")
                if chunk:
                    response += chunk
                    if ">" in response:
                        break
            return response

    @staticmethod
    def _normalize_response(response):
        text = (response or "").upper().replace("SEARCHING...", "")
        text = text.replace("BUSINIT...", "").replace("BUSINIT:", "")
        text = text.replace("\r", "").replace("\n", "").replace(" ", "").replace(">", "")
        return text

    @staticmethod
    def _has_elm_error(normalized):
        if not normalized:
            return True
        return any(
            marker in normalized
            for marker in (
                "NODATA",
                "UNABLETOCONNECT",
                "ERROR",
                "STOPPED",
                "CANERROR",
                "?",
            )
        )

    @staticmethod
    def _has_pid_payload(normalized, prefix):
        if not normalized:
            return False
        return prefix in normalized and not OBDService._has_elm_error(normalized)

    @staticmethod
    def _candidate_ports(requested_port):
        seen = set()
        ports = []

        def _add(port_name):
            if port_name and port_name not in seen:
                seen.add(port_name)
                ports.append(port_name)

        if requested_port:
            _add(requested_port)

        for preferred in (
            "/dev/rfcomm0",
            "/dev/rfcomm1",
            "/dev/ttyUSB0",
            "/dev/ttyUSB1",
            "/dev/ttyUSB2",
            "/dev/serial0",
        ):
            _add(preferred)

        if list_ports is not None:
            for port in list_ports.comports():
                device = port.device
                if any(token in device for token in ("ttyUSB", "rfcomm", "serial", "usbserial")):
                    _add(device)

        return ports

    def _schedule_apply(
        self,
        *,
        connected=_MISSING,
        status=_MISSING,
        speed=_MISSING,
        rpm=_MISSING,
        port_name=_MISSING,
        backend=_MISSING,
    ):
        Clock.schedule_once(
            lambda dt: self._apply_state(
                connected=connected,
                status=status,
                speed=speed,
                rpm=rpm,
                port_name=port_name,
                backend=backend,
            ),
            0,
        )

    def _apply_state(
        self,
        *,
        connected=_MISSING,
        status=_MISSING,
        speed=_MISSING,
        rpm=_MISSING,
        port_name=_MISSING,
        backend=_MISSING,
    ):
        if connected is not _MISSING:
            self.connected = bool(connected)
        if status is not _MISSING:
            self.status = status
        if speed is not _MISSING:
            self.speed = max(float(speed or 0), 0)
        if rpm is not _MISSING:
            self.rpm = max(float(rpm or 0), 0)
        if port_name is not _MISSING:
            self.port_name = port_name
        if backend is not _MISSING:
            self.backend = backend


obd_service = OBDService()
