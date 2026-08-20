from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Tickets
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/new/', views.ticket_create, name='ticket_create'),
    path('tickets/<str:request_id>/', views.ticket_detail, name='ticket_detail'),

    # Knowledge Base
    path('knowledge-base/', views.knowledge_base, name='knowledge_base'),

    # Manager
    path('manager/workload/', views.manager_workload, name='manager_workload'),
]
