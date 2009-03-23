"""

# create a new event
>>> from schedule.models import *
>>> import datetime
>>> from dateutil.rrule import *
>>> from dateutil.relativedelta import *
>>> r = Event()
>>> r.freq = YEARLY
>>> r.interval = 1
>>> today = datetime.datetime(2007, 3, 25)
>>> r.count = 2
>>> r.getDates(today, today, today + relativedelta(years=2))
(datetime.datetime(2007, 3, 25, 0, 0), datetime.datetime(2008, 3, 25, 0, 0))

# checking for conflicts
>>> import datetime
>>> from dateutil.rrule import *
>>> from dateutil.relativedelta import *
>>> r = rruleset()
>>> r.rrule(rrule(DAILY, count=2, dtstart=datetime.datetime(2008, 3, 26)))
>>> r.rrule(rrule(DAILY, count=2, dtstart=datetime.datetime(2008, 3, 27)))
>>> tuple(r)
(datetime.datetime(2007, 3, 27, 0, 0))
"""