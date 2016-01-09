import pyodbc
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import math


class DataManager:
    def __init__(self):

        self.now = datetime.now()
        self.conn = self.conn = pyodbc.connect('DRIVER={SQL Server};'
                                               'SERVER=ZIRSYSPRO;'
                                               'DATABASE=MAINTDATA;'
                                               'Trusted_Connection=yes')
        self.prod_lists = self.sql_data_lists('prs457_good_count_jnl',
                                              *self.current_shift())

        self.defect_lists = self.sql_data_lists('prs457_defect_code_jnl',
                                                *self.current_shift())

        # Production constants.
        self.nameplate = 23 # seconds per cycle, ideal/nominal.
        self.break_time = 1 # hour per shift
        self.hours_per_shift = 8

    def current_shift(self):
        self.now = datetime.now()
        hour = self.now.hour
        assert 0 <= hour <= 23, "hour out of range for current_shift method."
        if 7 <= hour <= 14:
            start_time = self.now.replace(hour=7, minute=0, second=0)
            end_time = self.now.replace(hour=14, minute=59, second=59)
        elif 15 <= hour <= 22:
            start_time = self.now.replace(hour=15, minute=0, second=0)
            end_time = self.now.replace(hour=22, minute=59, second=59)
        elif hour == 23:
            tomorrow = self.now + timedelta(days=1)
            start_time = self.now.replace(hour=23, minute=0, second=0)
            end_time = tomorrow.replace(hour=6, minute=59, second=59)
        elif 0 <= hour <= 6:
            yesterday = self.now - timedelta(days=-1)
            start_time = yesterday.replace(hour=23, minute=0, second=0)
            end_time = self.now.replace(hour=6, minute=59, second=59)
        return start_time, end_time

    def sql_data_lists(self, table, start_time, end_time):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM {0} "
                       "WHERE (submit_datetime > '{1}' "
                       "AND submit_datetime < '{2}')"
                       .format(table,
                               start_time.strftime('%Y-%m-%d %H:%M:%S'),
                               end_time.strftime('%Y-%m-%d %H:%M:%S')))
        data = cursor.fetchall()
        array = np.array(data)
        column_lists = array.transpose().tolist()
        try:
            column_lists.pop(0)
        except IndexError:
            pass
        return column_lists

    def data_reset(self):
        self.prod_lists = self.sql_data_lists('prs457_good_count_jnl',
                                              *self.current_shift())
        self.defect_lists = self.sql_data_lists('prs457_defect_code_jnl',
                                                *self.current_shift())

    @staticmethod
    def set_list_of_lists(length, list_of_lists):
        empty_lol = []
        for idx in range(length):
            empty_lol.append([])
        if (len(list_of_lists) != len(empty_lol)
            or type(list_of_lists) != type(empty_lol)):
            return empty_lol
        else:
            for item in list_of_lists:
                assert type(item) == list, \
                    "list of lists contains non-list item."
            return list_of_lists

    @property
    def prod_rate(self):
        return self._prod_rate

    @prod_rate.setter
    def prod_rate(self, rate):
        if rate <= 23.5:
            self._prod_rate = 23.5
        else:
            self._prod_rate = rate
        return self._prod_rate

    @property
    def prod_lists(self):
        return self._prod_lists

    @prod_lists.setter
    def prod_lists(self, list_of_lists):
        self._prod_lists = self.set_list_of_lists(8, list_of_lists)

    @property
    def defect_lists(self):
        return self._defect_lists

    @defect_lists.setter
    def defect_lists(self, list_of_lists):
        self._defect_lists = self.set_list_of_lists(7, list_of_lists)

    def prod_append(self, prod_list):
        assert len(prod_list) == 6, "prod_list is wrong size for this method."
        for value in prod_list:
            assert 0 <= value <= 1, "list values are not 0 or 1, as expected"
        good_cursor = self.conn.cursor()
        good_submit = list(prod_list)
        good_submit.extend([sum(prod_list), self.now])
        good_cursor.execute("INSERT INTO prs457_good_count_jnl(station_one, "
                            "station_two, station_three, station_four, "
                            "station_five, station_six, total_good, "
                            "submit_datetime) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            *good_submit)
        good_cursor.commit()
        good_cursor.close()
        index = 0
        for data_list in self._prod_lists:
            data_list.append(good_submit[index])
            index += 1

    def defect_append(self, defect_list):
        assert len(defect_list) == 6, \
            "prod_list is wrong size for this method."
        for value in defect_list:
            assert 0 <= value <= 16, \
                "defect value is outside of expected range."
        defect_cursor = self.conn.cursor()
        defect_submit = list(defect_list)
        defect_submit.append(self.now)
        defect_cursor.execute("INSERT INTO prs457_defect_code_jnl(station_one, "
                              "station_two, station_three, station_four, "
                              "station_five, station_six, submit_datetime) "
                              "VALUES (?, ?, ?, ?, ?, ?, ?)",
                              *defect_submit)
        defect_cursor.commit()
        defect_cursor.close()
        index = 0
        for data_list in self._defect_lists:
            data_list.append(defect_submit[index])
            index += 1

    def top_three_defect(self, station):
        assert 1 <= station <= 6, "Station does not exist."
        defect_data = self.defect_lists[station-1]
        defect_count = pd.Series(defect_data).value_counts()
        try:
            defect_count.pop(0)
        except KeyError:
            pass
        return defect_count.index.tolist()[:3], defect_count.tolist()[:3]

    def expand_average_prod(self, station):
        assert 1 <= station <= 6, "Station does not exist."
        prod_data = self.prod_lists[station-1]
        prod_expand_avg = pd.expanding_mean(pd.Series(prod_data))
        return self.prod_lists[7], prod_expand_avg.tolist()

    def station_sum_prod(self, station):
        station_sum = sum(self.prod_lists[station-1])
        return station_sum

    def press_sum_prod(self):
        prod_list = []
        for station in range(1, 7):
            prod_list.append(self.station_sum_prod(station))

        actual_prod = sum(prod_list)
        return actual_prod

    def press_cycles(self):
        cycles = len(self.prod_lists[0])
        return cycles

    def percent_production(self):
        prod_list = []
        for station in range(1, 7):
            prod_list.append(self.station_sum_prod(station))
        percent_prod_list = []
        if sum(prod_list) == 0:
            return [0, 0, 0, 0, 0, 0]
        else:
            for prod in prod_list:
                percent_prod_list.append(prod/sum(prod_list))
            return percent_prod_list

    def production_summary(self, actual_rate):
        MIN_PER_HR = 60
        SEC_PER_MIN = 60
        PCS_PER_CYCLE = 6

        nominal_production = (self.hours_per_shift * MIN_PER_HR * SEC_PER_MIN /
                              self.nameplate) * PCS_PER_CYCLE

        nom_prod_w_breaks = (nominal_production * (self.hours_per_shift -
                            self.break_time) / self.hours_per_shift)

        ideal_actual_prod = nom_prod_w_breaks * self.nameplate / actual_rate

        actual_prod_w_reject = self.press_cycles() * 6

        actual_prod = self.press_sum_prod()

        return (math.floor(nominal_production), math.floor(nom_prod_w_breaks),
                math.floor(ideal_actual_prod), actual_prod_w_reject,
                actual_prod)



if __name__ == '__main__':
    data = DataManager()
    print(data.defect_lists)
    print(data.top_three_defect(1))
    print(data.top_three_defect(2))
    print(data.top_three_defect(3))
    print(data.top_three_defect(4))
    print(data.top_three_defect(5))
    print(data.top_three_defect(6))

    print(data.expand_average_prod(1), data.expand_average_prod(2))
    print(data.expand_average_prod(3))
    print(data.expand_average_prod(4))
    print(data.expand_average_prod(5))
    print(data.expand_average_prod(6))
    print(data.production_summary(26))