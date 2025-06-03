import socket
from datetime import datetime
import json
import time
from typing import Optional
from .config import load_config

class NetworkClient:
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, timeout: float = 5.0, retries: int = 3, logger=None, config_path: str = "config.yaml"):
        """Inicjalizuje klienta sieciowego."""
        if host is None or port is None:
            config = load_config(config_path)
            self.host = config["host"]
            self.port = config["port"]
            self.timeout = config["timeout"]
            self.retries = config["retries"]
        else:
            self.host = host
            self.port = port
            self.timeout = timeout
            self.retries = retries

        self.socket: Optional[socket.socket] = None
        self.logger = logger
        self.keep_alive = False

    def connect(self) -> None:
        """Nawiazuje połączenie z serwerem."""
        if self.socket:
            if self.logger:
                self.logger.info("Połączenie już istnieje.")
            return

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)

        try:
            if self.logger:
                self.logger.info(f"Łączenie z {self.host}:{self.port}...")
            self.socket.connect((self.host, self.port))
            if self.logger:
                self.logger.info("Połączenie nawiązane.")
        except (socket.timeout, ConnectionRefusedError) as e:
            if self.logger:
                self.logger.error(f"Błąd połączenia: {str(e)}")
            raise

    def send(self, data: dict) -> bool:
        """Wysyła dane, utrzymując połączenie jeśli keep_alive=True."""
        attempt = 0
        success = False

        while attempt < self.retries and not success:
            try:
                # Nawiąż połączenie tylko jeśli nie istnieje
                if not self.socket:
                    self.connect()

                payload = self._serialize(data)

                # Logowanie próby
                if self.logger:
                    self.logger.log_reading(
                        sensor_id="NETWORK",
                        timestamp=datetime.now(),
                        value=0,
                        unit="STATUS",
                        additional_info={"level": "INFO", "message": f"Wysyłanie pakietu (próba {attempt + 1}): {data}"}
                    )

                # Wyślij i odbierz ACK
                self.socket.sendall(payload)
                ack = self._receive_ack()

                if ack.get("status") == "ok":
                    success = True
                    if self.logger:
                        self.logger.log_reading(
                            sensor_id="NETWORK",
                            timestamp=datetime.now(),
                            value=0,
                            unit="STATUS",
                            additional_info={"level": "INFO", "message": "ACK otrzymany"}
                        )

            except (ConnectionError, TimeoutError, json.JSONDecodeError) as e:
                # Zamknij połączenie przy błędzie i pozwól na ponowne połączenie
                self.close()
                if self.logger:
                    self.logger.log_reading(
                        sensor_id="NETWORK",
                        timestamp=datetime.now(),
                        value=0,
                        unit="ERROR",
                        additional_info={"level": "ERROR", "message": f"Błąd (próba {attempt + 1}): {str(e)}"}
                    )
                attempt += 1
                time.sleep(0.5)

            finally:
                if not self.keep_alive:
                    self.close()

        if not success and self.logger:
            self.logger.log_reading(
                sensor_id="NETWORK",
                timestamp=datetime.now(),
                value=0,
                unit="ERROR",
                additional_info={"level": "ERROR", "message": "Wyczerpano limit prób"}
            )
        return success

    def _receive_ack(self) -> dict:
        """Odbiera i parsuje ACK z timeoutem."""
        self.socket.settimeout(self.timeout)
        ack_buffer = b""

        # Czekaj na kompletny ACK (do \n)
        while b"\n" not in ack_buffer:
            data = self.socket.recv(1024)
            if not data:
                raise ConnectionError("Serwer zamknął połączenie")
            ack_buffer += data

        return json.loads(ack_buffer.decode().split("\n")[0])

    def close(self) -> None:
        """Zamyka połączenie."""
        if self.socket:
            try:
                self.socket.close()
                if self.logger:
                    self.logger.info("Połączenie zamknięte.")
            except OSError as e:
                if self.logger:
                    self.logger.error(f"Błąd przy zamykaniu: {str(e)}")
            finally:
                self.socket = None

    # Metody pomocnicze:
    def _serialize(self, data: dict) -> bytes:
        return (json.dumps(data) + "\n").encode('utf-8')

    def _deserialize(self, raw: bytes) -> dict:
        return json.loads(raw.decode('utf-8'))