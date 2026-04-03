import threading

try:
    import obd
except:
    obd = None


class OBDService:
    def __init__(self):
        self.connection = None
        self.connected = False
        self.speed = 0
        self.rpm = 0
        self.running = False

    def connect(self, port=None):
        if not obd:
            print("python-OBD not installed")
            return False

        try:
            self.connection = obd.OBD(port) if port else obd.OBD()

            if self.connection.is_connected():
                self.connected = True
                self.start()
                print("OBD Connected")
                return True
        except Exception as e:
            print("OBD error:", e)

        return False

    def disconnect(self):
        self.running = False
        if self.connection:
            self.connection.close()
        self.connected = False

    def start(self):
        self.running = True
        threading.Thread(target=self.update_loop, daemon=True).start()

    def update_loop(self):
        while self.running:
            try:
                speed = self.connection.query(obd.commands.SPEED)
                rpm = self.connection.query(obd.commands.RPM)

                if not speed.is_null():
                    self.speed = speed.value.to("km/h").magnitude

                if not rpm.is_null():
                    self.rpm = rpm.value.magnitude
            except:
                pass


# Global instance
obd_service = OBDService()