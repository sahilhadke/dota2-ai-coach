import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from collections import defaultdict
from typing import Callable

from dota2gsipy.hero.hero import Hero
from dota2gsipy.map import Map
from dota2gsipy.player import Player
from dota2gsipy.provider import Provider

logger = logging.getLogger(__name__)

EXTRA_DATA_KEYS = ("buildings", "minimap", "couriers", "draft", "wearables", "neutralitems")


class GameState:
    """Extended game state that holds both typed models and the raw payload."""

    def __init__(self, map=None, player=None, hero=None, provider=None, raw_payload=None):
        self._map = map
        self._player = player
        self._hero = hero
        self._provider = provider
        self._raw_payload = raw_payload or {}

    @property
    def map(self) -> Map:
        return self._map

    @property
    def player(self) -> Player:
        return self._player

    @property
    def hero(self) -> Hero:
        return self._hero

    @property
    def provider(self) -> Provider:
        return self._provider

    @property
    def raw_payload(self) -> dict:
        return self._raw_payload

    def has_data(self) -> bool:
        return self._player is not None or self._hero is not None or self._map is not None


class _RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = self.rfile.read(length).decode("utf-8")
        payload = defaultdict(lambda: None, json.loads(body))

        if not self._authenticate(payload):
            logger.info("Connection refused: auth token mismatch")
            self.send_response(401)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            return

        game_state = GameState(
            map=Map(payload) if payload["map"] else None,
            player=Player(payload) if payload["player"] else None,
            hero=Hero(payload) if payload["hero"] else None,
            provider=Provider(payload) if payload["provider"] else None,
            raw_payload=dict(payload),
        )
        self.server.game_state = game_state
        self.server.running = True

        if self.server.on_state is not None:
            try:
                self.server.on_state(game_state)
            except Exception:
                logger.exception("on_state callback failed")

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def _authenticate(self, payload) -> bool:
        if "auth" in payload and "token" in payload["auth"]:
            return payload["auth"]["token"] == self.server.auth_token
        return False

    def log_message(self, format, *args):
        logger.debug("GSI request: %s", args[0] if args else "")


class GSIServer(HTTPServer):
    def __init__(self, address: tuple, token: str, on_state: Callable | None = None):
        super().__init__(address, _RequestHandler)
        self.auth_token = token
        self.game_state = GameState()
        self.running = False
        self.on_state = on_state

    def start(self) -> None:
        thread = Thread(target=self.serve_forever, daemon=True)
        thread.start()
        logger.info("GSI server listening on %s:%d", *self.server_address)
