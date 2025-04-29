from Sensors.Sensor import Sensor
import random

class LightSensor(Sensor):
    def __init__(self, sensor_id, name="Light Sensor", unit="lx", min_value=0, max_value=10000, frequency=1, time_of_day=None):
        super().__init__(sensor_id, name, unit, min_value, max_value, frequency)
        self.time_of_day = time_of_day

        if self.time_of_day == "day":
            self.day_min = 200  # Wschód słońca
            self.day_max = 10000  # Pełne słońce w ciągu dnia
        else:
            self.night_min = 0  # Noc, brak światła
            self.night_max = 200  # Trochę sztucznego światła


        if self.last_value is None:
            if self.time_of_day == "day":
                self.last_value = random.uniform(self.day_min, self.day_max)
            else:
                self.last_value = random.uniform(self.night_min, self.night_max)

        print(f"Symulacja dla: {self.time_of_day.upper()}")

    def read_value(self):
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony.")

        fluctuation = random.uniform(-100, 100)  # Fluktuacje w oświetleniu

        new_value = self.last_value + fluctuation

        if self.time_of_day == "day":
            new_value = max(self.day_min, min(self.day_max, new_value))
        else:
            new_value = max(self.night_min, min(self.night_max, new_value))

        self.last_value = round(new_value, 2)
        return self.last_value
