import math

from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty


class RouteService(EventDispatcher):
    active = BooleanProperty(False)
    destination_name = StringProperty("")
    next_instruction = StringProperty("No route selected")
    distance_to_next_m = NumericProperty(0)
    route_points = ListProperty([])
    maneuvers = ListProperty([])
    maneuver_index = NumericProperty(0)

    def set_route(self, route_points, maneuvers, destination_name="Destination"):
        self.route_points = route_points
        self.maneuvers = maneuvers
        self.destination_name = destination_name
        self.maneuver_index = 0
        self.active = bool(route_points and maneuvers)
        self.distance_to_next_m = 0
        self._refresh_next_instruction()

    def clear(self):
        self.active = False
        self.destination_name = ""
        self.next_instruction = "No route selected"
        self.distance_to_next_m = 0
        self.route_points = []
        self.maneuvers = []
        self.maneuver_index = 0

    def update_position(self, lat, lon):
        if not self.active or self.maneuver_index >= len(self.maneuvers):
            return

        current = self.maneuvers[self.maneuver_index]
        distance = self._distance_m(lat, lon, current["lat"], current["lon"])
        self.distance_to_next_m = int(distance)

        if distance <= 35:
            self.maneuver_index += 1
            if self.maneuver_index >= len(self.maneuvers):
                self.next_instruction = "Arrived"
                self.distance_to_next_m = 0
                self.active = False
                return
            self._refresh_next_instruction()

    def load_demo_route(self, origin_lat, origin_lon):
        route_points = [
            (origin_lat, origin_lon),
            (origin_lat + 0.0010, origin_lon + 0.0018),
            (origin_lat + 0.0010, origin_lon + 0.0039),
            (origin_lat + 0.0002, origin_lon + 0.0051),
            (origin_lat - 0.0009, origin_lon + 0.0051),
        ]
        maneuvers = [
            {"instruction": "Head east", "lat": route_points[1][0], "lon": route_points[1][1]},
            {"instruction": "Keep right", "lat": route_points[2][0], "lon": route_points[2][1]},
            {"instruction": "Turn right", "lat": route_points[3][0], "lon": route_points[3][1]},
            {"instruction": "Destination ahead", "lat": route_points[4][0], "lon": route_points[4][1]},
        ]
        self.set_route(route_points, maneuvers, destination_name="Demo route")

    def _refresh_next_instruction(self):
        if not self.active or self.maneuver_index >= len(self.maneuvers):
            self.next_instruction = "No route selected"
            self.distance_to_next_m = 0
            return
        self.next_instruction = self.maneuvers[self.maneuver_index]["instruction"]

    @staticmethod
    def _distance_m(lat1, lon1, lat2, lon2):
        earth_radius = 6371000
        p1 = math.radians(lat1)
        p2 = math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)

        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * earth_radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


route_service = RouteService()
