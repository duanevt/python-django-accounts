from accounts.models import *
import datetime
from dateutil.relativedelta import relativedelta
from django import template
from django.core.cache import cache
from django.utils.datastructures import SortedDict
from accounts.templatetags.rollup import rollup
import os

#import matplotlib
#matplotlib.use('Agg')
#from pylab import *

register = template.Library()

@register.filter
def gte(val1, val2):
    return val1 >= val2
@register.filter
def gt(val1, val2):
    return val1 > val2
@register.filter
def lte(val1, val2):
    return val1 <= val2
@register.filter
def lt(val1, val2):
    return val1 < val2

@register.filter
def accounts_dataset(accounts, months=6):
    dataset = []
    totals = [None, [0 for x in range(months + 1)]]
    for account in accounts.all():
        stats = account_statistics(account, months)
        row = (account, stats)
        count = 0
        for date, item in stats.iteritems():
            if item:
                totals[1][count] += item
            count += 1
        dataset += [row]
    dataset += [totals]
    
    return dataset

@register.filter
def mini_monthly_graph(accounts, name):
    name = "monthly_%s" % name
    return mini_graph(accounts, name, True)

@register.filter
def monthly_graph():
    name = "monthly_%s" % name
    if cache.get(name):
        retval = cache.get(name)
    else:
        retval = graph(accounts,
                       name=name,
                       bymonth=True
                       )
        cache.set(name, retval, 5)
    return retval

@register.filter
def mini_graph(accounts, name, bymonth=False):
    name = "mini_%s" % name
    if cache.get(name):
        retval = cache.get(name)
    else:
        retval = graph(accounts,
                       name=name,
                       start=datetime.datetime.now() - relativedelta(months=12),
                       width=1.0,
                       height=.25,
                       decorations=False,
                       bymonth=bymonth
                       )
        cache.set(name, retval, 5)
    return retval

@register.filter
def graph(accounts, name, start=None, end=None, width=5, height=3.5, aggregate=True, bymonth=True, decorations=True):
    
    try:
        if start == None:
            start = datetime.datetime.now() - relativedelta(months=24)
        if end == None:
            end = datetime.datetime.now()
        name += ".png"

        #TODO: check cache

        if not hasattr(accounts, "__iter__"):
            accounts = [accounts]

        # get all applicable actions
        actions = EntryAction.objects.filter(
                                             account__in=accounts,
                                             entry__date__gte=start,
                                             entry__date__lte=end
                                             ).order_by("entry__date").select_related()
        
        nodes = []
        dates = []

        month = actions[0].entry.date.month
        day = actions[0].entry.date.day

        total = 0
        account_totals = {}
        for account in accounts:
            balance = account.balance(start)
            total += balance
            account_totals[account.id] = balance

        dates += [start]
        nodes += [total]
        
        for action in actions:
            total += action.amount
            if action.entry.date.month != month:

                # take statistics by month for tempory accounts
                if bymonth: #self.type in ["Expense", "Revenue"]:
                    total = 0
                month = action.entry.date.month
                day = action.entry.date.day

                # set the balances to normal
                if True: #self.type in ["Asset"]:
                    node = total
                else:
                    node = -total

                date = datetime.datetime(action.entry.date.year, month, day)
                dates += [date]
                nodes += [node]

        co = (1.0, 1.0, 1.0, 0.0,)
        fig = figure(figsize=[width, height], facecolor=co, edgecolor=co)
        ax = fig.add_subplot(111, frameon=False, axis_bgcolor="transparent")
        ax.plot_date(dates, nodes, '-', alpha=0.75)
        if decorations:
            ax.xaxis.set_major_locator(MonthLocator(bymonth=[1, 4, 7, 10]))
            ax.xaxis.set_major_formatter(DateFormatter("%b `%y"))
            setp(ylabel("Amount"), fontsize=9)
            setp(getp(gca(), 'yticklabels'), fontsize=7)
            setp(getp(gca(), 'xticklabels'), fontsize=7)
            grid(True)
        else:
            ax.xaxis.set_major_locator(NullLocator())
            ax.xaxis.set_major_formatter(NullFormatter())
            ax.yaxis.set_major_locator(NullLocator())
            ax.yaxis.set_major_formatter(NullFormatter())
            
            #setp(ylabel("Amount"), fontsize=9)
            setp(xlabel(""), fontsize=9)
            setp(getp(gca(), 'yticklabels'), fontsize=7)
            setp(getp(gca(), 'xticklabels'), fontsize=7)
            grid(False)
        fig.autofmt_xdate()

        # Render the graph
        savefig(
                os.path.join(settings.MEDIA_ROOT, name).encode("utf-8")
                )
        close()

        return os.path.join(settings.MEDIA_URL, name)
    except Exception, ex:
        import traceback
        return traceback.format_exc()

def get_balance(accounts, start, end):

    balance = 0
    if not getattr(accounts, '__iter__', False):
        accounts = [accounts]

    for account in accounts:
        balance += account.normal_balance(end) - account.normal_balance(start)

    return balance

@register.filter()
def get_months_back(months_back):
    return datetime.datetime.now() - relativedelta(months=months_back)

@register.filter
def monthly_balance(accounts, months_back=0):
    start = datetime.datetime.now() - relativedelta(months=months_back)
    start = datetime.datetime(start.year, start.month, 1) - relativedelta(days=1)
    if months_back == 0:
        end = datetime.datetime.now()
    else:
        end = datetime.datetime.now() - relativedelta(months=months_back-1)
        end = datetime.datetime(end.year, end.month, 1) - relativedelta(days=1)
    return get_balance(accounts, start, end)

@register.filter
def yearly_balance(accounts):
    now = datetime.datetime.now()
    return get_balance(accounts, datetime.datetime(now.year, 1, 1), now)

@register.filter()
def account_statistics(accounts, months_back=6):
    stats = SortedDict()
    total = 0
    count = 0
    thelist = range(months_back)
    thelist.reverse()
    for x in thelist:
        cur = monthly_balance(accounts, x)
        count += 1
        total += cur
        stats[get_months_back(x)] = cur
    stats["Avg"] = total / count
    return stats

@register.filter("range")
def _range(x):
    return range(x)