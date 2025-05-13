import os
import json
import csv
import zipfile
from datetime import datetime, timedelta
from typing import Iterator, Dict, Optional

class Logger:
    def __init__(self, config_path: str):
        """
        Inicjalizuje logger na podstawie pliku JSON.
        :param config_path: Ścieżka do pliku konfiguracyjnego (.json)
        """
        # Wczytaj konfigurację z pliku JSON
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Ustaw parametry z konfiguracji
        self.log_dir = config["log_dir"]
        self.filename_pattern = config["filename_pattern"]
        self.buffer_size = config["buffer_size"]
        self.rotate_every_hours = config["rotate_every_hours"]
        self.max_size_mb = config["max_size_mb"]
        self.rotate_after_lines = config["rotate_after_lines"]
        self.retention_days = config["retention_days"]

        # Utwórz katalogi log_dir/ i log_dir/archive/ jeśli nie istnieją
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(os.path.join(self.log_dir, "archive"), exist_ok=True)

        # Inicjalizacja bufora i innych zmiennych pomocniczych
        self.buffer = []
        self.current_file = None
        self.current_lines = 0
        self.current_file_start_time = None

    def start(self) -> None:
        now = datetime.now()
        filename = now.strftime(self.filename_pattern)
        self.current_file_path = os.path.join(self.log_dir, filename)
        file_exists = os.path.exists(self.current_file_path)

        # Otwórz plik i wczytaj liczbę istniejących linii
        if file_exists:
            with open(self.current_file_path, 'r', encoding='utf-8') as f:
                self.current_lines = sum(1 for line in f) - 1  # -1 dla nagłówka
        else:
            self.current_lines = 0

        self.current_file = open(self.current_file_path, mode='a', newline='', encoding='utf-8')
        self.csv_writer = csv.writer(self.current_file)

        if not file_exists or os.stat(self.current_file_path).st_size == 0:
            self.csv_writer.writerow(['TIMESTAMP', 'SENSOR_ID', 'VALUE', 'UNIT'])
            self.current_file.flush()

        self.current_file_start_time = now
        #print(f"[DEBUG] Start loggera: current_lines={self.current_lines}")  # Dodaj dla debugowania

    def stop(self) -> None:
        """
        Wymusza zapis bufora i zamyka bieżący plik.
        """
        # Zapisz wszystkie dane z bufora
        if self.buffer:
            self.csv_writer.writerows(self.buffer)
            self.current_file.flush()
            self.buffer.clear()
        # Zamknij plik
        if self.current_file:
            self.current_file.write('----- KONIEC SESJI -----\n')
            self.current_file.flush()
            self.current_file.close()
            self.current_file = None

    def log_reading(self, sensor_id: str, timestamp: datetime, value: float, unit: str) -> None:
        """
        Dodaje wpis do bufora i ewentualnie wykonuje rotację pliku.
        """
        # Dodaj wpis do bufora
        self.buffer.append([timestamp.isoformat(), sensor_id, value, unit])

        # Jeśli przekroczono buffer_size, wykonaj flush do pliku
        if len(self.buffer) >= self.buffer_size:
            lines_to_add = len(self.buffer)
            self.csv_writer.writerows(self.buffer)
            self.current_file.flush()
            self.current_lines += lines_to_add
            self.buffer.clear()


        # Sprawdź potrzebę rotacji pliku
        if self._should_rotate():
            print("[DEBUG] Rotacja!")
            self._rotate()

    def read_logs(self, start: datetime, end: datetime, sensor_id: Optional[str] = None) -> Iterator[Dict]:
        """
        Pobiera wpisy z logów zadanego zakresu i opcjonalnie konkretnego czujnika.
        """

        def parse_line(row):
            return {
                "timestamp": datetime.fromisoformat(row[0]),
                "sensor_id": row[1],
                "value": float(row[2]),
                "unit": row[3]
            }

        # Przeglądaj pliki CSV w log_dir
        for filename in os.listdir(self.log_dir):
            if filename.endswith('.csv'):
                file_path = os.path.join(self.log_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader, None)  # pomiń nagłówek
                    for row in reader:
                        if not row or 'KONIEC SESJI' in row[0]:
                            continue
                        entry = parse_line(row)
                        if start <= entry["timestamp"] <= end:
                            if sensor_id is None or entry["sensor_id"] == sensor_id:
                                yield entry

        # Przeglądaj archiwa ZIP w log_dir/archive
        archive_dir = os.path.join(self.log_dir, 'archive')
        if os.path.exists(archive_dir):
            for archive_name in os.listdir(archive_dir):
                if archive_name.endswith('.zip'):
                    archive_path = os.path.join(archive_dir, archive_name)
                    with zipfile.ZipFile(archive_path, 'r') as zipf:
                        for zipinfo in zipf.infolist():
                            if zipinfo.filename.endswith('.csv'):
                                with zipf.open(zipinfo) as f:
                                    reader = csv.reader((line.decode('utf-8') for line in f))
                                    next(reader, None)  # pomiń nagłówek
                                    for row in reader:
                                        if not row or 'KONIEC SESJI' in row[0]:
                                            continue
                                        entry = parse_line(row)
                                        if start <= entry["timestamp"] <= end:
                                            if sensor_id is None or entry["sensor_id"] == sensor_id:
                                                yield entry

    def _should_rotate(self):
        #print(f"[DEBUG] Sprawdzam rotację: current_lines={self.current_lines}, rotate_after_lines={self.rotate_after_lines}")
        # Rotacja po czasie
        if self.current_file_start_time and (
                datetime.now() - self.current_file_start_time >= timedelta(hours=self.rotate_every_hours)):
            return True
        # Rotacja po rozmiarze pliku
        if self.current_file_path and os.path.exists(self.current_file_path):
             size_mb = os.path.getsize(self.current_file_path) / (1024 * 1024)
             if size_mb >= self.max_size_mb:
                     return True
        # Rotacja po liczbie linii
        if self.current_lines >= self.rotate_after_lines:
            return True
        return False

    def _rotate(self):
        self.stop()
        self._archive()
        self._clean_old_archives()
        self.start()

    def _get_unique_archive_name(self, base_name: str) -> str:
        """Generuje unikalną nazwę archiwum ZIP z numeracją przyrostową."""
        base_name = os.path.splitext(base_name)[0]
        archive_name = f"{base_name}.zip"
        counter = 1
        archive_dir = os.path.join(self.log_dir, "archive")

        while os.path.exists(os.path.join(archive_dir, archive_name)):
            archive_name = f"{base_name}({counter}).zip"
            counter += 1

        return archive_name

    def _archive(self):
        if not self.current_file_path or not os.path.exists(self.current_file_path):
            return

        base_filename = os.path.basename(self.current_file_path)
        archive_name = self._get_unique_archive_name(base_filename)
        archive_path = os.path.join(self.log_dir, "archive", archive_name)

        print(f"[DEBUG] Tworzenie archiwum: {archive_path}")

        # Utwórz archiwum ZIP bez przenoszenia pliku CSV
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(self.current_file_path, arcname=base_filename)

        print(f"[DEBUG] Usuwanie starego pliku CSV: {self.current_file_path}")
        os.remove(self.current_file_path)

    def _clean_old_archives(self):
        archive_dir = os.path.join(self.log_dir, "archive")
        now = datetime.now()
        for filename in os.listdir(archive_dir):
            if filename.endswith(".zip"):
                file_path = os.path.join(archive_dir, filename)
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                if now - file_mtime > timedelta(days=self.retention_days):
                    os.remove(file_path)

