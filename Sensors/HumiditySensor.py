from Sensors.Sensor import Sensor
import random

class HumiditySensor(Sensor):
    def __init__(self, sensor_id, linked_temperature_sensor, name="Humidity Sensor", unit="%", min_value=0, max_value=100, frequency=1):
        super().__init__(sensor_id, name, unit, min_value, max_value, frequency)
        self.linked_temperature_sensor = linked_temperature_sensor  # powiązany czujnik temperatury
        self.last_temp = self.linked_temperature_sensor.get_last_value()

        # Startowa wilgotność na początku symulacji
        self.last_value = round(random.uniform(40, 80), 2)

    def read_value(self):
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony.")

        current_temp = self.linked_temperature_sensor.get_last_value()

        temp_difference = current_temp - self.last_temp

        if temp_difference > 0.5:
            # Temperatura rośnie → wilgotność lekko spada
            fluctuation = random.uniform(-2, -0.5)
        elif temp_difference < -0.5:
            # Temperatura spada → wilgotność lekko rośnie
            fluctuation = random.uniform(0.5, 2)
        else:
            # Mała zmiana temperatury → mała losowa zmiana wilgotności
            fluctuation = random.uniform(-0.5, 0.5)

        new_value = self.last_value + fluctuation

        # Ograniczenie wilgotności do zakresu 0%–100%
        new_value = max(self.min_value, min(self.max_value, new_value))

        self.last_value = round(new_value, 2)

        # Zapisz aktualną temperaturę na przyszłość
        self.last_temp = current_temp

        return self.last_value
