from Sensors.Sensor import Sensor
import random

class AirQualitySensor(Sensor):
    def __init__(self, sensor_id, name="Air Quality Sensor", unit="AQI", min_value=0, max_value=500, frequency=1):
        super().__init__(sensor_id, name, unit, min_value, max_value, frequency)

        # Początkowa jakość powietrza na początku symulacji (w środku zakresu)
        if self.last_value is None:
            self.last_value = random.uniform(self.min_value, self.max_value)

    def read_value(self):
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony.")

        new_value = self.last_value
        shock = 0

        # Symulacja nagłego wzrostu lub spadku zanieczyszczeń (np. z powodu wydarzeń, burz itp.)
        if random.random() < 0.05:  # 5% szansa na nagły skok/zstąpienie
            shock = random.uniform(-50, 50)  # Nagły wzrost/spadek o max ±50
            # Jeśli skok jest mniejszy niż 25, ustawiamy go na 25
            if abs(shock) < 20:
                shock = 20 * (1 if shock > 0 else -1)
            new_value += shock
            print(f"Shock: {shock:.2f} {self.unit}")

        # Ograniczamy do zakresu 0 - 500 po dodaniu ewentualnego skoku
        new_value = max(self.min_value, min(self.max_value, new_value))

        # Symulacja normalnej zmiany jakości powietrza tylko, jeśli nie było shocku
        if shock == 0:  # Jeśli nie było żadnego shocku, to możemy dodać fluktuację
            fluctuation = random.uniform(-10, 10)  # Zmiana o max ±10 AQI
            new_value += fluctuation

        # Ograniczamy do zakresu 0 - 500 po normalnej zmianie
        new_value = max(self.min_value, min(self.max_value, new_value))

        self.last_value = round(new_value, 2)
        return self.last_value
