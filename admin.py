from django.forms.models import BaseModelFormSet
from solardev.accounts.models import Account, AccountBalance, Budget, BudgetItem, Entry, EntryAction
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.forms.models import inlineformset_factory
from django import forms

open_accounts = Account.objects.filter(closed_on__isnull=True)

class BudgetItemForm(forms.ModelForm):
	account = forms.ModelChoiceField(queryset=Account.objects.filter(closed_on__isnull=True))

	def clean_amount(self):
		if 'amount' in self.cleaned_data:
			num = float(self.cleaned_data['amount'])
			if num <= 0:
				raise forms.ValidationError("Budget amounts must be greater than zero")
			return num
	class Meta:
		model = BudgetItem

#class BudgetFormset(inlineformset_factory(Budget, BudgetItem, can_order=True)):
#	def clean(self):
#		total = 0
#		for form in self.forms:
#			if form not in self.deleted_forms:
#				total += float(form.cleaned_data['amount'])
#		if total > 1:
#			raise forms.ValidationError("Hey you can't have a budget with items addinggreater than 100% ofdo that! %s" % (dir(self.cleaned_data), ))

class BudgetItem_Inline(admin.TabularInline):
	model = BudgetItem
	form = BudgetItemForm
#	formset = BudgetFormset
	template = 'accounts/budget.html'


class AccountOptions(admin.ModelAdmin):
	search_fields = ['name']
	list_filter = ['type']
	list_display = ("name", "type", "budgeted_limit", "balance", "closed")

class BudgetOptions(admin.ModelAdmin):
	inlines = [BudgetItem_Inline]

# ------------------------------------------------------------------------------

class EntryActionForm(forms.ModelForm):
	debit = forms.ModelChoiceField(open_accounts)
	credit = forms.ModelChoiceField(open_accounts)
	amount = forms.FloatField()
	class Meta:
		model = EntryAction
		exclude = ["account"]

class EntryActionFormset(BaseModelFormSet):

	def __init__(self, instance=None, *args, **kwargs):
		if instance:
			self.queryset = instance.entryaction_set.filter(amount__gt=0)
		super(EntryActionFormset, self).__init__(*args, **kwargs)

	def clean(self):
		pass
	
class EntryAction_Inline(admin.TabularInline):
	model = EntryAction
	#form = EntryActionForm
	#formset = EntryActionFormset
	
class EntryOptions(admin.ModelAdmin):
	inlines = [EntryAction_Inline]
	list_display = ("date", "description", "error", "total")
	date_hierarchy = 'date'	

#-------------------------------------------------------------------------------

admin.site.register(Account, AccountOptions)
admin.site.register(Budget, BudgetOptions)
admin.site.register(AccountBalance)
admin.site.register(Entry, EntryOptions)

