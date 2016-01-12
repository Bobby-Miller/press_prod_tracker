from pycomm.ab_comm.slc import Driver as SlcDriver
from datetime import datetime, timedelta
import sqlite3
import time

conn = sqlite3.connect('signal.sqlite',
                       detect_types=sqlite3.PARSE_DECLTYPES)
cursor = conn.cursor()

def table_create(cursor, table):
    try:
        cursor.execute("CREATE TABLE {0}(ID INT PRIMARY KEY NOT NULL, "
                       "signal_diff REAL, "
                       "sig_datetime timestamp)".format(table))
    except sqlite3.OperationalError:
        pass

def initialize_signal(signal):
    c = conn.cursor()
    c.execute("select * FROM conveyor_signal WHERE ID={}".format(signal))
    signal_check = c.fetchall()
    print('Reading from press. DO NOT TOUCH! Thanks!')
    if signal_check == []:
        now = datetime.now()
        c = conn.cursor()
        c.execute("INSERT INTO conveyor_signal (ID, signal_diff, sig_datetime)"
                  " values (?, 0, ?)", (signal, now))


def update_signal(cursor, table, values):
    cursor.execute("UPDATE {} SET ID=?, signal_diff=?, sig_datetime=? "
                   "WHERE ID=?".format(table), values)
    conn.commit()

table_create(cursor, 'conveyor_signal')
initialize_signal(0)
initialize_signal(1)

def connect_and_read():
    try:
        c = SlcDriver()
        if c.open('128.1.0.123'):
            print "Connection made."
            signal_on = None
            signal_off = None
            now = None
            signal_on_time = None
            signal_off_time = None
            conveyor_time = timedelta(0, 0, 0)
            cycle_time = timedelta(0, 0, 0)
            while True:
                start_time = datetime.now()
                tag = c.read_tag('B3:0/2')
                if tag and signal_off:
                    signal_off = False
                    if signal_on_time is None:
                        signal_on_time = datetime.now()
                    else:
                        signal_on_time = datetime.now()
                        conveyor_time = signal_on_time - signal_off_time
                    update_signal(cursor, 'conveyor_signal',
                                  (1, conveyor_time.total_seconds(),
                                   signal_on_time, 1))
                elif not tag and signal_on:
                    signal_on = False
                    if signal_on_time is None:
                        signal_off_time = datetime.now()
                    else:
                        signal_off_time = datetime.now()
                        cycle_time = signal_off_time - signal_on_time
                    update_signal(cursor, 'conveyor_signal',
                                  (0, cycle_time.total_seconds(),
                                   signal_off_time, 0))
                elif tag:
                    signal_on = True
                elif not tag:
                    signal_off = True
    except:
        print "Lost connection. Attempting to reconnect..."
        time.sleep(3)
        connect_and_read()

connect_and_read()
