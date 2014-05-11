#!/usr/bin/python

"""
Simple analysis of KakaoTalk chat export files
"""

import sys, os
import dateutil.parser
import datetime
import re
from collections import Counter

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

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

    def __str__(self):
        return "[%s] %s: %s" % (self.dt, self.sender.name, self.text)

class Sender:
    name = ""
    count = Counter(messages=0, words=0)

    def __init__(self, name):
        self.name = name

    def count_message(self, message):
        self.count = self.count + Counter(messages=1,
                             words=len(re.findall(r'\b\w+\b', message.text)))

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
        f = open(input_file_path)
        last_message = None
        for line in f:
            line = line.strip()
            if line == "":
                continue
            parsed_line = self.parse_line(line)
            (t, dt, sender_name, text) = parsed_line
            if t == LINE_TYPE_DATE:
                continue
            elif t == LINE_TYPE_UNCHANGED and last_message:
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
        for (name, sender) in self.senders.iteritems():
            print "%s: %d messages, %d words" % (sender.name, sender.count["messages"], sender.count["words"])

    def messages_per_period(self, period):
        """
        Returns a tuple of (list of dates, list of number of messages on the corresponding dates)
        """
        dates = []
        counts = Counter()
        for message in self.messages:
            date = message.dt.date()
            if period == 'day':
                pass
            elif period == 'week':
                date = date + datetime.timedelta(days=-date.isoweekday())
            elif period == 'month':
                date = date + datetime.timedelta(days=-date.day)
            dates.append(date)
            counts = counts + Counter({date: 1})

        values = []
        for date in dates:
            values.append( counts[date] )

        return (dates, values)

    def plot(self):
        """
        Plots the message counts with matplotlib
        Built on example from http://matplotlib.org/1.3.1/examples/api/date_demo.html
        """
        years     = mdates.YearLocator()
        months    = mdates.MonthLocator()
        weeks     = mdates.WeekdayLocator(byweekday=mdates.MO)
        monthsFmt = mdates.DateFormatter('%m. %Y')
        fig, ax = plt.subplots()

        (dates, values) = self.messages_per_period('month')
        ax.bar(dates, values, label="Messages per month")

        (dates, values) = self.messages_per_period('week')
        ax.plot(dates, values, label="Messages per week")

        (dates, values) = self.messages_per_period('day')
        ax.plot(dates, values, label="Messages per day")

        ax.xaxis.set_major_locator(months)
        ax.xaxis.set_major_formatter(monthsFmt)
        ax.xaxis.set_minor_locator(weeks)

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
    if (len(sys.argv) > 2):
        action = sys.argv[1];
        input_file_path = sys.argv[2];
        print "Parsing file..."
        analyzer = MessageExportAnalyer(input_file_path)
        if action == "stat":
            analyzer.stats()
        elif action == "plot":
            print "Generating plots..."
            analyzer.plot()
        sys.exit(0)
    else:
        print "Usage: %s action input-file.txt" % __file__
        print "  Actions: stat, plot"
        sys.exit(1)