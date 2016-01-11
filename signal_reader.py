import sqlite3
import datetime


class SignalReader:
    def __init__(self):
        self.conn = sqlite3.connect('C:/smiths_micrologix_data/signal.sqlite',
                                    detect_types=sqlite3.PARSE_DECLTYPES)

        self.last_on_signal = self.read_signal(1)
        self.last_off_signal = self.read_signal(0)
        self.signal_dict = {1: self.last_on_signal, 0: self.last_off_signal}
        self.min_cycle_time = 23  # seconds
        self.max_cycle_time = 36  # seconds
        self.current_cycle = 26

    def read_signal(self, signal):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM conveyor_signal "
                       "WHERE ID={}".format(signal))
        return cursor.fetchone()

    def last_signal_change(self):
        return max(self.read_signal(0)[2], self.read_signal(1)[2])

    def cycle_stopped(self):
        if self.last_signal_change() < \
                (datetime.datetime.now() -
                 datetime.timedelta(seconds=self.max_cycle_time)):
            return True
        else:
            return False

    def cycle_time_ok(self):
        full_cycle = sum((self.read_signal(0)[1], self.read_signal(1)[1]))
        if self.min_cycle_time <= full_cycle <= self.max_cycle_time:
            return True
        else:
            return False

    def signal_changed(self, signal):
        live_signal = self.read_signal(signal)
        if self.signal_dict[signal] == live_signal:
            return False
        else:
            self.signal_dict[signal] = live_signal
            return True

    def update_cycle(self):
        if self.cycle_time_ok() and not self.cycle_stopped():
            self.current_cycle = sum((self.read_signal(0)[1],
                                      self.read_signal(1)[1]))
            return self.current_cycle
        else:
            return self.current_cycle

signal = SignalReader()
new_signal = SignalReader()

