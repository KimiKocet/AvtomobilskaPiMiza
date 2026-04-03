from pydbus import SystemBus, SessionBus
from gi.repository import GLib
import threading


# ---------------------------------------------------------
#  BLUETOOTH SERVICE
# ---------------------------------------------------------
class BluetoothService:

    def __init__(self):
        self.sys_bus = SystemBus()
        self.sess_bus = SessionBus()
        self.adapter = None

        self._init_adapter()

        # Start GLib loop in background
        self.loop = GLib.MainLoop()
        threading.Thread(target=self.loop.run, daemon=True).start()

    # -----------------------------------------------------
    #  INIT ADAPTER
    # -----------------------------------------------------
    def _init_adapter(self):
        mngr = self.sys_bus.get("org.bluez", "/")
        objects = mngr.GetManagedObjects()

        for path, interfaces in objects.items():
            if "org.bluez.Adapter1" in interfaces:
                self.adapter = self.sys_bus.get("org.bluez", path)

                try:
                    self.adapter.Set(
                        "org.bluez.Adapter1",
                        "Powered",
                        GLib.Variant("b", True)
                    )
                except Exception as e:
                    print("Failed to power adapter:", e)

                break


    # -----------------------------------------------------
    #  SCANNING
    # -----------------------------------------------------
    def start_scan(self):
        if self.adapter:
            try:
                self.adapter.StartDiscovery()
            except Exception as e:
                print("Start scan error:", e)

    def stop_scan(self):
        if self.adapter:
            try:
                self.adapter.StopDiscovery()
            except Exception as e:
                print("Stop scan error:", e)

    # -----------------------------------------------------
    #  LIST DEVICES
    # -----------------------------------------------------
    def get_devices(self):
        devices = []
        mngr = self.sys_bus.get("org.bluez", "/")
        objects = mngr.GetManagedObjects()

        for path, interfaces in objects.items():
            if "org.bluez.Device1" not in interfaces:
                continue

            dev = interfaces["org.bluez.Device1"]

            alias = dev.get("Alias")
            name = dev.get("Name")
            address = dev.get("Address")
            connected = dev.get("Connected", False)
            paired = dev.get("Paired", False)
            rssi = dev.get("RSSI")

            if not alias and not name:
                continue

            if not connected and not paired and rssi is None:
                continue

            devices.append({
                "path": path,
                "name": alias or name,
                "address": address,
                "connected": connected,
                "paired": paired,
            })

        devices.sort(key=lambda d: (
            not d["connected"],
            not d["paired"],
            d["name"].lower()
        ))

        return devices

    # -----------------------------------------------------
    #  CONNECT / DISCONNECT
    # -----------------------------------------------------
    def connect(self, device_path):
        try:
            device = self.sys_bus.get("org.bluez", device_path)

            if not device.Paired:
                device.Pair()

            device.Connect()
        except Exception as e:
            print("Connect error:", e)

    def disconnect(self, device_path):
        try:
            device = self.sys_bus.get("org.bluez", device_path)
            device.Disconnect()
        except Exception as e:
            print("Disconnect error:", e)

    # -----------------------------------------------------
    #  MEDIA DETECTION
    # -----------------------------------------------------
    def get_active_media(self):
        # Spotify MPRIS
        try:
            self.sess_bus.get(
                "org.mpris.MediaPlayer2.spotify",
                "/org/mpris/MediaPlayer2"
            )
            return "spotify"
        except:
            pass

        # Bluetooth Media
        mngr = self.sys_bus.get("org.bluez", "/")
        objects = mngr.GetManagedObjects()

        for path, interfaces in objects.items():
            if "org.bluez.MediaPlayer1" in interfaces:
                return "bluetooth"

        return None

    # -----------------------------------------------------
    #  DISCOVERABLE
    # -----------------------------------------------------
    def set_discoverable(self, enabled: bool):
        if not self.adapter:
            return False

        try:
            self.adapter.Set(
                "org.bluez.Adapter1",
                "Discoverable",
                GLib.Variant("b", enabled)
            )
            return True
        except Exception as e:
            print("Discoverable error:", e)
            return False

    def is_discoverable(self):
        if not self.adapter:
            return False

        try:
            return bool(self.adapter.Get("org.bluez.Adapter1", "Discoverable"))
        except:
            return False


# ---------------------------------------------------------
#  SINGLETON INSTANCE
# ---------------------------------------------------------
bluetooth_service = BluetoothService()
