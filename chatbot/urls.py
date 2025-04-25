from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'), 
    path('translate/', views.translate_view, name='translate'),
    path('send_email/', views.send_email_view, name='send_email'),
    path('book-appointment/', views.book_appointment, name='book_appointment'),
    path('available-times/', views.get_available_times, name='get_available_times'),
    path('schedule-appointment/', views.schedule_appointment, name='schedule_appointment'), 
    path('doctors/', views.doctors_list, name='doctors_list'),
    path('get-doctors/', views.get_doctors, name='get_doctors'),
    path('check-availability/', views.check_availability, name='check_availability'),
    path('upload/', views.upload_prescription, name='upload_prescription'),  
]



