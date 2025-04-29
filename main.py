from Sensors.LightSensor import LightSensor
from Sensors.TemperatureSensor import TemperatureSensor
from Sensors.HumiditySensor import HumiditySensor
from Sensors.AirQualitySensor import AirQualitySensor  # Dodanie importu
import time
import random

def main():
    time_of_day = random.choice(["day", "night"])

    # Inicjalizacja czujników
    temp_sensor = TemperatureSensor(sensor_id="T001", time_of_day=time_of_day)
    humidity_sensor = HumiditySensor(sensor_id="H001", linked_temperature_sensor=temp_sensor)
    light_sensor = LightSensor(sensor_id="L001", time_of_day=time_of_day)
    air_quality_sensor = AirQualitySensor(sensor_id="AQ001")  # Inicjalizacja czujnika jakości powietrza

    print("Symulacja odczytów czujników:")
    for _ in range(10):
        temp = temp_sensor.read_value()
        hum = humidity_sensor.read_value()
        light = light_sensor.read_value()
        air_quality = air_quality_sensor.read_value()  # Odczyt wartości z czujnika jakości powietrza
        print(f"{temp_sensor.name}: {temp:.2f} {temp_sensor.unit} | {humidity_sensor.name}: {hum:.2f} {humidity_sensor.unit}")
        print(f"{light_sensor.name}: {light:.2f} {light_sensor.unit} | {air_quality_sensor.name}: {air_quality:.2f} {air_quality_sensor.unit}")
        time.sleep(temp_sensor.frequency)

if __name__ == "__main__":
    main()
