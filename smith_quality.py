from PyQt4.uic import loadUiType
from PyQt4 import QtGui, QtCore
import pyodbc
from datetime import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as \
    FigureCanvas
import smith_data as sd
import signal_reader as sr
from matplotlib.pyplot import style
import math
from subprocess import Popen

style.use('bmh')

Ui_main, Qmain = loadUiType('ui/main.ui')


class Main(Qmain, Ui_main):
    def __init__(self):
        self.now = datetime.now() # Current time
        # Database connection.
        self.conn = pyodbc.connect('DRIVER={SQL Server};'
                                   'SERVER=ZIRSYSPRO;'
                                   'DATABASE=MAINTDATA;'
                                   'Trusted_Connection=yes')

        self.data = sd.DataManager()    # Separate class created to manage the
        # data aspect of the application.

        self.signal = sr.SignalReader()

        self.cycle_time = self.signal.update_cycle()

        super(Main, self).__init__()  # Inherit parent methods...I think?
        self.setupUi(self)  # I don't know what this is.

        self.widget_dicts()  # initialize widget_dicts method (a static method
        # used to organize buttons outside of the init method - a cleaner
        # approach.)

        self.button_methods()  # Initialize button method - method holds all
        # button actions for the UI. Again, defined outside of init for
        # cleanliness.

        self.defect_list = [0, 0, 0, 0, 0, 0]  # defect code per station per
        # cycle.
        self.good_pieces = [1, 1, 1, 1, 1, 1]  # good piece per station per
        # cycle.

        self.startup = False  # Used to denote if under start up conditions
        # (no parts collected).

        self.station_on = {1: True, 2: True, 3: True, 4: True, 5: True,
                           6: True} # Used for station on/off toggles.

        self.update_display()  # Used to run charts and values for the first
        # time.

        self.current_shift = self.data.current_shift()  # Used to determine the
        # current shift and update data accordingly

        self.timer = QtCore.QTimer()  # PyQt timer action signal.
        self.timer.start(500)  # Trigger a signal every second.
        self.timer.timeout.connect(self.cycle_check)  # perform action
        # trigger.

        self.new_entry = self.cycle_time  # New entry is used as a trigger to
        # reset input. Another jumper aspect for program.

        self._want_to_close = False  # True: Can close program with 'X'. False:
        # Can only minimize program

    def cycle_check(self):
        """
        The current event triggered on the timer. Runs the jumper function to
        reset cycle.
        :return: No return
        """
        if self.signal.signal_changed(1):
            self.cycle_time = self.signal.update_cycle()
            self.submit_data()
            self.update_display()
            # Check if shift change, and update list if so.
            if self.current_shift != self.data.current_shift():
                self.current_shift = self.data.current_shift()
                self.data.data_reset()

    def submit_data(self):
        """
        Sends cycle data (production and defect) to the data handling class.
        Resets the cycle count with the reset_count method.
        :return: No return.
        """
        self.data.prod_append(self.good_pieces)
        self.data.defect_append(self.defect_list)

        self.reset_count()

    def reset_count(self):
        """
        Checks for startup and station off conditions, and otherwise resets
        the cycle using the defect_reset function (the same as is applied
        for the nevermind button.)
        :return:
        """
        if self.startup:  # Startup toggle check
            pass
        elif not self.startup:
            for station in range(1, 7):
                if self.station_on[station]: # Station off toggle check.
                    self.defect_reset(station)

    def defect_select(self, station):
        self.stack_dict[station].setCurrentIndex(1)  # Changes index of stacked
        # widget for defect button selection.

    def defect_reset(self, station):
        """
        Resets a station to normal production values. Can be used in middle of
        cycle (nevermind button) or to reset cycle (reset count function).
        :param station: (Int): The press station, 1-6
        :return: No Return
        """
        self.stack_dict[station].setCurrentIndex(0)  # Turn stacked widget
        # back to main screen.
        if self.defect_list[station-1] != 0:
            assert self.good_pieces[station-1] == 0, ("good piece count does "
                                                      "not match defect list")
            # Reset the gray-out of buttons, and un-check them if checked.
            for ignore, button in self.station_dict[station].items():
                button.setEnabled(True)
                button.setChecked(False)
            # Reset cycle values.
            self.defect_list[station-1] = 0
            self.good_pieces[station-1] = 1

    def defect_toggle(self, clicked, code, station):
        """
        The method called when a defect option is selected. Method will grey
        out other buttons, and update the production and value lists
        appropriately.
        :param clicked: (Bool): Button clicked or un-clicked.
        :param code: (Int): Code number of button defect.
        :param station: (Int): Press station 1-6
        :return: No return.
        """
        if clicked:
            self.defect_list[station-1] = code
            self.good_pieces[station-1] = 0
            # Grey-out other group buttons.
            for dict_code, button in self.station_dict[station].items():
                if dict_code != code:
                    button.setEnabled(False)
        else:
            self.defect_list[station-1] = 0
            self.good_pieces[station-1] = 1
            for dict_code, button in self.station_dict[station].items():
                button.setEnabled(True)

    def station_toggle(self, station, clicked):
        """
        Method called for station on/off toggle. Updates prod/defect list, and
        updates the boolean station dict to not reset during cycle reset.
        :param station: (Int): Press station 1-6
        :param clicked: (Bool): Button clicked or un-clicked.
        :return: No Return
        """
        if clicked:
            self.station_toggle_dict[station].setText(
                    'Station {0}\nON'.format(station))
            self.station_defect_dict[station].setEnabled(False)
            self.station_on[station] = False
            self.good_pieces[station-1] = 0
            self.defect_list[station-1] = 15
        else:
            self.station_toggle_dict[station].setText(
                    'Station {0}\nOFF'.format(station))
            self.station_defect_dict[station].setEnabled(True)
            self.station_on[station] = True
            self.good_pieces[station-1] = 1
            self.defect_list[station-1] = 0

    def startup_toggle(self, clicked):
        """
        Method called for startup on/off toggle. Under start up conditions,
        all pieces are counted as defect, and given a defect code (14).
        :param clicked: (Bool): Button clicked or un-clicked.
        :return: No Return
        """
        if clicked:
            self.startup = True
            self.good_pieces = [0, 0, 0, 0, 0, 0]
            self.defect_list = [14, 14, 14, 14, 14, 14]
            for station in range(1, 7):
                self.station_defect_dict[station].setEnabled(False)

        else:
            self.startup = False
            self.good_pieces = [1, 1, 1, 1, 1, 1]
            self.defect_list = [0, 0, 0, 0, 0, 0]
            for station in range(1, 7):
                self.station_defect_dict[station].setEnabled(True)

    def add_mpl(self, plot, layout):
        """
        Helper function for plot updating. I believe this could be a static
        method, but I'm not clear on how to appropriately use static methods
        yet.
        :param plot: (matplotlib figure): Figure to be added to a layout.
        :param layout: (class layout): Layout in which to add the figure.
        :return: No return
        """
        canvas = FigureCanvas(plot)
        layout.addWidget(canvas)
        canvas.draw()

    def clear_layout(self, layout):
        """
        Helper function for plot updating. Clears a layout to allow for update
        replacement.
        :param layout: (class layout): Layout to be cleared.
        :return:  No return.
        """
        while layout.count():
            child = layout.takeAt(0)
            child.widget().deleteLater()

    def update_layout(self, plot, layout):
        """
        Applied the clear_layout and add_mpl functions in sequence to update a
        plot.
        :param plot: (matplotlib figure): Figure to be added to a layout.
        :param layout: (class layout): Layout in which to add the figure.
        :return: No return.
        """
        self.clear_layout(layout)
        self.add_mpl(plot, layout)

    def update_display(self):
        """
        Contains all items to be updated during every refresh. (All graphs,
        and the production value.
        :return: No return.
        """
        Popen('connect.bat', shell=False)
        self.update_layout(self.top_three_plot(1), self.mplvlTopThree_1)
        self.update_layout(self.top_three_plot(2), self.mplvlTopThree_2)
        self.update_layout(self.top_three_plot(3), self.mplvlTopThree_3)
        self.update_layout(self.top_three_plot(4), self.mplvlTopThree_4)
        self.update_layout(self.top_three_plot(5), self.mplvlTopThree_5)
        self.update_layout(self.top_three_plot(6), self.mplvlTopThree_6)

        self.update_layout(self.expanding_average_plot(1), self.mplvlExpAvg_1)
        self.update_layout(self.expanding_average_plot(2), self.mplvlExpAvg_2)
        self.update_layout(self.expanding_average_plot(3), self.mplvlExpAvg_3)
        self.update_layout(self.expanding_average_plot(4), self.mplvlExpAvg_4)
        self.update_layout(self.expanding_average_plot(5), self.mplvlExpAvg_5)
        self.update_layout(self.expanding_average_plot(6), self.mplvlExpAvg_6)

        self.update_layout(self.percent_performance_plot(),
                           self.mplvlProdPercent)

        self.update_layout(self.prod_summary_chart(), self.mplvlProdSum)

        self.prodDisp.setText(str(self.data.press_sum_prod()))
        self.cycleTimeDisp.setText(str(round(self.cycle_time, 1)))


    def top_three_plot(self, station):
        """
        Method for the bar chart displayed for each station. Displays the top
        three defects of each station
        :param station: (Int): Press station 1-6
        :return: matplotlib figure.
        """
        fig = Figure(frameon=False)
        codes, counts = self.data.top_three_defect(station)

        # Order bar chart in a row, based on number of codes.
        x_axis = range(len(counts))

        ax = fig.add_subplot(111)
        ax.bar(x_axis, counts, align='center', color='darkred')

        # Set labels for x axis.
        x_labels = []
        for code in codes:
            x_labels.append(str(code))
        ax.set_xticks(x_axis)
        ax.set_xticklabels(x_labels)

        # Customized y-axis display.
        try:
            high_count = max(counts)
        except ValueError:
            high_count = 0
        y_int = range(4)
        if 1 <= high_count <= 10:
            y_int = range(0, high_count + 2)
        elif 11 <= high_count <= 100:
            y_int = range(0, high_count + 2, math.ceil(high_count/10))
        ax.set_yticks(y_int)

        return fig

    def expanding_average_plot(self, station):
        """
        Method for the line chart displayed on each station. Updates with the
        expanding average over the shift.
        :param station: (Int): Press station 1-6
        :return: matplotlib figure
        """
        fig = Figure(frameon=False)
        dates, average = self.data.expand_average_prod(station)
        ax = fig.add_subplot(111)
        ax.plot(range(len(average)), average, color='red')
        ax.set_ylim(bottom=0)
        ax.get_xaxis().set_visible(False)

        return fig

    def percent_performance_plot(self):
        """
        Method for the bar chart displayed at the top of the application.
        Displays the relative production of each station.
        :return: matplotlib figure.
        """
        fig = Figure(frameon=False)
        fig.subplots_adjust(left=.03, right=.97)
        prod_percents = self.data.percent_production()
        ax = fig.add_subplot(111)
        ax.bar(range(1, 7), prod_percents, align='center', color='darkred')
        ax.set_ylim(bottom=0)
        ax.set_xticks([1, 2, 3, 4, 5, 6])

        return fig

    def prod_summary_chart(self):
        """
        Method for the progress bar displayed at the bottom of the application.
        Displays ideal production, best-case production, actual production, and
        rejects. Tracks throughout shift.
        :return: matplotlib figure.
        """
        fig = Figure(frameon=False)
        prod_data = self.data.production_summary(self.cycle_time)
        ax = fig.add_subplot(111)
        fig.subplots_adjust(top=.75, bottom=.25, right=.95, left=.05)

        ax.barh(0, prod_data[0], facecolor='.6')
        ax.annotate("Ideal: " + str(prod_data[0]), (prod_data[0], .5),
                    xytext=(prod_data[0], -.12), va="top", ha="right",
                    arrowprops=dict(arrowstyle="->"))
        ax.barh(0, prod_data[1], facecolor='.8')
        ax.annotate("Ideal (w/ Breaks): " + str(prod_data[1]),
                    (prod_data[1], .5), xytext=(prod_data[1], .88),
                    va="bottom", ha="right", arrowprops=dict(arrowstyle="->"))
        ax.barh(0, prod_data[2], facecolor='.5')
        ax.annotate("Best Case: " + str(prod_data[2]), (prod_data[2], .5),
                    xytext=(prod_data[2], -.12), va="top", ha="right",
                    arrowprops=dict(arrowstyle="->"))

        ax.barh(0, prod_data[3], facecolor='red')
        try:
            defect_percent = round((prod_data[3] - prod_data[4]) * 100 /
                                   prod_data[3], 1)
        except ZeroDivisionError:
            defect_percent = 0.0
        ax.annotate("Defects: " + str(prod_data[3] - prod_data[4]) + " (" +
                    str(defect_percent) + "%)",
                    (prod_data[3], .5), xytext=(prod_data[3], .88),
                    va="bottom", ha="center", arrowprops=dict(arrowstyle="->"))

        ax.barh(0, prod_data[4], facecolor='darkred')
        try:
            prod_percent = round(prod_data[4] * 100 / prod_data[2], 1)
        except ZeroDivisionError:
            prod_percent = 0.0
        ax.annotate("Shift: " + str(prod_data[4]) + " (" + str(prod_percent) +
                    "%)", (prod_data[4], .5), xytext=(prod_data[4], -.12),
                    va="top", ha="center", arrowprops=dict(arrowstyle="->"))

        ax.set_xlim(left=0, right=prod_data[0])
        ax.axis('off')

        return fig

    def widget_dicts(self):
        # Contains all dicts used in the class, for cleanliness.
        self.stack_dict = {1: self.stackedWidget1, 2: self.stackedWidget2,
                           3: self.stackedWidget3, 4: self.stackedWidget4,
                           5: self.stackedWidget5, 6: self.stackedWidget6,
                           }

        self.defect_dict_1 = {1: self.pushButtonTipChip_1,
                              2: self.pushButtonTipPositive_1,
                              3: self.pushButtonTipNegative_1,
                              4: self.pushButtonTipCupping_1,
                              5: self.pushButtonTipTophat_1,
                              6: self.pushButtonTipUnderfill_1,
                              7: self.pushButtonTipOverfill_1,
                              8: self.pushButtonBaseChip_1,
                              9: self.pushButtonBaseFlash_1,
                              10: self.pushButtonBaseWarp_1,
                              11: self.pushButtonHole_1,
                              12: self.pushButtonCrack_1,
                              13: self.pushButtonPieceDropped_1,
                              }
        self.defect_dict_2 = {1: self.pushButtonTipChip_2,
                              2: self.pushButtonTipPositive_2,
                              3: self.pushButtonTipNegative_2,
                              4: self.pushButtonTipCupping_2,
                              5: self.pushButtonTipTophat_2,
                              6: self.pushButtonTipUnderfill_2,
                              7: self.pushButtonTipOverfill_2,
                              8: self.pushButtonBaseChip_2,
                              9: self.pushButtonBaseFlash_2,
                              10: self.pushButtonBaseWarp_2,
                              11: self.pushButtonHole_2,
                              12: self.pushButtonCrack_2,
                              13: self.pushButtonPieceDropped_2,
                              }
        self.defect_dict_3 = {1: self.pushButtonTipChip_3,
                              2: self.pushButtonTipPositive_3,
                              3: self.pushButtonTipNegative_3,
                              4: self.pushButtonTipCupping_3,
                              5: self.pushButtonTipTophat_3,
                              6: self.pushButtonTipUnderfill_3,
                              7: self.pushButtonTipOverfill_3,
                              8: self.pushButtonBaseChip_3,
                              9: self.pushButtonBaseFlash_3,
                              10: self.pushButtonBaseWarp_3,
                              11: self.pushButtonHole_3,
                              12: self.pushButtonCrack_3,
                              13: self.pushButtonPieceDropped_3,
                              }
        self.defect_dict_4 = {1: self.pushButtonTipChip_4,
                              2: self.pushButtonTipPositive_4,
                              3: self.pushButtonTipNegative_4,
                              4: self.pushButtonTipCupping_4,
                              5: self.pushButtonTipTophat_4,
                              6: self.pushButtonTipUnderfill_4,
                              7: self.pushButtonTipOverfill_4,
                              8: self.pushButtonBaseChip_4,
                              9: self.pushButtonBaseFlash_4,
                              10: self.pushButtonBaseWarp_4,
                              11: self.pushButtonHole_4,
                              12: self.pushButtonCrack_4,
                              13: self.pushButtonPieceDropped_4,
                              }
        self.defect_dict_5 = {1: self.pushButtonTipChip_5,
                              2: self.pushButtonTipPositive_5,
                              3: self.pushButtonTipNegative_5,
                              4: self.pushButtonTipCupping_5,
                              5: self.pushButtonTipTophat_5,
                              6: self.pushButtonTipUnderfill_5,
                              7: self.pushButtonTipOverfill_5,
                              8: self.pushButtonBaseChip_5,
                              9: self.pushButtonBaseFlash_5,
                              10: self.pushButtonBaseWarp_5,
                              11: self.pushButtonHole_5,
                              12: self.pushButtonCrack_5,
                              13: self.pushButtonPieceDropped_5,
                              }
        self.defect_dict_6 = {1: self.pushButtonTipChip_6,
                              2: self.pushButtonTipPositive_6,
                              3: self.pushButtonTipNegative_6,
                              4: self.pushButtonTipCupping_6,
                              5: self.pushButtonTipTophat_6,
                              6: self.pushButtonTipUnderfill_6,
                              7: self.pushButtonTipOverfill_6,
                              8: self.pushButtonBaseChip_6,
                              9: self.pushButtonBaseFlash_6,
                              10: self.pushButtonBaseWarp_6,
                              11: self.pushButtonHole_6,
                              12: self.pushButtonCrack_6,
                              13: self.pushButtonPieceDropped_6,
                              }

        self.station_dict = {1: self.defect_dict_1, 2: self.defect_dict_2,
                             3: self.defect_dict_3, 4: self.defect_dict_4,
                             5: self.defect_dict_5, 6: self.defect_dict_6,
                             }

        self.station_defect_dict = {1: self.pushButtonDefect_1,
                                    2: self.pushButtonDefect_2,
                                    3: self.pushButtonDefect_3,
                                    4: self.pushButtonDefect_4,
                                    5: self.pushButtonDefect_5,
                                    6: self.pushButtonDefect_6,}

        self.station_toggle_dict = {1: self.stationToggle_1,
                                    2: self.stationToggle_2,
                                    3: self.stationToggle_3,
                                    4: self.stationToggle_4,
                                    5: self.stationToggle_5,
                                    6: self.stationToggle_6,}

        self.nvm_dict = {1: self.pushButtonNevermind_1,
                         2: self.pushButtonNevermind_2,
                         3: self.pushButtonNevermind_3,
                         4: self.pushButtonNevermind_4,
                         5: self.pushButtonNevermind_5,
                         6: self.pushButtonNevermind_6,}

    def button_methods(self):
        # contains all button method initiation for the class.

        # Defect Select Button Methods
        for station, button in self.station_defect_dict.items():
            button.clicked.connect(lambda ignore_overload, station=station:
                                   self.defect_select(station))

        # Nevermind Button Methods.
        for station, button in self.nvm_dict.items():
            button.clicked.connect(lambda ignore_overload, station=station:
                                   self.defect_reset(station))

        for station, toggle in self.station_toggle_dict.items():
            toggle.clicked.connect(lambda clicked, station=station:
                                   self.station_toggle(station, clicked))

        # Button method for defect codes.
        for station, defect_dict in self.station_dict.items():
            for value, button in defect_dict.items():
                button.clicked.connect(lambda clicked,
                                       num=value, station=station:
                                       self.defect_toggle(clicked, num,
                                                          station))
        # Button method for startup button
        self.pushButtonStartup.clicked.connect(lambda toggled:
                                               self.startup_toggle(toggled))

        def closeEvent(self, event):
            print("event")
            reply = QtGui.QMessageBox.question(self, 'Message',
                "Are you sure to quit?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)

            if reply == QtGui.QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()

    def closeEvent(self, event):
        """
        Overrides standard close event, to optionally only minimize when
        'closed' (as long as self._want_to_close is false).
        :param event: Close event.
        :return: No return
        """
        if self._want_to_close:
            self.conn.close()
            super(Main, self).closeEvent(event)
        else:
            event.ignore()
            self.setWindowState(QtCore.Qt.WindowMinimized)

if __name__ == '__main__':
    import sys

    app = QtGui.QApplication(sys.argv)
    main = Main()
    main.setWindowIcon(QtGui.QIcon('fypy logo wo Title-mod.ico'))
    main.show()
    sys.exit(app.exec_())
