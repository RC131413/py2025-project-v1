# server/server.py
import socket
import json
import yaml
import sys
from threading import Thread


class NetworkServer:
    def __init__(self, port: int = None, config_path: str = "../config.yaml"):
        """Inicjalizuje serwer na wskazanym porcie."""
        if port is None:
            config = self._load_config(config_path)
            # Szukaj portu w sekcjach 'server' lub 'network'
            self.port = (
                    config.get("server", {}).get("port")
                    or config.get("network", {}).get("port")
            )
            if not self.port:
                raise ValueError("Brak portu w pliku config.yaml!")
        else:
            self.port = port

        self.host = "0.0.0.0"
        self.running = False
        self.server_socket = None
        self.on_data_received = None

    def _load_config(self, config_path: str) -> dict:
        """Wczytuje konfigurację z pliku YAML."""
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                return config
        except FileNotFoundError:
            return {}

    def start(self) -> None:
        """Uruchamia nasłuchiwanie połączeń i obsługę klientów."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        print(f"Serwer nasłuchuje na {self.host}:{self.port}")

        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"Połączono z {addr}")
                client_thread = Thread(
                    target=self._handle_client,
                    args=(client_socket,)
                )
                client_thread.start()
            except OSError:
                break

    def _handle_client(self, client_socket) -> None:
        """Przetwarzaj wszystkie wiadomości w jednym połączeniu."""
        try:
            client_socket.settimeout(30.0)
            buffer = b""

            while True:
                # Odbierz dane partiami (do 4096 bajtów)
                data = client_socket.recv(4096)
                if not data:
                    break  # Klient zamknął połączenie

                buffer += data

                # Przetwarzaj wszystkie kompletne wiadomości (rozdzielone \n)
                while b"\n" in buffer:
                    message_part, buffer = buffer.split(b"\n", 1)
                    try:
                        decoded = message_part.decode().strip()
                        if not decoded:
                            continue  # Pomiń puste linie

                        data = json.loads(decoded)
                        self._print_data(data)

                        if self.on_data_received and callable(self.on_data_received):
                            self.on_data_received(data)

                        # Wyślij ACK
                        ack = json.dumps({"status": "ok"}) + "\n"
                        client_socket.sendall(ack.encode())

                    except json.JSONDecodeError as e:
                        print(f"Błąd parsowania JSON: {e}\nDane: {decoded}", file=sys.stderr)
                        client_socket.sendall(b"ERROR\n")

                    except Exception as e:
                        print(f"Inny błąd: {str(e)}", file=sys.stderr)
                        break

        except socket.timeout:
            print("Timeout połączenia.", file=sys.stderr)
        except Exception as e:
            print(f"Błąd: {str(e)}", file=sys.stderr)
        finally:
            client_socket.close()
            print("Połączenie z klientem zamknięte.")

    def _print_data(self, data: dict) -> None:
        """Wyświetla dane w czytelnej formie."""
        print("\n--- Odebrane dane ---")
        for key, value in data.items():
            print(f"{key.upper():<15}: {value}")
        print("---------------------\n")

    def stop(self) -> None:
        """Zatrzymuje serwer."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()

if __name__ == "__main__":
    server = NetworkServer()
    server.start()