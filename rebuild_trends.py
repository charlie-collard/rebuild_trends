from __future__ import print_function, division
from pytrends.request import TrendReq
from pandas.core.frame import DataFrame
from io import open
import numpy as np
import traceback
import datetime
import sys
import os
import math

if sys.version_info[0] < 3:
    input_func = raw_input
else:
    input_func = input

def error_quit(error_msg):
    print("ERROR: " + error_msg, file=sys.stderr)
    sys.exit(1)

IN_FILENAME = input_func("Please enter filename containing keywords to search for: ")
if not os.path.isfile(IN_FILENAME):
    error_quit("File does not exist")
    
OUT_FILENAME = input_func("Please enter filename to write to: ")
while os.path.isfile(OUT_FILENAME):
    response = input_func("WARNING: File already exists. Overwrite? y/N ")
    if response.lower() == "y":
        break
    else:
        OUT_FILENAME = input_func("Please enter filename to write to: ")

try:
    start_date = input_func("Please enter start date in format YYYY/MM/DD: ")
    START_DATETIME = datetime.datetime.strptime(start_date, "%Y/%m/%d")
    end_date = input_func("Please enter end date in format YYYY/MM/DD: ")
    END_DATETIME = datetime.datetime.strptime(end_date, "%Y/%m/%d")
except ValueError:
    error_quit("Invalid date format")

if END_DATETIME <= START_DATETIME:
    error_quit("End date should not be before start date")

TOTAL_TIMESPAN = END_DATETIME - START_DATETIME + datetime.timedelta(days=1)
WINDOW_SIZE = datetime.timedelta(weeks=32) # Known to cause google trends to respond with daily data
WINDOW_OVERLAP = datetime.timedelta(weeks=7) # Overlap the windows by about 20% of their size
WINDOW_COUNT = int(math.ceil(TOTAL_TIMESPAN.total_seconds() / (WINDOW_SIZE - WINDOW_OVERLAP).total_seconds()))

try:
    with open(IN_FILENAME, encoding="utf8") as f:
        keywords = f.readlines()
        for i in range(len(keywords)):
            word = keywords[i]
            if "\n" in word:
                keywords[i] = word[:word.find("\n")]
except IOError:
    error_quit("File does not exist")

final_data = None
try:
    for keyword in keywords:
        window_data = []
        for window in range(WINDOW_COUNT):
            window_start_date = START_DATETIME + window*WINDOW_SIZE - window*WINDOW_OVERLAP
            window_end_date = window_start_date + WINDOW_SIZE - datetime.timedelta(days=1)
            window_start_date = window_start_date.strftime("%Y-%m-%d")
            window_end_date = window_end_date.strftime("%Y-%m-%d")
            print("Collecting data from %s to %s for keyword '%s'" % (window_start_date, window_end_date, keyword))
            window_timeframe = "%s %s" % (window_start_date, window_end_date)

            pytrends = TrendReq()
            pytrends.build_payload([keyword], timeframe=window_timeframe)
            received_data = pytrends.interest_over_time()
            if received_data.empty:
                date_index = []
                for i in range((window_end_date - window_start_date).days + 1):
                    new_time = window_start_date + i*datetime.timedelta(days=1)
                    date_index.append(new_time)
                received_data["date"] = date_index
                received_data.set_index("date", inplace=True)
                received_data[keyword] = 0
                received_data[keyword] = received_data[keyword].astype(np.int32)
                received_data["isPartial"] = False
            window_data.append(received_data)

        current_ratio = 1
        keyword_data = window_data[0]
        for window in range(WINDOW_COUNT-1):
            currentw = window_data[window]
            nextw = window_data[window+1]
            try:
                start_datetime = nextw.axes[0][0].to_pydatetime()
            except IndexError:
                break
            overlap_start = 0
            while currentw.axes[0][overlap_start].to_pydatetime() != start_datetime:
                overlap_start += 1

            current_data = currentw[currentw.columns[0]][overlap_start:overlap_start+WINDOW_OVERLAP.days]
            next_data = nextw[nextw.columns[0]][:WINDOW_OVERLAP.days]
            sum_current = sum(current_data)
            sum_next = sum(next_data)
            if sum_current == 0 or sum_next == 0:
                print("Couldn't get enough data for keyword '%s'" + keyword)
                to_zero = nextw[WINDOW_OVERLAP.days:]
                to_zero[to_zero.columns[0]] = 0
                keyword_data = keyword_data.append(to_zero)
                continue
            ratios = [next_data[i] / current_data[i] for i in range(WINDOW_OVERLAP.days) if current_data[i] != 0 and next_data[i] != 0]
            if len(ratios) == 0:
                print("Couldn't get enough data for keyword '%s'" % keyword)
                to_zero = nextw[WINDOW_OVERLAP.days:]
                to_zero[to_zero.columns[0]] = 0
                keyword_data = keyword_data.append(to_zero)
                continue
            losses = [ratios[i] * sum_current - sum_next for i in range(len(ratios))]
            for i in range(len(losses)):
                if losses[i] == 0:
                    losses[i] = 0.0000001
            weights = [abs(1 / losses[i]) for i in range(len(ratios))]
            products = [ratios[i] * weights[i] for i in range(len(weights))]
            best_ratio = sum(products) / sum(weights)
            current_ratio *= best_ratio
            nextw = nextw / current_ratio
            keyword_data = keyword_data.append(nextw[WINDOW_OVERLAP.days:])
        if final_data is None:
            final_data = keyword_data.drop("isPartial", axis=1)
        else:
            final_data[keyword_data.columns[0]] = keyword_data.drop("isPartial", axis=1).values
        print("Finished collecting data for keyword '%s'" % keyword)
    with open(OUT_FILENAME, "wb") as f:
        f.write(final_data.to_csv().encode("utf8"))
except Exception as e:
    traceback.print_exc()
    print("Exception occurred, attempting to write to file to preserve data collected so far...", file=sys.stderr)
    with open(OUT_FILENAME, "wb") as f:
        f.write(final_data.to_csv().encode("utf8"))
    print("Successfully wrote to file", file=sys.stderr)
    sys.exit(1)
