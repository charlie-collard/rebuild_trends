Rebuild Trends
====

Attempt to reconstruct daily google trends data over longer periods of time.

Rebuild Trends is a (fairly messy) python script which attempts to solve the problem of obtaining fine grained Google Trends data over large periods of time. It uses the [pytrends](https://github.com/GeneralMills/pytrends) API.

The Problem
----------------------------------------

 When trends data is requested from Google, what is returned depends heavily on the width of the timespan you request. Request a single day, and you'll likely get hourly data. Request a year on the other hand, and the data is coarsened to be weekly (or even monthly!). So is it possible to get daily data over longer timespans?

 The naïve approach to solving this might be to request each month in sequence, then concatenate the data. Unfortunately, data received from different timespans are incomparable due to the automatic normalisation Google performs on the data. The biggest data-point in the timespan is given the value 100, and other data-points in the range are simply relative to that maximum value.
 
 Rebuild Trends attempts to solve this by overlapping the requests it makes, then using the overlapping days to compute a good scaling multiplier between the two timespans. If a given day has the value 83 in one timespan, but that same day has the value 59 in another timespan, we can reasonably assume that the second timespan has points approximately 82/59 times bigger, or about 40%.
 
 This is not an exact science - Google also performs slight fuzzing on the data it provides. The script attempts to rectify this by taking an average over the possible multipliers weighted by the error that multiplier produces over the overlapping days. Even then it's not perfect, so please bear in mind that for longer timespans the error may be significant.
 
Installation
----------------------------------------

 If you don't have pytrends installed then `pip install pytrends` should do the trick. Then simply create a file with keywords you want to search for on each line, run the script (python 3 preferred, but 2 has been tested to work), and follow the instructions. The data is output in CSV format to a file of your choice.
 
Example (sample output data available in repo)
----------------------------------------

 ![](https://i.imgur.com/XDAKFjx.png)
 *Search trends for 'Bitcoin' over 7 years from trends.google.com (1 month data granularity)*
 
 ![](https://i.imgur.com/XgdGbnA.png)
 *Search trends for 'Bitcoin' over 7 years rebuilt with the script (1 day data granularity)*
