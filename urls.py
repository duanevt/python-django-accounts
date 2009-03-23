from django.conf.urls.defaults import *
from views import *

urlpatterns = patterns('',
    url(r'^account/new/', update_account, name="accounts-add-account"),
    url(r'^account/(\d+)/', update_account, name="accounts-change-account"),
    url(r'^journal/', journal, name="journal"),
    url(r'^ledger/(?P<id>\d+)/', ledger, name="ledger"), 
    url(r'^expense/new/', add_expense, name="add_expense"),
    url(r'^revenue/new/', add_revenue, name="add_revenue"),
	url(r'^close/(\d+)/', close_account, name="accounts-close"),
    url(r'^', summary, name="summary"), 
)
