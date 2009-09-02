from django.utils.datastructures import SortedDict
from django import forms
from solardev.forms import reorder_fields
from accounts.models import *

def get_cash():
    try: 
        return Account.objects.get(type="Asset", name="Cash").pk
    except Exception, ex:
        print ex
        return None
def get_default_budget():
    if Budget.objects.count() == 1:
        return Budget.objects.get().pk
    else:
        return None
    
class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget 

class BudgetItemForm(forms.ModelForm):
    class Meta:
        model = BudgetItem 

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account 

class AddExpenseForm(forms.ModelForm):
    amount = forms.FloatField()
    expense = forms.ModelChoiceField(
        Account.objects.filter(closed_on__isnull=True, type="Expense"),
        label="Expense Account")
    asset = forms.ModelChoiceField(
        Account.objects.filter(closed_on__isnull=True, type="Asset"),
        label="Asset Account",
        initial=get_cash()
    )

    class Meta:
        model = Entry
        #exclude = ("site",)
        order = ("amount", "date", "expense", "asset", "description")

    def __init__(self, *args, **kwargs):
        super(AddExpenseForm, self).__init__(*args, **kwargs)
        reorder_fields(self)

    def save(self, *args, **kwargs):
        obj = super(AddExpenseForm, self).save(*args, **kwargs)
        obj.site = Site.objects.get_current()
        if "commit" in kwargs and kwargs["commit"]:
            obj.save()
        return obj

class AssetActionForm(forms.ModelForm):
    account = forms.ModelChoiceField(
        Account.objects.filter(closed_on__isnull=True, type="Asset"),
        label="Asset Account"
    )
    class Meta:
        model = EntryAction
        exclude = ('entry',)

class AddRevenueForm(forms.ModelForm):
    amount = forms.FloatField()
    budget = forms.ModelChoiceField(
        Budget.objects.all(), 
        label="Budget",
        initial=get_default_budget())
    default = forms.ModelChoiceField(
        Account.objects.filter(closed_on__isnull=True, type="Asset"),
        label="Default Account",
        initial=get_cash()
    )
    revenue = forms.ModelChoiceField(
        Account.objects.filter(closed_on__isnull=True, type="Revenue"),
        label="Revenue Account"
    )

    class Meta:
        model = Entry
        exclude = ("site", )
        order = ("amount", "budget", "default", "revenue", "description")

    def __init__(self, *args, **kwargs):
        super(AddRevenueForm, self).__init__(*args, **kwargs)
        reorder_fields(self)

    def save(self, *args, **kwargs):
        obj = super(AddRevenueForm, self).save(*args, **kwargs)
        obj.site = Site.objects.get_current()
        if "commit" in kwargs and kwargs["commit"]:
            obj.save()
        return obj

class WithholdingForm(forms.ModelForm):
    account = forms.ModelChoiceField(
        Account.objects.filter(closed_on__isnull=True, type__in=["Asset", "Expense"])
    )
    
    class Meta:
        model = EntryAction
        exclude = ('entry',)
