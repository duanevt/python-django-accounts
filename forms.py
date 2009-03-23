from django import forms
from solardev.accounts.models import *

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

class WithholdingForm(forms.ModelForm):
	account = forms.ModelChoiceField(
		Account.objects.filter(closed_on__isnull=True, type__in=["Asset", "Expense"])
	)
	
	class Meta:
		model = EntryAction
		exclude = ('entry',)
