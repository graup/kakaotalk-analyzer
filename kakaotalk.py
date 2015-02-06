#!/usr/bin/python

"""
Simple analysis of KakaoTalk chat export files.
Parses messages and senders into python objects
Automatically reads split files.
Either run this file directly or import as module

    analyzer = MessageExportAnalyer(input_file_path, use_cache=True)
    print analyzer.messages
    print analyzer.senders
"""

from __future__ import division

import sys
import glob
import dateutil.parser
from dateutil.relativedelta import relativedelta
import datetime
import re
import time
from collections import Counter
import operator
import pickle

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy

LINE_TYPE_UNCHANGED = 0 # Status unchanged from last line. Usually a continued message.
LINE_TYPE_DATE      = 1 # Line with a single date (new day). Can be ignored.
LINE_TYPE_MESSAGE   = 2 # Line with datetime, sender and message

class Message:
    dt = None
    response_time = 0
    text = ""
    sender = None # pointer to sender
    prev = None # pointer to previous message

    def __init__(self, dt, sender, text, response_time):
        self.dt = dt
        self.sender = sender
        self.text = text
        self.response_time = response_time

    def add_line(self, text):
        self.text = self.text + "\n" + text

    def count_words(self):
        return len(re.findall(r'\b\w+\b', self.text))

    def __str__(self):
        return "[%s] %s: %s" % (self.dt, self.sender.name, self.text)

class Sender:
    name = ""
    count = Counter(messages=0, words=0)
    response_time = Counter(time=0, count=0)

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def count_message(self, message):
        self.count = self.count + Counter(messages=1, words=message.count_words())

class MessageExportAnalyser:
    messages = []
    senders = {}

    def __init__(self, input_file_path, use_cache=True):
        """
        Parse given file as well as check for split files.
        Exports can be split in files named a.txt, a-1.txt, a-2.txt and so on.
        If use_cache is True the parsed content is saved as a bytestream and
        the file is not reparsed.
        """
        cache_file = input_file_path + '.data'
        if use_cache:
            # Read parsed data from cache
            try:
                f = open(cache_file, "r")
                t_start = time.clock()
                print "Parsing cached data..."
                self.messages, self.senders = pickle.load(f)
                print "Parsed %d messages in %.4f seconds" % (self.total_count(), time.clock()-t_start)
                return
            except IOError:
                pass
            except pickle.PickleError:
                print "Error parsing cached data. Try deleting .data file."

        t_start = time.clock()

        # We use glob to automatically find split files, but glob doesn't work well with
        # UTF-8 filenames, so we need to work around that...
        regex = re.compile("^(.*/)(.*?)(\-\d)?\.(.*?)$")
        r = regex.search(input_file_path)
        glob_string = unicode(r.groups()[0] + '*[0-9].*', sys.getfilesystemencoding())
        file_path_beginning = unicode(r.groups()[0] + r.groups()[1], sys.getfilesystemencoding())
        files = glob.glob(glob_string)
        split_files = filter(lambda f: f.startswith(file_path_beginning), files)
        all_files = split_files
        for f in all_files:
            print "Parsing file %s..." % f
            self.parse_file(f)

        print "Parsed %d messages from %d files in %.4f seconds" % (self.total_count(), len(all_files), time.clock()-t_start)

        if use_cache:
            # Dump parsed data to cache
            try:
                f = open(cache_file, "w")
                pickle.dump( (self.messages, self.senders, ), f)
            except IOError:
                print "Could not open cache file for saving parsed data."

    def parse_file(self, input_file_path):
        """
        Parses one export file.
        Parses every line on its own while handling continued messages.
        """
        try:
            f = open(input_file_path)
        except IOError:
            print "Could not open input file %s." % input_file_path
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
                try:
                    sender = self.senders[sender_name]
                except KeyError:
                    sender = Sender(sender_name)
                    self.senders[sender_name] = sender
                if last_message and last_message.sender != sender:
                    response_time = (dt - last_message.dt).total_seconds()
                else:
                    response_time = 0
                message = Message(dt, sender, text, response_time)
                message.prev = last_message
                self.messages.append(message)
                last_message = message
            else:
                pass

        for message in self.messages:
            message.sender.count_message(message)

    def parse_line(self, line):
        """
        Parses a single line of the export.
        Recognizes dates and continued messages
        Returns a tuple of (type of line, datetime, sender name, message)
        """
        t = LINE_TYPE_UNCHANGED
        dt = None
        sender = ""
        text = line

        # Try to find a datetime at beginning of line
        # Export can be in different formats, so check multiple string lengths
        for c in range(40,10,-1):
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

        if sender == "" or sender == " ":
            t = LINE_TYPE_UNCHANGED

        return (t, dt, sender, text)

    def stats(self):
        """
        Prints some simple stats
        """
        print "\nFirst message: %s" % self.messages[0].dt
        print "Last message: %s" % self.messages[len(self.messages)-1].dt
        time_range = self.messages[len(self.messages)-1].dt - self.messages[0].dt
        print "(%d days, avg. %.1f messages per day)" % (time_range.days, len(self.messages)/time_range.days)

        print "\nCounts per sender:"
        for (name, sender) in self.senders.iteritems():
            print "%s:  %d messages, %d words, %.2f words/message" % (
                        sender,
                        sender.count["messages"], sender.count["words"],
                        sender.count["words"]/sender.count["messages"])

        print "\nMost active days:"
        data = self.count_per_period('messages', 'day')
        sorted_data = sorted(data, key=operator.itemgetter(1), reverse=True)
        for date, count in sorted_data[:10]:
            print "%s: %d messages" % (date, count)

    def analyze(self):
        print "\nLongest messages:"
        sorted_data = sorted(self.messages, key=lambda x: len(x.text), reverse=True)
        for message in sorted_data[:10]:
            print "\n%s" % message

    def total_count(self):
        return sum(s.count['messages'] for s in self.senders.itervalues())

    def count_per_period(self, counter, period):
        """
        Returns a list of (date, number of messages) tuples
        """
        dates = []
        counts = Counter()

        # Count messages
        for message in self.messages:
            if period == 'hour':
                date = message.dt
            else:
                date = message.dt.date()

            # Depending on requested period, adjust date
            if period == 'hour':
                date = date.replace(minute=0, second=0, microsecond=0)
            elif period == 'day':
                pass
            elif period == 'week':
                date = date + datetime.timedelta(days=1-date.isoweekday())
            elif period == 'month':
                date = date + datetime.timedelta(days=1-date.day)
            if not date in dates:
                dates.append(date)

            # Determine what to count
            if counter == 'messages':
                cnt = 1
            elif counter == 'words':
                cnt = message.count_words()

            counts = counts + Counter({date: cnt})

        values_out = []
        last_date = None

        # Timedelta to account for missing dates
        td = None
        if period == 'hour':
            td = datetime.timedelta(hours=1)
        elif period == 'day':
            td = datetime.timedelta(days=1)
        elif period == 'week':
            td = datetime.timedelta(days=7)
        elif period == 'month':
            td = relativedelta(months=1)

        for date in dates:
            # Fill in missing dates (count=0)
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
        ax.plot(dates, values, label=("%s per %s" % (counter, period)))

        # Plot moving average
        average_n = 3
        if period == 'hour':
            average_n = 48
        if period == 'day':
            average_n = 30
        if period == 'week':
            average_n = 5

        # a very simple and fast moving average
        def moving_average(a, n=3):
            ret = numpy.cumsum(a, dtype=float)
            ret[n:] = ret[n:] - ret[:-n]
            return ret[:] / n
        
        # a moving average that looks behind and ahead
        def moving_average2(a, n=3):
            out = []
            for s in range(0, len(a)):
                first = s-n if s > n else 0
                last = s+n if s+n < len(a) else len(a)
                out.append(numpy.sum(a[first:last]) / (last-first))
            return out
        ax.plot(dates, moving_average2(values, average_n//2), '--k')

        # Format for axis
        ax.xaxis.set_major_locator(months)
        ax.xaxis.set_major_formatter(date_formatter)
        ax.xaxis.set_minor_locator(weeks)

        ax.set_ylim(bottom=0)
        
        ax.format_xdata = mdates.DateFormatter('%Y-%m-%d')
        ax.format_ydata = int
        ax.grid(True)

        ax.legend(loc='upper center')

        fig.autofmt_xdate()
        plt.show()

    def output(self):
        for message in self.messages:
            print "[%s] [%s] %s" % (message.dt, message.sender, message.text)

if __name__ == "__main__":

    # periods to apply to plots
    # hour is not recommended, takes a lot of memory and time
    possible_periods = ['month', 'week', 'day', 'hour']
    # actions this script handles
    possible_actions = ['data', 'stat', 'plot', 'analyze']

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

        analyzer = MessageExportAnalyser(input_file_path)
        if action == "stat":
            analyzer.stats()
        elif action == "analyze":
            analyzer.analyze()
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