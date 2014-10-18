#!/usr/bin/python

"""
Simple analysis of KakaoTalk chat export files
"""

from __future__ import division

import sys, os
import dateutil.parser
from dateutil.relativedelta import relativedelta
import datetime
import re
from collections import Counter
import operator

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy

LINE_TYPE_UNCHANGED = 0 # Status unchanged from last line. Usually a continued message.
LINE_TYPE_DATE      = 1 # Line with a single date (new day). Can be ignored.
LINE_TYPE_MESSAGE   = 2 # Line with datetime, sender and message

class Message:
    dt = None
    sender = None
    text = ""

    def __init__(self, dt, sender, text):
        self.dt = dt
        self.sender = sender
        self.text = text

    def add_line(self, text):
        self.text = self.text + "\n" + text

    def count_words(self):
        return len(re.findall(r'\b\w+\b', self.text))

    def __str__(self):
        return "[%s] %s: %s" % (self.dt, self.sender.name, self.text)

class Sender:
    name = ""
    count = Counter(messages=0, words=0)

    def __init__(self, name):
        self.name = name

    def count_message(self, message):
        self.count = self.count + Counter(messages=1,
                                          words=message.count_words())

class MessageExportAnalyer:
    messages = []
    senders = {}

    def __init__(self, input_file_path):
        self.parse_file(input_file_path)

    def parse_file(self, input_file_path):
        """
        Parses an export file
        Parses every line on its own, but handles
        continued messages
        """
        try:
            f = open(input_file_path)
        except IOError:
            print "Input file not found."
            sys.exit(1)

        last_message = None
        for line in f:
            line = line.strip()
            if not line:
                continue
            (t, dt, sender_name, text) = self.parse_line(line)
            if t == LINE_TYPE_UNCHANGED and last_message:
                last_message.add_line(text)
            elif t == LINE_TYPE_MESSAGE:
                s = None
                try:
                    sender = self.senders[sender_name]
                except KeyError:
                    sender = Sender(sender_name)
                    self.senders[sender_name] = sender
                message = Message(dt, sender, text)
                self.messages.append(message)
                last_message = message
            else:
                pass
        for message in self.messages:
            message.sender.count_message(message)

    def parse_line(self, line):
        """
        Parses a single line of the export
        Handles dates and continued messages
        Returns a tuple of (type of line, datetime, sender name, message)
        """
        t = LINE_TYPE_UNCHANGED
        dt = None
        sender = ""
        text = line

        # Try to find a datetime at beginning of line
        # Export can be in different formats, so check multiple string lengths
        for c in range(20,10,-1):
            try:
                dt = dateutil.parser.parse(line[0:c])
                line = line[(c-1):]
                break
            except ValueError:
                pass
        
        # If datetime found, check if this is an actual message or just the day divider
        if dt:
            if dt.time() == datetime.time():
                t = LINE_TYPE_DATE
            else:
                t = LINE_TYPE_MESSAGE

        # Split sender and text
        try:
            (sender, text) = [x.strip() for x in line.split(":", 1)]
        except ValueError:
            text = line

        return (t, dt, sender, text)

    def stats(self):
        """
        Prints some simple stats
        """
        print "\nCounts per sender:"
        for (name, sender) in self.senders.iteritems():
            print "%s:  %d messages, %d words, %.2f words/message" % (sender.name,
                        sender.count["messages"], sender.count["words"],
                        sender.count["words"]/sender.count["messages"])

        data = self.count_per_period('messages', 'day')
        print "\nMost active days:"

        sorted_data = sorted(data, key=operator.itemgetter(1), reverse=True)
        for date, count in sorted_data[:10]:
            print "%s: %d messages" % (date, count)

    def count_per_period(self, counter, period):
        """
        Returns a list of (date, number of messages) tuples
        """
        dates = []
        counts = Counter()

        # Count messages
        for message in self.messages:
            date = message.dt.date()

            # Depending on requested period, adjust date
            if period == 'day':
                pass
            elif period == 'week':
                date = date + datetime.timedelta(days=1-date.isoweekday())
            elif period == 'month':
                date = date + datetime.timedelta(days=1-date.day)
            if not date in dates:
                dates.append(date)

            # Determine what to count
            cnt = 0
            if counter == 'messages':
                cnt = 1
            elif counter == 'words':
                cnt = message.count_words()

            counts = counts + Counter({date: cnt})

        values_out = []
        last_date = None

        # Timedelta to account for missing dates
        td = None
        if period == 'day':
            td = datetime.timedelta(days=1)
        elif period == 'week':
            td = datetime.timedelta(days=7)
        elif period == 'month':
            td = relativedelta(months=1)

        for date in dates:
            # Fill in missing (count=0) dates
            if last_date:
                while (last_date+td) < date:
                    fill_date = last_date + td
                    values_out.append((fill_date, 0))
                    last_date = fill_date
            values_out.append((date, counts[date]))
            last_date = date

        return values_out

    def plot(self, counter, period):
        """
        Plots the message counts with matplotlib
        Built on example from http://matplotlib.org/1.3.1/examples/api/date_demo.html
        """
        months    = mdates.MonthLocator()
        weeks     = mdates.WeekdayLocator(byweekday=mdates.MO)
        date_formatter = mdates.DateFormatter('%m. %Y')

        fig, ax = plt.subplots()

        data = self.count_per_period(counter, period)
        (dates, values) = zip(*data)
        ax.plot(dates, values, label=("Messages per %s" % (period)))

        # Plot trend
        # x = range(0, len(dates))
        # fit = numpy.polyfit(x, values, 1)
        # fit_fn = numpy.poly1d(fit)
        average_n = 3
        if period == 'day':
            average_n = 20
        if period == 'week':
            average_n = 5
        def moving_average(a, n=3):
            ret = numpy.cumsum(a, dtype=float)
            ret[n:] = ret[n:] - ret[:-n]
            return ret[:] / n
        ax.plot(dates, moving_average(values, average_n), '--k')

        # Format for axis
        ax.xaxis.set_major_locator(months)
        ax.xaxis.set_major_formatter(date_formatter)
        ax.xaxis.set_minor_locator(weeks)

        ax.set_ylim(bottom=0)
        
        ax.format_xdata = mdates.DateFormatter('%Y-%m-%d')
        ax.format_ydata = int
        ax.grid(True)

        legend = ax.legend(loc='upper center')

        fig.autofmt_xdate()
        plt.show()

    def output(self):
        for message in self.messages:
            print "[%s] [%s] %s" % (message.dt, message.sender, message.text)

if __name__ == "__main__":

    possible_periods = ['day', 'week', 'month']
    possible_actions = ['data', 'stat', 'plot']

    if (len(sys.argv) > 2):
        input_file_path = sys.argv[1];

        action = sys.argv[2];
        if not action in possible_actions:
            print "Invalid action. Use one of %s" % (", ".join(possible_actions))
            sys.exit(1)

        period = 'day'
        if len(sys.argv) > 3:
            period = sys.argv[3];
        if not period in possible_periods:
            print "Invalid period. Use one of %s" % (", ".join(possible_periods))
            sys.exit(1)

        print "Parsing file..."
        analyzer = MessageExportAnalyer(input_file_path)
        if action == "stat":
            analyzer.stats()
        elif action == "plot":
            print "Generating plots..."
            analyzer.plot('messages', period)
        elif action == "data":
            data = analyzer.count_per_period('messages', period)
            for date, count in data:
                print "%s: %d" % (date, count)
        sys.exit(0)
    else:
        print "Usage: %s input-file.txt action [period]" % __file__
        print "  Actions: %s" % (", ".join(possible_actions))
        print "  Periods: %s" % (", ".join(possible_periods))
        sys.exit(1)