import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict, deque
from server.server import NetworkServer


class ServerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Network Server GUI")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # Stan aplikacji
        self.server = None
        self.server_thread = None
        self.is_running = False
        self.sensor_data = defaultdict(lambda: {
            'last_value': 0.0,
            'unit': '',
            'timestamp': '',
            'history': deque(maxlen=1000)  # Bufor na ostatnie 1000 odczytów
        })

        # Wczytaj konfigurację
        self.config = self.load_config()

        self.setup_ui()
        self.update_sensor_display()

    def setup_ui(self):
        """Tworzy interfejs użytkownika."""
        # Górny panel - kontrola serwera
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(top_frame, text="Port:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value=str(self.config.get('port', 8081)))
        self.port_entry = ttk.Entry(top_frame, textvariable=self.port_var, width=10)
        self.port_entry.pack(side=tk.LEFT, padx=5)

        self.start_btn = ttk.Button(top_frame, text="Start", command=self.start_server)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(top_frame, text="Stop", command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Środkowa część - tabela czujników
        self.setup_sensor_table()

        # Dolny panel - pasek statusu
        self.status_var = tk.StringVar(value="Serwer zatrzymany")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var,
                                    relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_sensor_table(self):
        """Tworzy tabelę czujników."""
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Kolumny tabeli
        columns = ('sensor', 'value', 'unit', 'timestamp', 'avg_1h', 'avg_12h')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)

        self.tree.heading('sensor', text='Sensor')
        self.tree.heading('value', text='Wartość')
        self.tree.heading('unit', text='Jednostka')
        self.tree.heading('timestamp', text='Timestamp')
        self.tree.heading('avg_1h', text='Śr. 1h')
        self.tree.heading('avg_12h', text='Śr. 12h')

        self.tree.column('sensor', width=100)
        self.tree.column('value', width=80)
        self.tree.column('unit', width=80)
        self.tree.column('timestamp', width=150)
        self.tree.column('avg_1h', width=80)
        self.tree.column('avg_12h', width=80)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def start_server(self):
        """Uruchamia serwer w osobnym wątku."""
        try:
            port = int(self.port_var.get())
            self.save_config({'port': port})

            # Utwórz serwer z callbackiem
            self.server = NetworkServer(port=port)
            self.server.on_data_received = self.on_sensor_data_received

            self.server_thread = threading.Thread(target=self.run_server, daemon=True)
            self.server_thread.start()

            self.is_running = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.DISABLED)
            self.status_var.set(f"Listening on port {port}")

        except ValueError:
            messagebox.showerror("Błąd", "Port musi być liczbą")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się uruchomić serwera: {str(e)}")

    def run_server(self):
        """Uruchamia serwer (funkcja dla wątku)."""
        try:
            self.server.start()
        except Exception as e:
            self.root.after(0, lambda: self.show_server_error(str(e)))

    def stop_server(self):
        """Zatrzymuje serwer."""
        if self.server:
            self.server.stop()
            self.is_running = False

        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.port_entry.config(state=tk.NORMAL)
        self.status_var.set("Serwer zatrzymany")

    def on_sensor_data_received(self, data):
        """Callback wywoływany gdy serwer otrzyma dane czujnika."""
        sensor_id = data.get('sensor_id', 'unknown')
        value = float(data.get('value', 0))
        unit = data.get('unit', '')
        timestamp = data.get('timestamp', datetime.now().isoformat())

        # Aktualizuj dane czujnika
        self.sensor_data[sensor_id].update({
            'last_value': value,
            'unit': unit,
            'timestamp': timestamp
        })

        # Dodaj do historii
        self.sensor_data[sensor_id]['history'].append({
            'value': value,
            'timestamp': datetime.fromisoformat(timestamp)
        })

    def calculate_averages(self, sensor_id):
        """Oblicza średnie wartości dla czujnika."""
        history = self.sensor_data[sensor_id]['history']
        now = datetime.now()

        # Średnia z 1 godziny
        hour_ago = now - timedelta(hours=1)
        hour_values = [item['value'] for item in history
                       if item['timestamp'] >= hour_ago]
        avg_1h = sum(hour_values) / len(hour_values) if hour_values else 0

        # Średnia z 12 godzin
        twelve_hours_ago = now - timedelta(hours=12)
        twelve_hour_values = [item['value'] for item in history
                              if item['timestamp'] >= twelve_hours_ago]
        avg_12h = sum(twelve_hour_values) / len(twelve_hour_values) if twelve_hour_values else 0

        return avg_1h, avg_12h

    def update_sensor_display(self):
        """Aktualizuje wyświetlanie tabeli czujników."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Dodaj aktualne dane czujników
        for sensor_id, data in self.sensor_data.items():
            avg_1h, avg_12h = self.calculate_averages(sensor_id)

            self.tree.insert('', tk.END, values=(
                sensor_id,
                f"{data['last_value']:.2f}",
                data['unit'],
                data['timestamp'][:19] if data['timestamp'] else '',  # Tylko data i czas
                f"{avg_1h:.2f}",
                f"{avg_12h:.2f}"
            ))

        # Zaplanuj kolejną aktualizację za 3 sekundy
        self.root.after(3000, self.update_sensor_display)

    def show_server_error(self, error_msg):
        """Pokazuje błąd serwera."""
        messagebox.showerror("Błąd serwera", error_msg)
        self.stop_server()

    def load_config(self):
        """Wczytuje konfigurację z pliku."""
        try:
            if os.path.exists('gui_config.json'):
                with open('gui_config.json', 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {'port': 8081}

    def save_config(self, config):
        """Zapisuje konfigurację do pliku."""
        try:
            with open('gui_config.json', 'w') as f:
                json.dump(config, f)
            self.config.update(config)
        except Exception as e:
            print(f"Nie udało się zapisać konfiguracji: {e}")

    def on_closing(self):
        """Obsługa zamykania aplikacji."""
        if self.is_running:
            self.stop_server()
        self.root.destroy()

    def run(self):
        """Uruchamia aplikację GUI."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
