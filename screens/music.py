import threading

from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from services.spotify import SpotifyError, spotify_service
from services.theme import theme_service
from widgets.MediaPanel import MediaPanel


class MusicScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.playlists = []
        self.playlist_tiles = {}
        self.selected_playlist = None

        root = BoxLayout(orientation="horizontal", padding=dp(22), spacing=dp(18))

        self.left = MDCard(
            orientation="vertical",
            padding=dp(22),
            spacing=dp(14),
            radius=[dp(30)],
            elevation=0,
            size_hint=(0.42, 1),
        )
        self.copy_label = MDLabel(
            text="Clean playlist launch from the dashboard.",
            theme_text_color="Custom",
            adaptive_height=True,
        )
        self.status_label = MDLabel(
            text="Spotify is not configured.",
            theme_text_color="Custom",
            adaptive_height=True,
        )
        self.account_label = MDLabel(
            text="Account  Not connected",
            theme_text_color="Custom",
            adaptive_height=True,
        )
        self.device_label = MDLabel(
            text="Device  No Spotify device",
            theme_text_color="Custom",
            adaptive_height=True,
        )
        self.playlists_label = MDLabel(
            text="Playlists",
            theme_text_color="Custom",
            adaptive_height=True,
            bold=True,
        )

        self.selected_card = _SelectedPlaylistCard()
        self.selected_card.play_button.bind(on_release=lambda *_: self.play_playlist())

        self.playlist_list = GridLayout(rows=1, spacing=dp(8), size_hint_x=None)
        self.playlist_list.bind(minimum_width=self.playlist_list.setter("width"))
        self.playlist_scroll = ScrollView(bar_width=dp(5), do_scroll_x=True, do_scroll_y=False)
        self.playlist_scroll.add_widget(self.playlist_list)

        self.connect_button = _MusicButton("Connect")
        self.refresh_button = _MusicButton("Refresh", accent=False)
        self.sign_out_button = _MusicButton("Sign Out", accent=False)
        self.connect_button.bind(on_release=self.connect_spotify)
        self.refresh_button.bind(on_release=self.refresh_playlists)
        self.sign_out_button.bind(on_release=self.sign_out)

        button_row = BoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(48),
        )
        self.connect_button.size_hint_x = 1.15
        button_row.add_widget(self.connect_button)
        button_row.add_widget(self.refresh_button)
        button_row.add_widget(self.sign_out_button)

        self.left.add_widget(self.status_label)
        self.left.add_widget(self.selected_card)
        self.left.add_widget(button_row)

        right = BoxLayout(
            orientation="vertical",
            size_hint=(0.58, 1),
            spacing=dp(12),
        )
        
        playlist_container = BoxLayout(
            orientation="vertical",
            size_hint=(1, 0.22),
            spacing=dp(8),
        )
        playlist_label = MDLabel(
            text="Playlists",
            theme_text_color="Custom",
            adaptive_height=True,
            bold=True,
            size_hint_y=None,
            height=dp(24),
        )
        self.playlist_label_ref = playlist_label
        self.playlist_scroll.size_hint = (1, 1)
        playlist_container.add_widget(playlist_label)
        playlist_container.add_widget(self.playlist_scroll)
        
        media_anchor = AnchorLayout(size_hint=(1, 0.78))
        media_anchor.add_widget(MediaPanel(compact=True, size_hint=(0.94, 0.94)))
        
        right.add_widget(playlist_container)
        right.add_widget(media_anchor)

        root.add_widget(self.left)
        root.add_widget(right)
        self.add_widget(root)

        theme_service.bind(mode=self._apply_theme)
        spotify_service.bind(status=self._sync_spotify_state)
        spotify_service.bind(configured=self._sync_spotify_state)
        spotify_service.bind(connected=self._sync_spotify_state)
        spotify_service.bind(busy=self._sync_spotify_state)
        spotify_service.bind(account_name=self._sync_spotify_state)
        spotify_service.bind(account_product=self._sync_spotify_state)
        spotify_service.bind(device_name=self._sync_spotify_state)
        spotify_service.bind(playback_available=self._sync_spotify_state)
        self._sync_spotify_state()
        self._apply_theme()

    def on_enter(self):
        if spotify_service.configured and not spotify_service.busy and not self.playlists:
            Clock.schedule_once(lambda _dt: self.refresh_playlists(), 0)

    def _apply_theme(self, *_):
        palette = theme_service.palette
        self.left.md_bg_color = palette["card"]
        self.status_label.text_color = palette["accent"]
        self.playlist_label_ref.text_color = palette["text"]
        self.selected_card.apply_theme()
        self.connect_button.apply_theme()
        self.refresh_button.apply_theme()
        self.sign_out_button.apply_theme()
        for tile in self.playlist_tiles.values():
            tile.apply_theme()

    def _sync_spotify_state(self, *_):
        if spotify_service.configured:
            self.status_label.text = spotify_service.status
        else:
            self.status_label.text = spotify_service.status

        self.connect_button.set_text("Reconnect" if spotify_service.connected else "Connect")
        self.connect_button.disabled = spotify_service.busy
        self.refresh_button.disabled = spotify_service.busy or not spotify_service.configured
        self.sign_out_button.disabled = spotify_service.busy or not spotify_service.configured
        self.selected_card.play_button.disabled = not bool(self.selected_playlist and spotify_service.playback_available)

        if not spotify_service.configured and not self.playlists:
            self.selected_card.set_message(
                "Spotify setup needed",
                "Add your client ID to spotify_config.json, then connect from this screen.",
            )
        elif spotify_service.connected and not spotify_service.playback_available and not self.playlists and not spotify_service.busy:
            self.selected_card.set_message(
                "Spotify connected",
                "Your account can sign in and browse data, but playlist launch is locked because Spotify Premium is unavailable.",
            )
        elif spotify_service.configured and not self.playlists and not spotify_service.busy:
            self.selected_card.set_message(
                "No playlist loaded",
                "Tap Refresh after sign-in to load your playlists.",
            )

        self._apply_theme()

    def connect_spotify(self, *_):
        threading.Thread(target=self._connect_worker, daemon=True).start()

    def refresh_playlists(self, *_):
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def sign_out(self, *_):
        spotify_service.sign_out()
        self.playlists = []
        self.playlist_tiles = {}
        self.selected_playlist = None
        self.playlist_list.clear_widgets()
        self.selected_card.set_message("Spotify disconnected", "Use Connect when you want to link it again.")
        self._sync_spotify_state()

    def select_playlist(self, playlist, *_):
        self.selected_playlist = playlist
        self._refresh_playlist_tile_states()
        self.selected_card.set_loading(playlist)
        self._apply_theme()
        threading.Thread(target=self._load_playlist_worker, args=(playlist,), daemon=True).start()

    def play_playlist(self, playlist=None, offset=None, *_):
        target_playlist = playlist or self.selected_playlist
        if not target_playlist:
            return
        threading.Thread(target=self._play_playlist_worker, args=(target_playlist, offset), daemon=True).start()

    def _connect_worker(self):
        try:
            spotify_service.authorize()
            self._refresh_worker()
        except SpotifyError as exc:
            spotify_service.set_status(str(exc), busy=False)

    def _refresh_worker(self):
        spotify_service.set_status("Loading Spotify playlists...", busy=True)
        try:
            spotify_service.reload_config()
            profile = spotify_service.get_profile()
            display_name, _product, playback_available = spotify_service.sync_profile(profile)
            playlists = spotify_service.get_playlists(limit=14)
            device_warning = ""
            try:
                spotify_service.get_devices()
            except SpotifyError as exc:
                device_warning = str(exc)
            Clock.schedule_once(lambda _dt, data=playlists: self._populate_playlists(data), 0)
            if playback_available:
                spotify_service.set_status(f"Loaded {len(playlists)} playlists.", busy=False)
            else:
                message = f"Loaded {len(playlists)} playlists. Playback controls are locked because Spotify Premium is unavailable."
                if device_warning:
                    message = f"{message} {device_warning}"
                spotify_service.set_status(message, busy=False)
        except SpotifyError as exc:
            spotify_service.set_status(str(exc), busy=False)

    def _load_playlist_worker(self, playlist):
        try:
            details = spotify_service.get_playlist_items(playlist["id"], limit=3)
            items = details.get("items", [])
            note = ""
            if not items:
                note = "No track preview returned for this playlist."
        except SpotifyError:
            items = []
            note = "Track preview is unavailable for this playlist. You can still play the full playlist."
        Clock.schedule_once(
            lambda _dt, data=playlist, tracks=items, fallback=note: self._show_playlist_details(data, tracks, fallback),
            0,
        )

    def _play_playlist_worker(self, playlist, offset):
        spotify_service.set_status(f'Starting "{playlist["name"]}"...', busy=True)
        try:
            target = spotify_service.play_playlist(playlist["uri"], offset=offset)
            spotify_service.set_status(f'Playing "{playlist["name"]}" on {target["name"]}.', busy=False)
        except SpotifyError as exc:
            spotify_service.set_status(str(exc), busy=False)

    def _populate_playlists(self, playlists):
        self.playlists = playlists
        self.playlist_tiles = {}
        self.playlist_list.clear_widgets()

        if not playlists:
            self.selected_playlist = None
            self.selected_card.set_message("No playlists found", "Spotify returned no playlists for this account.")
            self._apply_theme()
            return

        for playlist in playlists:
            tile = _PlaylistIconTile(
                image_url=playlist.get("image_url", ""),
                playlist_id=playlist["id"],
            )
            tile.bind(on_release=lambda _tile, data=playlist: self.select_playlist(data))
            self.playlist_tiles[playlist["id"]] = tile
            self.playlist_list.add_widget(tile)

        selected = next((item for item in playlists if self.selected_playlist and item["id"] == self.selected_playlist["id"]), None)
        self.select_playlist(selected or playlists[0])

    def _show_playlist_details(self, playlist, items, fallback_note):
        if not self.selected_playlist or playlist["id"] != self.selected_playlist["id"]:
            return

        body = playlist["description"] or fallback_note or "Select Play Playlist to launch this list on your active device."
        if not spotify_service.playback_available:
            lock_note = "Playback is locked because Spotify Premium is unavailable."
            body = f"{body}\n\n{lock_note}" if body else lock_note
        self.selected_card.set_playlist(playlist, body)
        self.selected_card.tracks_box.clear_widgets()

        for index, item in enumerate(items):
            row = _TrackRow(
                index=index + 1,
                title=item["name"],
                subtitle=item["artists"],
                hint=item["duration_label"],
            )
            if spotify_service.playback_available:
                row.bind(on_release=lambda _row, position=index: self.play_playlist(offset=position))
            self.selected_card.tracks_box.add_widget(row)

        self.selected_card.play_button.disabled = not spotify_service.playback_available

        self._apply_theme()

    def _refresh_playlist_tile_states(self):
        selected_id = self.selected_playlist["id"] if self.selected_playlist else None
        for playlist_id, tile in self.playlist_tiles.items():
            tile.set_active(playlist_id == selected_id)
        self._apply_theme()


class _MusicButton(ButtonBehavior, AnchorLayout):
    def __init__(self, text, accent=True, **kwargs):
        super().__init__(**kwargs)
        self.accent = accent
        self.size_hint_y = None
        self.height = dp(48)
        self.padding = (dp(12), 0)
        self.anchor_x = "center"
        self.anchor_y = "center"
        self.corner_radius = [dp(16)]

        with self.canvas.before:
            self.bg_color = Color(0, 0, 0, 1)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=self.corner_radius)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.label = MDLabel(
            text=text,
            halign="center",
            valign="middle",
            theme_text_color="Custom",
            bold=True,
            font_size="11sp",
            shorten=True,
            max_lines=1,
        )
        self.label.bind(size=lambda widget, _size: setattr(widget, "text_size", widget.size))
        self.add_widget(self.label)
        theme_service.bind(mode=self.apply_theme)
        self.apply_theme()

    def _update_bg(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def set_text(self, text):
        self.label.text = text

    def on_disabled(self, *_):
        self.apply_theme()

    def apply_theme(self, *_):
        palette = theme_service.palette
        if self.disabled:
            self.bg_color.rgba = palette["chip"]
            self.label.text_color = palette["subtle"]
        else:
            self.bg_color.rgba = palette["button_bg"] if self.accent else palette["card_soft"]
            self.label.text_color = palette["button_text"] if self.accent else palette["text"]
        self._update_bg()


class _SelectedPlaylistCard(MDCard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = dp(18)
        self.spacing = dp(12)
        self.radius = [dp(24)]
        self.elevation = 0
        self.size_hint_y = 1

        self.eyebrow_label = MDLabel(
            text="Selected",
            theme_text_color="Custom",
            size_hint_y=None,
            height=dp(20),
        )
        self.title_label = MDLabel(
            text="No playlist loaded",
            theme_text_color="Custom",
            bold=True,
            size_hint_y=None,
            font_style="H6",
        )
        self.meta_label = MDLabel(
            text="",
            theme_text_color="Custom",
            size_hint_y=None,
        )
        self.body_label = MDLabel(
            text="Tap Refresh to load Spotify playlists.",
            theme_text_color="Custom",
            size_hint_y=None,
            valign="top",
        )
        self.header_box = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            size_hint_y=None,
        )
        self.header_box.bind(minimum_height=self.header_box.setter("height"))
        self.tracks_box = GridLayout(cols=1, spacing=dp(8), size_hint=(1, None), padding=(0, 0, 0, dp(2)))
        self.tracks_box.bind(minimum_height=self.tracks_box.setter("height"))
        self.tracks_scroll = ScrollView(
            do_scroll_x=False,
            bar_width=dp(4),
            scroll_type=["bars", "content"],
        )
        self.tracks_scroll.add_widget(self.tracks_box)
        self.play_button = _MusicButton("Play Playlist")

        self.header_box.add_widget(self.eyebrow_label)
        self.header_box.add_widget(self.title_label)
        self.header_box.add_widget(self.meta_label)
        self.header_box.add_widget(self.body_label)

        self.add_widget(self.header_box)
        self.add_widget(self.tracks_scroll)
        self.add_widget(self.play_button)

        self._wrap_label(self.title_label)
        self._wrap_label(self.meta_label)
        self._wrap_label(self.body_label)
        theme_service.bind(mode=self.apply_theme)
        self.apply_theme()

    @staticmethod
    def _wrap_label(label):
        def _sync_text_width(instance, width):
            instance.text_size = (width, None)

        def _sync_height(instance, texture_size):
            instance.height = texture_size[1]

        label.bind(width=_sync_text_width)
        label.bind(texture_size=_sync_height)
        label.text_size = (label.width, None)

    def set_message(self, title, body):
        self.title_label.text = title
        self.meta_label.text = ""
        self.body_label.text = body
        self.tracks_box.clear_widgets()
        self.tracks_scroll.scroll_y = 1
        self.play_button.disabled = True

    def set_loading(self, playlist):
        self.title_label.text = playlist["name"]
        self.meta_label.text = f'{playlist["owner"]}  |  {playlist["tracks_total"]} tracks'
        self.body_label.text = "Loading preview..."
        self.tracks_box.clear_widgets()
        self.tracks_scroll.scroll_y = 1
        self.play_button.disabled = True

    def set_playlist(self, playlist, body):
        self.title_label.text = playlist["name"]
        self.meta_label.text = f'{playlist["owner"]}  |  {playlist["tracks_total"]} tracks'
        self.body_label.text = body
        self.tracks_scroll.scroll_y = 1
        self.play_button.disabled = False

    def apply_theme(self, *_):
        palette = theme_service.palette
        self.md_bg_color = palette["card_soft"]
        self.eyebrow_label.text_color = palette["accent"]
        self.title_label.text_color = palette["text"]
        self.meta_label.text_color = palette["subtle"]
        self.body_label.text_color = palette["muted"]
        self.play_button.apply_theme()
        for child in self.tracks_box.children:
            if hasattr(child, "apply_theme"):
                child.apply_theme()


class _PlaylistIconTile(MDCard, ButtonBehavior):
    def __init__(self, image_url, playlist_id, **kwargs):
        super().__init__(**kwargs)
        self.active = False
        self.playlist_id = playlist_id
        self.orientation = "vertical"
        self.padding = 0
        self.spacing = 0
        self.radius = [dp(16)]
        self.elevation = 0
        self.size_hint = (None, None)
        self.size = (dp(80), dp(80))

        self.image = AsyncImage(
            source=image_url,
            size_hint=(1, 1),
            keep_ratio=True,
        )
        self.add_widget(self.image)
        theme_service.bind(mode=self.apply_theme)
        self.apply_theme()

    def set_active(self, active):
        self.active = bool(active)
        self.apply_theme()

    def apply_theme(self, *_):
        palette = theme_service.palette
        self.md_bg_color = palette["nav_active"] if self.active else palette["card_alt"]


class _PlaylistTile(MDCard, ButtonBehavior):
    def __init__(self, title, subtitle, **kwargs):
        super().__init__(**kwargs)
        self.active = False
        self.orientation = "vertical"
        self.padding = dp(14)
        self.spacing = dp(4)
        self.radius = [dp(20)]
        self.elevation = 0
        self.size_hint_y = None
        self.height = dp(84)

        self.title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            bold=True,
            adaptive_height=True,
        )
        self.subtitle_label = MDLabel(
            text=subtitle,
            theme_text_color="Custom",
            adaptive_height=True,
        )
        self.add_widget(self.title_label)
        self.add_widget(self.subtitle_label)
        theme_service.bind(mode=self.apply_theme)
        self.apply_theme()

    def set_active(self, active):
        self.active = bool(active)
        self.apply_theme()

    def apply_theme(self, *_):
        palette = theme_service.palette
        self.md_bg_color = palette["nav_active"] if self.active else palette["card_alt"]
        self.title_label.text_color = palette["button_text"] if self.active else palette["text"]
        self.subtitle_label.text_color = palette["button_text"] if self.active else palette["muted"]


class _TrackRow(ButtonBehavior, BoxLayout):
    def __init__(self, index, title, subtitle, hint, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.spacing = dp(12)
        self.padding = (dp(12), dp(10))
        self.size_hint_y = None
        self.height = dp(64)
        self.corner_radius = [dp(18)]

        with self.canvas.before:
            self.bg_color = Color(0, 0, 0, 1)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=self.corner_radius)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.index_label = MDLabel(
            text=f"{index:02d}",
            size_hint=(None, 1),
            width=dp(42),
            halign="center",
            valign="middle",
            theme_text_color="Custom",
            bold=True,
        )
        self.index_label.bind(size=lambda widget, _size: setattr(widget, "text_size", widget.size))
        text_box = BoxLayout(orientation="vertical", spacing=dp(3), size_hint=(1, 1))
        self.title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            bold=True,
            size_hint_y=None,
            height=dp(22),
            shorten=True,
            max_lines=1,
            valign="middle",
        )
        self.subtitle_label = MDLabel(
            text=subtitle,
            theme_text_color="Custom",
            size_hint_y=None,
            height=dp(20),
            shorten=True,
            max_lines=1,
            valign="middle",
        )
        self.title_label.bind(size=lambda widget, _size: setattr(widget, "text_size", widget.size))
        self.subtitle_label.bind(size=lambda widget, _size: setattr(widget, "text_size", widget.size))
        text_box.add_widget(self.title_label)
        text_box.add_widget(self.subtitle_label)
        self.hint_label = MDLabel(
            text=hint,
            size_hint=(None, 1),
            width=dp(56),
            halign="right",
            valign="middle",
            theme_text_color="Custom",
            shorten=True,
            max_lines=1,
        )
        self.hint_label.bind(size=lambda widget, _size: setattr(widget, "text_size", widget.size))

        self.add_widget(self.index_label)
        self.add_widget(text_box)
        self.add_widget(self.hint_label)
        theme_service.bind(mode=self.apply_theme)
        self.apply_theme()

    def _update_bg(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def apply_theme(self, *_):
        palette = theme_service.palette
        self.bg_color.rgba = palette["chip"]
        self.index_label.text_color = palette["accent"]
        self.title_label.text_color = palette["text"]
        self.subtitle_label.text_color = palette["muted"]
        self.hint_label.text_color = palette["subtle"]
        self._update_bg()
