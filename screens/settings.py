from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from services.bluetooth import bluetooth_service
from services.obd import obd_service


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        main_layout = BoxLayout(
            orientation="horizontal",
            padding=dp(22),
            spacing=dp(18),
        )

        bt_card = self._build_card("Bluetooth", "Manage paired devices and discovery mode.")
        bt_body = BoxLayout(orientation="vertical", spacing=dp(14))

        button_row = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(52))
        self.discoverable_button = self._make_button("Make Discoverable")
        self.refresh_button = self._make_button("Refresh")
        self.discoverable_button.bind(on_release=self.toggle_discoverable)
        self.refresh_button.bind(on_release=self.manual_refresh)
        button_row.add_widget(self.discoverable_button)
        button_row.add_widget(self.refresh_button)

        self.device_list = GridLayout(cols=1, spacing=dp(10), size_hint_y=None)
        self.device_list.bind(minimum_height=self.device_list.setter("height"))
        scroll = ScrollView()
        scroll.add_widget(self.device_list)

        bt_body.add_widget(button_row)
        bt_body.add_widget(scroll)
        bt_card.add_widget(bt_body)

        obd_card = self._build_card("OBD-II", "Choose the serial device used for speed and RPM telemetry.")
        obd_body = BoxLayout(orientation="vertical", spacing=dp(14))
        self.obd_status = MDLabel(
            text="OBD: Disconnected",
            theme_text_color="Custom",
            text_color=(0.86, 0.91, 0.96, 1),
        )
        self.port_input = TextInput(
            text="/dev/ttyUSB0",
            multiline=False,
            size_hint_y=None,
            height=dp(52),
            background_color=(0.1, 0.14, 0.2, 1),
            foreground_color=(0.96, 0.98, 1, 1),
            cursor_color=(0.38, 0.78, 1, 1),
            padding=(dp(14), dp(14)),
        )
        self.obd_button = self._make_button("Connect OBD")
        self.obd_button.bind(on_release=self.toggle_obd)

        obd_body.add_widget(self.obd_status)
        obd_body.add_widget(self.port_input)
        obd_body.add_widget(self.obd_button)
        obd_body.add_widget(Label())
        obd_card.add_widget(obd_body)

        main_layout.add_widget(bt_card)
        main_layout.add_widget(obd_card)
        self.add_widget(main_layout)

        bluetooth_service.start_scan()
        if bluetooth_service.is_discoverable():
            self.discoverable_button.text = "Discoverable: ON"

        self._sync_obd_state()
        Clock.schedule_interval(self.refresh_devices, 3)

    def _build_card(self, title, subtitle):
        card = MDCard(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(14),
            radius=[dp(30)],
            elevation=0,
            md_bg_color=(0.08, 0.11, 0.16, 0.98),
            size_hint=(0.5, 1),
        )
        card.add_widget(
            MDLabel(
                text=title,
                theme_text_color="Custom",
                text_color=(0.98, 0.99, 1, 1),
                bold=True,
                font_style="H5",
            )
        )
        card.add_widget(
            MDLabel(
                text=subtitle,
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=(0.61, 0.7, 0.79, 1),
            )
        )
        return card

    def _make_button(self, text):
        button = Button(
            text=text,
            background_normal="",
            background_color=(0.17, 0.4, 0.64, 1),
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(52),
        )
        return button

    def _sync_obd_state(self):
        if obd_service.connected:
            self.obd_status.text = "OBD: Connected"
            self.obd_button.text = "Disconnect OBD"
        else:
            self.obd_status.text = "OBD: Disconnected"
            self.obd_button.text = "Connect OBD"

    def toggle_obd(self, instance):
        if obd_service.connected:
            obd_service.disconnect()
        else:
            if not obd_service.connect(self.port_input.text.strip()):
                self.obd_status.text = "OBD: Failed to connect"
                self.obd_button.text = "Connect OBD"
                return
        self._sync_obd_state()

    def refresh_devices(self, dt):
        self.device_list.clear_widgets()
        devices = bluetooth_service.get_devices()

        if not devices:
            self.device_list.add_widget(
                Label(
                    text="No Bluetooth devices found",
                    size_hint_y=None,
                    height=dp(60),
                    color=(0.8, 0.86, 0.92, 1),
                )
            )
            return

        for dev in devices:
            status = "Connected" if dev["connected"] else "Paired" if dev["paired"] else "Available"
            btn = self._make_button(f"{dev['name']}   [{status}]")
            btn.bind(
                on_release=lambda _, path=dev["path"], connected=dev["connected"]: self.toggle_device(path, connected)
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

    def toggle_device(self, path, connected):
        if connected:
            bluetooth_service.disconnect(path)
            Clock.schedule_once(lambda dt: self.refresh_devices(0), 1)
        else:
            Clock.schedule_once(lambda dt: self.connect_device(path), 0.1)

    def connect_device(self, path):
        try:
            bluetooth_service.connect(path)
        except Exception as exc:
            print("Bluetooth pairing error:", exc)
        finally:
            Clock.schedule_once(lambda dt: self.refresh_devices(0), 1)
