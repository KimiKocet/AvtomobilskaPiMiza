# settings_screen.py
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock

from services.bluetooth import bluetooth_service
from services.obd import OBDService


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Dialog for pairing overlay
        self.pairing_dialog = None

        # -------- MAIN LAYOUT --------
        main_layout = BoxLayout(
            orientation='vertical',
            padding=20,
            spacing=20
        )

        # -------- ROW LAYOUT (Bluetooth | OBD) --------
        row_layout = BoxLayout(
            orientation='horizontal',
            spacing=40
        )

        # -------------------------
        # BLUETOOTH PANEL
        # -------------------------
        bt_layout = BoxLayout(
            orientation='vertical',
            spacing=15,
            size_hint=(0.5, 1)
        )

        bt_title = Label(
            text="Bluetooth",
            font_size=28,
            size_hint_y=None,
            height=50
        )

        # Device list
        self.device_list = GridLayout(
            cols=1,
            spacing=10,
            size_hint_y=None
        )
        self.device_list.bind(minimum_height=self.device_list.setter('height'))

        scroll = ScrollView()
        scroll.add_widget(self.device_list)

        # Buttons row (Discoverable + Refresh)
        button_row = BoxLayout(
            orientation='horizontal',
            spacing=10,
            size_hint_y=None,
            height=50
        )

        self.discoverable_button = Button(text="Make Discoverable")
        self.discoverable_button.bind(on_release=self.toggle_discoverable)

        self.refresh_button = Button(text="Refresh")
        self.refresh_button.bind(on_release=self.manual_refresh)

        button_row.add_widget(self.discoverable_button)
        button_row.add_widget(self.refresh_button)

        bt_layout.add_widget(bt_title)
        bt_layout.add_widget(button_row)
        bt_layout.add_widget(scroll)

        # Start scanning
        bluetooth_service.start_scan()

        if bluetooth_service.is_discoverable():
            self.discoverable_button.text = "Discoverable: ON"

        # Auto-refresh every 3 seconds
        Clock.schedule_interval(self.refresh_devices, 3)

        # -------------------------
        # OBD PANEL
        # -------------------------
        obd_layout = BoxLayout(
            orientation='vertical',
            spacing=10,
            size_hint=(0.5, 1)
        )

        self.obd_status = Label(text="OBD: Disconnected")
        self.port_input = TextInput(text="/dev/ttyUSB0", multiline=False)

        self.obd_button = Button(text="Connect OBD", on_release=self.toggle_obd)

        obd_layout.add_widget(self.obd_status)
        obd_layout.add_widget(self.port_input)
        obd_layout.add_widget(self.obd_button)

        # Add both panels to row
        row_layout.add_widget(bt_layout)
        row_layout.add_widget(obd_layout)

        # Add row to main layout
        main_layout.add_widget(row_layout)

        self.add_widget(main_layout)

    # ==========================
    # OBD LOGIC
    # ==========================
    def toggle_obd(self, instance):
        if OBDService.connected:
            OBDService.disconnect()
            self.obd_status.text = "OBD: Disconnected"
            self.obd_button.text = "Connect OBD"
        else:
            if OBDService.connect(self.port_input.text.strip()):
                self.obd_status.text = "OBD: Connected"
                self.obd_button.text = "Disconnect OBD"
            else:
                self.obd_status.text = "OBD: Failed"

    # ==========================
    # BLUETOOTH LOGIC
    # ==========================
    def refresh_devices(self, dt):
        self.device_list.clear_widgets()
        devices = bluetooth_service.get_devices()

        if not devices:
            self.device_list.add_widget(
                Label(text="No Bluetooth devices found", size_hint_y=None, height=60)
            )
            return

        for dev in devices:
            status = "   ✓ Connected" if dev["connected"] else "   Paired" if dev["paired"] else ""
            btn = Button(text=f"{dev['name']}{status}", size_hint_y=None, height=65)
            btn.bind(
                on_release=lambda x, path=dev["path"], connected=dev["connected"]: self.toggle_device(path, connected)
            )
            self.device_list.add_widget(btn)

    def manual_refresh(self, instance):
        self.refresh_button.text = "Scanning..."
        bluetooth_service.stop_scan()
        bluetooth_service.start_scan()
        self.refresh_devices(0)
        Clock.schedule_once(lambda dt: setattr(self.refresh_button, "text", "Refresh"), 2)

    def toggle_discoverable(self, instance):
        current = bluetooth_service.is_discoverable()
        if bluetooth_service.set_discoverable(not current):
            self.discoverable_button.text = "Discoverable: ON" if not current else "Make Discoverable"

    # ==========================
    # PAIR / CONNECT DEVICE WITH OVERLAY
    # ==========================
    def toggle_device(self, path, connected):
        if connected:
            bluetooth_service.disconnect(path)
            Clock.schedule_once(lambda dt: self.refresh_devices(0), 1)
        else:
            Clock.schedule_once(lambda dt: self.connect_device(path), 0.1)

    def connect_device(self, path):
        try:
            device = bluetooth_service.sys_bus.get("org.bluez", path)
            device.Connect()
        except Exception as e:
            print("Bluetooth pairing error:", e)
        finally:
            self.dismiss_pairing_overlay()
            Clock.schedule_once(lambda dt: self.refresh_devices(0), 1)