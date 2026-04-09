import base64
import hashlib
import html
import json
import os
import re
import secrets
import string
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, StringProperty


AUTH_BASE_URL = "https://accounts.spotify.com"
API_BASE_URL = "https://api.spotify.com/v1"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = " ".join(
    [
        "playlist-read-private",
        "playlist-read-collaborative",
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-private",
    ]
)
VERIFIER_CHARS = string.ascii_letters + string.digits + "-._~"


class SpotifyError(RuntimeError):
    pass


class SpotifyService(EventDispatcher):
    configured = BooleanProperty(False)
    connected = BooleanProperty(False)
    busy = BooleanProperty(False)
    status = StringProperty("Spotify is not configured.")
    account_name = StringProperty("Not connected")
    device_name = StringProperty("No Spotify device")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(self.project_root, "spotify_config.json")
        self.token_dir = os.path.join(os.path.expanduser("~"), ".config", "avtomobilska_pimiza")
        self.token_path = os.path.join(self.token_dir, "spotify_tokens.json")
        self.client_id = ""
        self.redirect_uri = DEFAULT_REDIRECT_URI
        self._configured = False
        self._tokens = {}
        self._lock = threading.Lock()
        self._load_tokens()
        self.reload_config()

    def reload_config(self):
        config_data = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as handle:
                    config_data = json.load(handle)
            except Exception:
                config_data = {}

        self.client_id = (
            os.environ.get("SPOTIFY_CLIENT_ID")
            or config_data.get("client_id")
            or ""
        ).strip()
        self.redirect_uri = (
            os.environ.get("SPOTIFY_REDIRECT_URI")
            or config_data.get("redirect_uri")
            or DEFAULT_REDIRECT_URI
        ).strip()

        is_configured = bool(self.client_id and self.redirect_uri)
        self._configured = is_configured
        self._dispatch_state(configured=is_configured)
        if not is_configured:
            self._dispatch_state(
                connected=False,
                account_name="Not connected",
                device_name="No Spotify device",
                status="Create spotify_config.json with your Spotify Client ID.",
            )
            return

        if self._tokens.get("refresh_token") or self._tokens.get("access_token"):
            self._dispatch_state(status="Spotify ready. Tap Refresh to load playlists.")
        else:
            self._dispatch_state(status="Spotify configured. Tap Connect to sign in.")

    def set_status(self, text, busy=None):
        updates = {"status": text}
        if busy is not None:
            updates["busy"] = bool(busy)
        self._dispatch_state(**updates)

    def authorize(self):
        self.reload_config()
        if not self._configured:
            raise SpotifyError("Spotify is not configured.")

        with self._lock:
            self._dispatch_state(busy=True, status="Opening Spotify sign-in...")
            try:
                code_verifier = "".join(secrets.choice(VERIFIER_CHARS) for _ in range(64))
                state = secrets.token_urlsafe(18)
                code_challenge = self._build_code_challenge(code_verifier)
                auth_url = self._build_authorize_url(state, code_challenge)
                code = self._wait_for_authorization(auth_url, state)
                self._exchange_code_for_token(code, code_verifier)
                profile = self.get_profile()
                display_name = profile.get("display_name") or "Spotify user"
                self._dispatch_state(
                    connected=True,
                    account_name=display_name,
                    status=f"Connected as {display_name}.",
                )
                return display_name
            finally:
                self._dispatch_state(busy=False)

    def sign_out(self):
        self._tokens = {}
        try:
            os.remove(self.token_path)
        except FileNotFoundError:
            pass
        except Exception:
            pass
        self._dispatch_state(
            connected=False,
            account_name="Not connected",
            device_name="No Spotify device",
            status="Spotify disconnected.",
        )

    def get_profile(self):
        return self.api_request("GET", "/me")

    def get_playlists(self, limit=12):
        payload = self.api_request(
            "GET",
            "/me/playlists",
            query={"limit": min(max(int(limit), 1), 50)},
        )
        playlists = []
        for item in payload.get("items", []):
            playlists.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name") or "Untitled playlist",
                    "description": self._clean_text(item.get("description", "")),
                    "owner": (item.get("owner") or {}).get("display_name") or "Spotify",
                    "uri": item.get("uri"),
                    "external_url": ((item.get("external_urls") or {}).get("spotify") or ""),
                    "tracks_total": self._playlist_total(item),
                }
            )
        self._dispatch_state(connected=True)
        return playlists

    def get_playlist_items(self, playlist_id, limit=8):
        payload = self.api_request(
            "GET",
            f"/playlists/{playlist_id}/items",
            query={
                "limit": min(max(int(limit), 1), 20),
                "fields": "items(item(name,uri,duration_ms,artists(name),type),track(name,uri,duration_ms,artists(name),type)),total",
            },
        )
        items = []
        for entry in payload.get("items", []):
            media = entry.get("item") or entry.get("track") or {}
            if not media:
                continue
            artist_names = ", ".join(artist.get("name", "") for artist in media.get("artists", []))
            items.append(
                {
                    "name": media.get("name") or "Unknown item",
                    "uri": media.get("uri"),
                    "artists": artist_names or "Unknown artist",
                    "duration_label": self._format_duration(media.get("duration_ms", 0)),
                    "type": media.get("type") or "track",
                }
            )
        return {
            "items": items,
            "total": payload.get("total", len(items)),
        }

    def get_devices(self):
        payload = self.api_request("GET", "/me/player/devices")
        devices = []
        for device in payload.get("devices", []):
            devices.append(
                {
                    "id": device.get("id"),
                    "name": device.get("name") or "Spotify device",
                    "type": device.get("type") or "device",
                    "active": bool(device.get("is_active")),
                    "restricted": bool(device.get("is_restricted")),
                }
            )
        active = next((device for device in devices if device["active"]), None)
        label = (
            f'{active["name"]} ({active["type"]})'
            if active
            else f'{devices[0]["name"]} ({devices[0]["type"]})'
            if devices
            else "No Spotify Connect device"
        )
        self._dispatch_state(device_name=label)
        return devices

    def play_playlist(self, playlist_uri, offset=None):
        target = self._ensure_playback_device()
        body = {"context_uri": playlist_uri}
        if offset is not None:
            body["offset"] = {"position": max(int(offset), 0)}
        self.api_request("PUT", "/me/player/play", query={"device_id": target["id"]}, body=body)
        self._dispatch_state(
            device_name=f'{target["name"]} ({target["type"]})',
            status=f'Playing on {target["name"]}.',
        )
        return target

    def _ensure_playback_device(self):
        devices = self.get_devices()
        active = next((device for device in devices if device["active"] and not device["restricted"] and device["id"]), None)
        if active:
            return active

        available = next((device for device in devices if not device["restricted"] and device["id"]), None)
        if not available:
            raise SpotifyError("Open Spotify on your Pi, phone, or another Spotify Connect device first.")

        self.api_request(
            "PUT",
            "/me/player",
            body={"device_ids": [available["id"]], "play": False},
        )
        return available

    def api_request(self, method, path, query=None, body=None, retry=True):
        token = self._ensure_access_token()
        url = f"{API_BASE_URL}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"

        data = None
        headers = {"Authorization": f"Bearer {token}"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                if response.status == 204:
                    return {}
                payload = response.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as exc:
            details = self._extract_http_error(exc)
            if exc.code == 401 and retry and self._tokens.get("refresh_token"):
                self._refresh_access_token()
                return self.api_request(method, path, query=query, body=body, retry=False)
            raise SpotifyError(details) from exc
        except urllib.error.URLError as exc:
            raise SpotifyError(f"Spotify network error: {exc.reason}") from exc

    def _ensure_access_token(self):
        if not self._configured:
            raise SpotifyError("Spotify is not configured.")

        expires_at = float(self._tokens.get("expires_at", 0))
        access_token = self._tokens.get("access_token")
        if access_token and time.time() < max(expires_at - 60, 0):
            self._dispatch_state(connected=True)
            return access_token

        if self._tokens.get("refresh_token"):
            self._refresh_access_token()
            self._dispatch_state(connected=True)
            return self._tokens.get("access_token")

        self._dispatch_state(connected=False)
        raise SpotifyError("Spotify sign-in required. Tap Connect to sign in.")

    def _refresh_access_token(self):
        payload = self._token_request(
            {
                "client_id": self.client_id,
                "grant_type": "refresh_token",
                "refresh_token": self._tokens.get("refresh_token", ""),
            }
        )
        self._apply_token_payload(payload, keep_existing_refresh=True)

    def _exchange_code_for_token(self, code, code_verifier):
        payload = self._token_request(
            {
                "client_id": self.client_id,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": code_verifier,
            }
        )
        self._apply_token_payload(payload, keep_existing_refresh=False)

    def _token_request(self, form_data):
        request = urllib.request.Request(
            f"{AUTH_BASE_URL}/api/token",
            data=urllib.parse.urlencode(form_data).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise SpotifyError(self._extract_http_error(exc)) from exc
        except urllib.error.URLError as exc:
            raise SpotifyError(f"Spotify network error: {exc.reason}") from exc

    def _apply_token_payload(self, payload, keep_existing_refresh):
        refresh_token = payload.get("refresh_token") or (self._tokens.get("refresh_token") if keep_existing_refresh else "")
        self._tokens = {
            "access_token": payload.get("access_token", ""),
            "refresh_token": refresh_token,
            "expires_at": time.time() + int(payload.get("expires_in", 3600)),
            "scope": payload.get("scope", ""),
            "token_type": payload.get("token_type", "Bearer"),
        }
        self._save_tokens()

    def _build_authorize_url(self, state, code_challenge):
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": SCOPES,
            "state": state,
            "code_challenge_method": "S256",
            "code_challenge": code_challenge,
            "show_dialog": "true",
        }
        return f"{AUTH_BASE_URL}/authorize?{urllib.parse.urlencode(params)}"

    def _wait_for_authorization(self, auth_url, expected_state):
        redirect_parts = urllib.parse.urlparse(self.redirect_uri)
        host = redirect_parts.hostname or "127.0.0.1"
        port = redirect_parts.port or 8888
        expected_path = redirect_parts.path or "/"
        auth_response = {}

        class CallbackHandler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                return

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path != expected_path:
                    self.send_response(404)
                    self.end_headers()
                    return

                query = urllib.parse.parse_qs(parsed.query)
                auth_response["code"] = query.get("code", [""])[0]
                auth_response["state"] = query.get("state", [""])[0]
                auth_response["error"] = query.get("error", [""])[0]

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    b"<html><body style='font-family:sans-serif;background:#10161f;color:#ffffff;'>"
                    b"<h2>Spotify linked</h2><p>You can close this window and return to the dashboard.</p>"
                    b"</body></html>"
                )

        try:
            server = HTTPServer((host, port), CallbackHandler)
        except OSError as exc:
            raise SpotifyError(f"Spotify callback server could not start on {host}:{port}: {exc}") from exc

        server.timeout = 240
        server_thread = threading.Thread(target=server.handle_request, daemon=True)
        server_thread.start()

        opened = webbrowser.open(auth_url)
        if not opened:
            print("Spotify authorization URL:", auth_url)

        self._dispatch_state(status="Finish Spotify sign-in in the browser window...")
        server_thread.join(240)
        server.server_close()

        if auth_response.get("error"):
            raise SpotifyError(f"Spotify authorization failed: {auth_response['error']}")
        if auth_response.get("state") != expected_state:
            raise SpotifyError("Spotify authorization was rejected due to invalid state.")
        if not auth_response.get("code"):
            raise SpotifyError("Spotify sign-in timed out.")
        return auth_response["code"]

    @staticmethod
    def _build_code_challenge(code_verifier):
        digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    @staticmethod
    def _clean_text(value):
        text = html.unescape(value or "")
        return re.sub(r"<[^>]+>", "", text).strip()

    @staticmethod
    def _playlist_total(item):
        details = item.get("items") or item.get("tracks") or {}
        return int(details.get("total") or 0)

    @staticmethod
    def _format_duration(duration_ms):
        total_seconds = max(int(duration_ms or 0) // 1000, 0)
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes}:{seconds:02d}"

    @staticmethod
    def _extract_http_error(exc):
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            return f"Spotify request failed with HTTP {exc.code}."

        error = payload.get("error", {})
        if isinstance(error, dict):
            message = error.get("message") or payload.get("error_description")
        else:
            message = payload.get("error_description") or str(error)
        return message or f"Spotify request failed with HTTP {exc.code}."

    def _load_tokens(self):
        if not os.path.exists(self.token_path):
            self._tokens = {}
            return
        try:
            with open(self.token_path, "r", encoding="utf-8") as handle:
                self._tokens = json.load(handle)
        except Exception:
            self._tokens = {}

    def _save_tokens(self):
        os.makedirs(self.token_dir, exist_ok=True)
        with open(self.token_path, "w", encoding="utf-8") as handle:
            json.dump(self._tokens, handle)

    def _dispatch_state(self, **values):
        def apply_state(_dt):
            for key, value in values.items():
                setattr(self, key, value)

        Clock.schedule_once(apply_state, 0)


spotify_service = SpotifyService()
