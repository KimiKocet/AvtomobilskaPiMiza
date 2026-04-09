from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from services.bluetooth import bluetooth_service
from services.obd import obd_service
from services.theme import theme_service


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cards = []
        self.subcards = []

        main_layout = BoxLayout(
            orientation="horizontal",
            padding=dp(22),
            spacing=dp(18),
        )

        self.bt_card = self._build_card("Bluetooth", "Minimal pairing controls and a cleaner device list.")
        bt_body = BoxLayout(orientation="vertical", spacing=dp(12))

        button_row = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(52))
        self.discoverable_button = ActionPill("Make Discoverable")
        self.refresh_button = ActionPill("Refresh", accent=False)
        self.discoverable_button.bind(on_release=self.toggle_discoverable)
        self.refresh_button.bind(on_release=self.manual_refresh)
        button_row.add_widget(self.discoverable_button)
        button_row.add_widget(self.refresh_button)

        self.devices_title = self._make_text("Devices", style="title")
        self.device_list = GridLayout(cols=1, spacing=dp(10), size_hint_y=None)
        self.device_list.bind(minimum_height=self.device_list.setter("height"))
        scroll = ScrollView(bar_width=dp(6), do_scroll_x=False)
        scroll.add_widget(self.device_list)

        bt_body.add_widget(button_row)
        bt_body.add_widget(self.devices_title)
        bt_body.add_widget(scroll)
        self.bt_card.add_widget(bt_body)

        self.system_card = self._build_card("System", "Appearance and OBD connection settings.")
        system_body = BoxLayout(orientation="vertical", spacing=dp(16))

        self.appearance_card = self._build_subcard()
        appearance_body = self._make_stack(spacing=dp(10))
        self.appearance_title = self._make_text("Appearance", style="title")
        self.appearance_copy = self._make_text("Switch the dashboard between dark and light surfaces.", style="muted")
        self.theme_button = ActionPill("Light Mode: Off", accent=False)
        self.theme_button.bind(on_release=self.toggle_theme)
        appearance_body.add_widget(self.appearance_title)
        appearance_body.add_widget(self.appearance_copy)
        appearance_body.add_widget(self.theme_button)
        self.appearance_card.add_widget(appearance_body)

        self.obd_card = self._build_subcard()
        obd_body = self._make_stack(spacing=dp(12))
        self.obd_title = self._make_text("OBD-II", style="title")
        self.obd_copy = self._make_text("Choose the serial device used for RPM and speed telemetry.", style="muted")
        self.obd_status = self._make_text("OBD: Disconnected", style="body")
        self.port_input = TextInput(
            text="/dev/ttyUSB0",
            multiline=False,
            size_hint_y=None,
            height=dp(52),
            padding=(dp(14), dp(14)),
        )
        self.obd_button = ActionPill("Connect OBD")
        self.obd_button.bind(on_release=self.toggle_obd)
        obd_body.add_widget(self.obd_title)
        obd_body.add_widget(self.obd_copy)
        obd_body.add_widget(self.obd_status)
        obd_body.add_widget(self.port_input)
        obd_body.add_widget(self.obd_button)
        self.obd_card.add_widget(obd_body)

        system_body.add_widget(self.appearance_card)
        system_body.add_widget(Widget())
        system_body.add_widget(self.obd_card)
        self.system_card.add_widget(system_body)

        main_layout.add_widget(self.bt_card)
        main_layout.add_widget(self.system_card)
        self.add_widget(main_layout)

        bluetooth_service.start_scan()
        if bluetooth_service.is_discoverable():
            self.discoverable_button.set_text("Discoverable: On")

        self._sync_obd_state()
        theme_service.bind(mode=self._apply_theme)
        self._apply_theme()
        Clock.schedule_interval(self.refresh_devices, 3)

    def _build_card(self, title, subtitle):
        card = MDCard(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(12),
            radius=[dp(30)],
            elevation=0,
            size_hint=(0.5, 1),
        )
        header_box = self._make_stack(spacing=dp(6))
        card.title_label = self._make_text(title, style="header")
        card.subtitle_label = self._make_text(subtitle, style="muted")
        header_box.add_widget(card.title_label)
        header_box.add_widget(card.subtitle_label)
        card.add_widget(header_box)
        self.cards.append(card)
        return card

    def _build_subcard(self):
        card = MDCard(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(10),
            radius=[dp(24)],
            elevation=0,
            size_hint_y=None,
            adaptive_height=True,
        )
        self.subcards.append(card)
        return card

    def _make_stack(self, spacing=0):
        layout = BoxLayout(orientation="vertical", spacing=spacing, size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))
        return layout

    def _make_text(self, text, style="body"):
        label = MDLabel(text=text, theme_text_color="Custom")
        label.style_name = style
        if style == "header":
            label.bold = True
            label.font_style = "H5"
        elif style == "title":
            label.bold = True
            label.adaptive_height = True
        else:
            label.adaptive_height = True
        return label

    def _apply_theme(self, *_):
        palette = theme_service.palette
        for card in self.cards:
            card.md_bg_color = palette["card"]
            card.title_label.text_color = palette["text"]
            card.subtitle_label.text_color = palette["muted"]

        for card in self.subcards:
            card.md_bg_color = palette["card_soft"]

        for label in [
            self.devices_title,
            self.appearance_title,
            self.obd_title,
            self.obd_status,
        ]:
            label.text_color = palette["text"]

        for label in [
            self.appearance_copy,
            self.obd_copy,
        ]:
            label.text_color = palette["muted"]

        self.port_input.background_color = palette["input_bg"]
        self.port_input.foreground_color = palette["input_text"]
        self.port_input.cursor_color = palette["accent_strong"]
        self.theme_button.set_text(f"Light Mode: {'On' if theme_service.mode == 'light' else 'Off'}")
        self.theme_button.apply_theme()
        self.refresh_button.apply_theme()
        self.discoverable_button.apply_theme()
        self.obd_button.apply_theme()

        for child in self.device_list.children:
            if hasattr(child, "apply_theme"):
                child.apply_theme()

    def _sync_obd_state(self):
        if obd_service.connected:
            self.obd_status.text = "OBD: Connected"
            self.obd_button.set_text("Disconnect OBD")
        else:
            self.obd_status.text = "OBD: Disconnected"
            self.obd_button.set_text("Connect OBD")

    def toggle_theme(self, *_):
        next_mode = "light" if theme_service.mode == "dark" else "dark"
        app = MDApp.get_running_app()
        if hasattr(app, "set_theme_mode"):
            app.set_theme_mode(next_mode)
        else:
            theme_service.set_mode(next_mode)
        self._apply_theme()

    def toggle_obd(self, *_):
        if obd_service.connected:
            obd_service.disconnect()
        else:
            if not obd_service.connect(self.port_input.text.strip()):
                self.obd_status.text = "OBD: Failed to connect"
                self.obd_button.set_text("Connect OBD")
                return
        self._sync_obd_state()

    def refresh_devices(self, dt):
        self.device_list.clear_widgets()
        devices = bluetooth_service.get_devices()

        if not devices:
            empty = self._build_subcard()
            empty.add_widget(self._make_text("No Bluetooth devices found right now.", style="muted"))
            self.device_list.add_widget(empty)
            self._apply_theme()
            return

        for dev in devices:
            status = "Connected" if dev["connected"] else "Paired" if dev["paired"] else "Available"
            tile = DeviceTile(dev["name"], dev["address"], status)
            tile.bind(on_release=lambda _, path=dev["path"], connected=dev["connected"]: self.toggle_device(path, connected))
            self.device_list.add_widget(tile)

        self._apply_theme()

    def manual_refresh(self, *_):
        self.refresh_button.set_text("Scanning...")
        bluetooth_service.stop_scan()
        bluetooth_service.start_scan()
        self.refresh_devices(0)
        Clock.schedule_once(lambda dt: self.refresh_button.set_text("Refresh"), 2)

    def toggle_discoverable(self, *_):
        current = bluetooth_service.is_discoverable()
        if bluetooth_service.set_discoverable(not current):
            self.discoverable_button.set_text("Discoverable: On" if not current else "Make Discoverable")

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


class ActionPill(ButtonBehavior, AnchorLayout):
    def __init__(self, text, accent=True, **kwargs):
        super().__init__(**kwargs)
        self.accent = accent
        self.size_hint_y = None
        self.height = dp(52)
        self.padding = (dp(18), 0)
        self.anchor_x = "center"
        self.anchor_y = "center"
        self.corner_radius = [dp(22)]

        with self.canvas.before:
            self.bg_color = Color(0, 0, 0, 1)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=self.corner_radius)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.label = MDLabel(
            text=text,
            halign="center",
            theme_text_color="Custom",
            bold=True,
        )
        self.add_widget(self.label)
        theme_service.bind(mode=self.apply_theme)
        self.apply_theme()

    def _update_bg(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def set_text(self, text):
        self.label.text = text

    def apply_theme(self, *_):
        palette = theme_service.palette
        self.bg_color.rgba = palette["button_bg"] if self.accent else palette["chip"]
        self.label.text_color = palette["button_text"] if self.accent else palette["text"]
        self._update_bg()


class DeviceTile(ButtonBehavior, BoxLayout):
    def __init__(self, name, address, status, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.padding = dp(16)
        self.spacing = dp(10)
        self.size_hint_y = None
        self.height = dp(84)
        self.corner_radius = [dp(22)]

        with self.canvas.before:
            self.bg_color = Color(0, 0, 0, 1)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=self.corner_radius)
        self.bind(pos=self._update_bg, size=self._update_bg)

        text_box = BoxLayout(orientation="vertical", spacing=dp(2))
        self.name_label = MDLabel(text=name, theme_text_color="Custom", bold=True)
        self.address_label = MDLabel(text=address or "Unknown address", theme_text_color="Custom")
        text_box.add_widget(self.name_label)
        text_box.add_widget(self.address_label)

        self.status_chip = MDCard(
            size_hint=(None, None),
            size=(dp(116), dp(32)),
            radius=[dp(16)],
            elevation=0,
            padding=(dp(10), 0),
        )
        self.status_label = MDLabel(text=status, halign="center", theme_text_color="Custom", bold=True)
        self.status_chip.add_widget(self.status_label)

        self.add_widget(text_box)
        self.add_widget(self.status_chip)
        theme_service.bind(mode=self.apply_theme)
        self.apply_theme()

    def _update_bg(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def apply_theme(self, *_):
        palette = theme_service.palette
        self.bg_color.rgba = palette["card_soft"]
        self.name_label.text_color = palette["text"]
        self.address_label.text_color = palette["muted"]
        self.status_chip.md_bg_color = palette["chip"]
        self.status_label.text_color = palette["accent_strong"]
        self._update_bg()
