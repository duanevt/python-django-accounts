from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.conf import settings 
from django.http import *
from django import forms
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required, permission_required
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, InvalidPage
from django.forms.models import inlineformset_factory
from django.template import RequestContext

from models import *
from forms import *
import datetime

@permission_required("accounts.add_account")
def summary(request, template_name="accounts/summary.htm"):
	accounts = Account.objects.select_related()
	assets = accounts.filter(type="Asset", closed_on=None)
	expenses = accounts.filter(type="Expense", closed_on=None)
	revenues = accounts.filter(type="Revenue", closed_on=None)
	liabilities = accounts.filter(type="Liability", closed_on=None)
	equity = accounts.filter(type="Equity", closed_on=None)

	income = {"Revenue": revenues, "Expenses": expenses}
	oe = {"Liabilities": liabilities, "Equity": equity}
	claims = {"Liabilities": liabilities, "Equity": equity,
			"Revenue": revenues, "Expenses": expenses}
	return render_to_response(template_name, locals(),
		context_instance=RequestContext(request))

@permission_required("accounts.add_account")
def journal(request, template_name="accounts/journal.htm"):
	""" 
	# Journal View
	renders an accounting general journal
	
	## Context
	- **entries**: list of all entry objects
	- **pages**: the paginator object for the entries
	- **page**: current page of objects	
	"""
	entries = Entry.objects.all()
	
	page = request.GET.get("page", 1)
	pages = Paginator(entries, 20)	
	page = pages.page(page)
	
	return render_to_response(template_name, locals(),
		context_instance=RequestContext(request))

@permission_required("accounts.add_account")
def ledger(request, id=None, template_name="accounts/ledger.htm"):
	try:
		account = Account.objects.get(pk=id)
	except:
		raise Http404
	page = request.GET.get("page", 1)
	actions = EntryAction.objects.all().filter(account=account).order_by("-entry__date")
	pages = Paginator(actions, 20)	
	page = pages.page(page)
	
	return render_to_response(template_name, locals(),
		context_instance=RequestContext(request))

@permission_required("accounts.delete_account")
def close_account(request, id=None, template_name="accounts/close_account.html"):

	account = Account.objects.get(id=id)

	try:
		default = list(Account.objects.filter(type__iexact="Equity"))[0]
	except Exception, ex:
		default = None

	class CloseAccountForm(forms.Form):
		close_to = forms.ModelChoiceField(
			initial=default,
			queryset=Account.objects.filter(type__iexact="Equity")
		)
		renew = forms.BooleanField(
			required=False,
			initial=True,
			help_text="check to zero and renew the account<br />uncheck to zero and close account"
		)

	if request.method == "POST":
		form = CloseAccountForm(request.POST)
		if form.is_valid():
			entry = Entry(site=Site.objects.get_current())
			entry.description = "closing entry for " + account.name
			entry.save()

			balance = account.balance()
			action1 = EntryAction(entry=entry)
			action1.amount = -balance
			action1.account = account
			action1.save()

			action2 = EntryAction(entry=entry)
			action2.amount = balance
			action2.account = form.cleaned_data['close_to']
			action2.save()

			if form.cleaned_data['renew']:
				name = account.name[:account.name.rfind(" ")] + datetime.datetime.now().strftime(" %y")
				account.name = name
			else:
				account.closed_on = datetime.datetime.now()
			account.save()
			return HttpResponseRedirect(reverse("summary"))
	else:
		form = CloseAccountForm()

	return render_to_response(template_name, locals(),
		context_instance=RequestContext(request))

@permission_required("accounts.add_entry")
def add_expense(request, template_name="accounts/add_expense.htm"):
	ActionFormSet = inlineformset_factory(Entry, EntryAction, form=AssetActionForm)
	
	entry = Entry(site=Site.objects.get_current())
	if request.method == "POST":
		form = AddExpenseForm(request.POST, instance=entry)
		action_forms = ActionFormSet(request.POST, instance=entry)
		if form.is_valid() and action_forms.is_valid():
			entry = form.save()
			actions = action_forms.save(commit=False)
			amount = form.cleaned_data['amount']				

			# get all extra actions and subtract them from the base
			for action in actions:
				amount -= action.amount
				action.amount = -action.amount
				
			if amount < 0:
				raise Exception("other assets are more that expected")
			
			entry.save()		
			
			# add the default action
			expense = EntryAction()
			expense.entry = entry
			expense.amount = form.cleaned_data['amount']
			expense.account = form.cleaned_data['expense'] 
				
			asset = EntryAction()
			asset.entry = entry
			asset.amount = -amount
			asset.account = form.cleaned_data['asset']
				
			actions += [expense, asset]
			
			# save entry and actions
			for action in actions:
				action.entry = entry
				action.save()
			
			return HttpResponseRedirect(reverse("summary"))
	else:
		form = AddExpenseForm(instance=entry)
		action_forms = ActionFormSet(instance=entry)
		
	return render_to_response(template_name, locals(),
		context_instance=RequestContext(request))

@permission_required("accounts.add_entry")
def add_revenue(request, template_name="accounts/add_revenue.htm"):
	WithholdingFormSet = inlineformset_factory(Entry, EntryAction, form=WithholdingForm,
		can_delete=False, extra=5)

	entry = Entry(site=Site.objects.get_current())
	if request.method == "POST":
		form = AddRevenueForm(request.POST, instance=entry)
		action_forms = WithholdingFormSet(request.POST, instance=entry)
		if form.is_valid() and action_forms.is_valid():
			entry = form.save(commit=False)
			amount = total = form.cleaned_data['amount']
			entry.save()
			
			actions = action_forms.save()
		
			# get all extra actions and subtract them from the base
			for action in actions:
				amount -= action.amount
			
			# process the budget
			amount, budgeted = form.cleaned_data['budget'].process(entry, total, amount)
			actions += budgeted
			
			# add the default action
			actions += [EntryAction(entry=entry, amount=-total, account=form.cleaned_data['revenue'])]
			if amount > 0:
				actions += [EntryAction(entry=entry, amount=amount, account=form.cleaned_data['default'])]
			
			# save entry and actions
			for action in actions:
				action.save()
			
			return HttpResponseRedirect(reverse("summary"))
	else:
		form = AddRevenueForm(instance=entry)
		action_forms = WithholdingFormSet(instance=entry)

	cash = get_cash()
	
	return render_to_response(template_name, locals(),
		context_instance=RequestContext(request))

