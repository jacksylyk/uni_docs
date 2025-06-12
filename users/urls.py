from django.urls import path
from django.contrib.auth import views as auth_views

from users import views

app_name = 'users'

urlpatterns = [
    # Используя собственное представление
    path('login/', views.CustomLoginView.as_view(), name='login'),

    # Или используя функциональное представление
    # path('login/', views.login_view, name='login'),

    # Выход из системы
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),

    # Другие URL для пользователей
    # path('register/', views.register, name='register'),
]