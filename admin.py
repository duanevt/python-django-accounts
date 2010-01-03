from accounts.forms import WithholdingForm
from accounts.forms import AddRevenueForm
from accounts.forms import AddExpenseForm
from django.contrib.sites.models import Site
from accounts.forms import AssetActionForm
from django.template.context import RequestContext
from django.http import HttpResponseRedirect
from django.forms.models import BaseModelFormSet
from django.contrib.auth.decorators import permission_required
from django.shortcuts import render_to_response
from accounts.forms import get_cash
from django.template.loader import render_to_string
from accounts.models import Account, AccountBalance, Budget, BudgetItem, Entry, EntryAction
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.forms.models import inlineformset_factory
from django import forms
from django.core.urlresolvers import reverse
from django.conf.urls.defaults import *

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
#    def clean(self):
#        total = 0
#        for form in self.forms:
#            if form not in self.deleted_forms:
#                total += float(form.cleaned_data['amount'])
#        if total > 1:
#            raise forms.ValidationError("Hey you can't have a budget with items addinggreater than 100% ofdo that! %s" % (dir(self.cleaned_data), ))

class BudgetItem_Inline(admin.TabularInline):
    model = BudgetItem
    form = BudgetItemForm
#    formset = BudgetFormset
    template = 'accounts/budget.html'


class AccountOptions(admin.ModelAdmin):
    search_fields = ['name']
    list_filter = ['type', 'closed_on']
    list_display = ("name", "type", "budgeted_limit", "balance", "closed")
    ordering = ("name", "closed_on")

    def get_urls(self):
        urls = super(AccountOptions, self).get_urls()
        my_urls = patterns('',
            url(r'^(\d+)/close/$', self.admin_site.admin_view(self.close), name="accounts-close"),
            url(r'^(\d+)/delete/$', "accounts.views.delete_account", name="accounts-delete")
        )

        return my_urls + urls
        
    @permission_required("accounts.delete_account")
    def close(self, request, id, template_name="accounts/close_account.html"):

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
                return HttpResponseRedirect(reverse("accounts-summary"))
        else:
            form = CloseAccountForm()

        return render_to_response(template_name, locals(),
            context_instance=RequestContext(request))

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
    list_display = ("date", "transactions", "error")
    list_filter = ("site", )
    search_fields = ("description",)
    date_hierarchy = 'date'    

    def transactions(self, entry):
        return render_to_string("accounts/journal_entry.html", locals())
    transactions.allow_tags = True

    def get_urls(self):
        urls = super(EntryOptions, self).get_urls()
        my_urls = patterns('',
            url(r'^expense/$', self.admin_site.admin_view(self.expense), name="accounts-add-expense"),
            url(r'^revenue/$', self.admin_site.admin_view(self.revenue), name="accounts-add-revenue"),
        )
        return my_urls + urls
    
    @permission_required("accounts.add_entry")
    def expense(self, request, template_name="accounts/add_expense.html"):
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

                return HttpResponseRedirect(reverse("accounts-summary"))
        else:
            form = AddExpenseForm(instance=entry)
            action_forms = ActionFormSet(instance=entry)

        return render_to_response(template_name, locals(),
            context_instance=RequestContext(request))

    @permission_required("accounts.add_entry")
    def revenue(self, request, template_name="accounts/add_revenue.html"):
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

                return HttpResponseRedirect(reverse("accounts-summary"))
        else:
            form = AddRevenueForm(instance=entry)
            action_forms = WithholdingFormSet(instance=entry)

        cash = get_cash()

        return render_to_response(template_name, locals(),
            context_instance=RequestContext(request))

#-------------------------------------------------------------------------------

admin.site.register(Account, AccountOptions)
admin.site.register(Budget, BudgetOptions)
#admin.site.register(AccountBalance)
admin.site.register(Entry, EntryOptions)

