from Sensors.Sensor import Sensor
import random

class TemperatureSensor(Sensor):
    def __init__(self, sensor_id, name="Temperature Sensor", unit="°C", min_value=-20, max_value=50, frequency=1, time_of_day=None):
        super().__init__(sensor_id, name, unit, min_value, max_value, frequency)
        self.time_of_day = time_of_day

        # Pora dnia będzie już dostępna przez self.get_time_of_day()
        if self.time_of_day == "day":
            self.day_min = 15
            self.day_max = 35
        else:
            self.night_min = -5
            self.night_max = 20

        # Startowa temperatura na początku symulacji (w środku zakresu)
        if self.last_value is None:
            if self.time_of_day == "day":
                self.last_value = random.uniform(self.day_min, self.day_max)
            else:
                self.last_value = random.uniform(self.night_min, self.night_max)

        print(f"Symulacja dla: {self.time_of_day.upper()}")

    def read_value(self):
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony.")

        fluctuation = random.uniform(-2, 2)  # zmiana o max ±2 stopnie

        new_value = self.last_value + fluctuation

        # Ograniczamy do zakresu dla dnia lub nocy
        if self.time_of_day == "day":
            new_value = max(self.day_min, min(self.day_max, new_value))
        else:
            new_value = max(self.night_min, min(self.night_max, new_value))

        self.last_value = round(new_value, 2)
        self._notify_callbacks(self.last_value)
        return self.last_value
