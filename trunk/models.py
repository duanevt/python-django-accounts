# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#     * Rearrange models' order
#     * Make sure each model has one field with primary_key=True
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [appname]'
# into your database.

from django.db import connection, models
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from math import ceil, floor
import datetime, sys, os

from django.utils.safestring import mark_safe
#import matplotlib
#matplotlib.use('Agg')
#from pylab import *
from dateutil.relativedelta import relativedelta    
            
class Account(models.Model):
    type = models.CharField(max_length=15,
        choices=(("Asset", "Asset"),("Expense", "Expense"),("Revenue", "Revenue"),("Liability", "Liability"),("Equity", "Equity")))
    
    name = models.CharField(max_length=255)
    budgeted_limit = models.FloatField(blank=True, null=True, 
        help_text=mark_safe(
            "<strong>Assets</strong>: Forces the budget to add no more that specified<br />" +
            "<strong>Expenses & Revenues</strong>: Used for user convience<br />"+
            "<strong>Liabilities & Owner's Equity</strong>: Not Applicable<br />")
    )
    closed_on = models.DateField(null=True, blank=True)
    site = models.ForeignKey(Site)

    objects = CurrentSiteManager()

    class Meta:
        ordering = [ 'closed_on', 'type', 'name',]
    
    def closed(self):
        return self.closed_on != None
    
    def balance(self, as_of=datetime.datetime.now()):
        try:
            balance = AccountBalance.objects.all().filter(as_of__lte=as_of, account__exact=self)[-1]
            actions = EntryAction.objects.all().filter(
                entry__date__gte=balance.as_of,
                entry__date__lte=as_of,
                account=self)#.exclude(entry__description__icontains="closing entry")
            last = balance.balance
        except:
            actions = EntryAction.objects.all().filter(
                entry__date__lte=as_of, account=self
            ).exclude(entry__description__icontains="closing entry")
            last = 0.0

        # add up current amount
        count = 0
        current = 0.0
        for action in actions:
            count += 1
            current += action.amount

        # save a new account balance
        if count > 100: #TODO: set this in the settings
            AccountBalance(account=self, balance = last + current).save()

        return round(last + current, 2)

    def normal(self):
        if self.type in ['Asset']:
            return True
        return False

    def normal_balance(self, as_of=datetime.datetime.now()):
        if self.normal():
            balance = self.balance(as_of)
        else: balance = -self.balance(as_of)

        
        if balance == 0.0 or balance == -0.0:
            balance = 0.0
        return balance
    
    def has_normal_balance(self):        
        return self.normal_balance() >= 0
    
    def graph(self, start=None, end=None):
        try:
            start = datetime.datetime.now() - relativedelta(months=24)
            end = datetime.datetime.now()
            name = u'%s_history_%s.png' % (self.name, start.month)
            #TODO: check cache
            
            actions = self.entryaction_set.all().order_by("entry__date")#(start, end))filter(entry__date__gte=start)
            nodes = []
            dates = []
            month = actions[0].entry.date.month
            day = actions[0].entry.date.day
            
            max = 0
            total = 0
            count = 0
            for action in actions:
                total += action.amount
                count += 1
                if action.entry.date.month != month:# or \
#                action.entry.date.day != day:
                    month = action.entry.date.month
                    day = action.entry.date.day

                    # set the balances to normal
                    if self.type in ["Asset"]:
                        node = total
                    else:
                        node = -total

                    # take statistics by month for tempory accounts
                    if self.type in ["Expense", "Revenue"]:
                        total = 0

                    date = datetime.datetime(action.entry.date.year, month, 1)
                    dates += [date]
                    nodes += [node]
            
            fig = figure()
            ax = fig.add_subplot(111)
            ax.plot_date(dates, nodes, '-')
            ax.xaxis.set_major_locator(MonthLocator(bymonth=[1, 4, 7, 10]))
            ax.xaxis.set_major_formatter(DateFormatter("%b `%y"))
            #ax.xaxis.set_minor_locator(MonthLocator(bymonth=[6]))
            #ax.xaxis.set_minor_formatter(DateFormatter("%m"))
            setp(ylabel("Amount"), fontsize=9)
            setp(getp(gca(), 'yticklabels'), fontsize=7)
            setp(getp(gca(), 'xticklabels'), fontsize=7)
            #ax.autoscale_view()
            fig.autofmt_xdate()
            title("History of %s" % self.name)
            
            grid(True)
            f = gcf()
            f.set_figsize_inches([5, 3.5])
            #axis([1, len(nodes), 0, max * 1.3])

            # Render the graph
            savefig(os.path.join(settings.MEDIA_ROOT, name).encode("utf-8"))
            close()
            
            return os.path.join(settings.MEDIA_URL, name)
        except Exception, ex:
            import traceback
            return traceback.format_exc()
    
    def __unicode__(self):
        return u"%s" % self.name
    
class AccountBalance(models.Model):
    account = models.ForeignKey(Account)
    balance = models.FloatField()
    as_of = models.DateTimeField(default=datetime.datetime.now())

class Budget(models.Model):
    name = models.CharField(max_length=255)
    site = models.ForeignKey(Site)

    objects = CurrentSiteManager()
    
    def __unicode__(self):
        return u"%s" % self.name
    
    def process(self, entry, total, amount):
        actions = []
        items = BudgetItem.objects.filter(budget=self).order_by('sequence')
        for item in items:
            amount, action = item.getAction(total, amount)
            action.entry = entry
            actions += [action]
        return amount, actions
    
class BudgetItem(models.Model):
    class Meta:
        ordering = ("sequence",)
    budget = models.ForeignKey(Budget)
    account = models.ForeignKey(Account)
    type = models.CharField(max_length=1,
        choices=(("E", "Exact"), ("P", "Percent of Total"), ("R", "Percent of Remaining")))
    amount = models.FloatField()
    sequence = models.IntegerField()
    
    def getAction(self, total, amount):
        if self.type == "E":
            myamount = self.amount
        else:
            percent = self.amount
            if percent > 1.0:
                percent = percent / 100.0
            if self.type == "P":
                myamount = total * percent
            else:
                myamount = amount * percent
            
        myamount = ceil(myamount*100)/100
        if myamount > amount:
            myamount = amount
            amount = 0
        else: 
            amount -= myamount
            
        return amount, EntryAction(account=self.account, amount=myamount)

class Entry(models.Model):
    class Meta:
        verbose_name_plural = "Entries"
        ordering = ["-date", "-id"]

    description = models.CharField(max_length=300)
    date = models.DateField(default=datetime.date.today())
    site = models.ForeignKey(Site)

    objects = CurrentSiteManager()
    
    def __unicode__(self):
        return u"Entry #%s %s" % (self.id, self.date)
    
    def debits(self):
        return self.entryaction_set.filter(amount__gte=0)
    
    def credits(self):
        return self.entryaction_set.filter(amount__lt=0)

    def total(self):
        total = 0
        for debit in self.debits():
            total += debit.amount
        return total

    def error(self):
        total = 0
        for debit in self.entryaction_set.all():
            total += debit.amount
        if abs(floor(total)) > 0:
            return "Error!: %.0f" % total# != 0.0
        else:
            return ""
    #error.boolean = True

class EntryAction(models.Model):
    entry = models.ForeignKey(Entry)
    account = models.ForeignKey(Account)
    amount = models.FloatField()
    
    def __unicode__(self):
        return u'%s: %s-%s' % (self.entry, self.account, self.amount)

    def positive(self):
        if self.amount > 0:
            return self.amount
        else:
            return -self.amount
