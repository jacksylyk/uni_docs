# views.py
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import FormView


class CustomLoginView(FormView):
    template_name = 'users/login.html'
    form_class = AuthenticationForm
    success_url = reverse_lazy('index')  # или другая URL после входа

    def dispatch(self, request, *args, **kwargs):
        # Если пользователь уже авторизован, перенаправляем его
        if request.user.is_authenticated:
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Получаем пользователя из формы
        user = form.get_user()

        # Входим в систему
        login(self.request, user)

        # Добавляем сообщение об успешном входе
        messages.success(self.request, f'Добро пожаловать, {user.full_name}!')

        return super().form_valid(form)

    def get_success_url(self):
        # Если есть параметр next, используем его
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return self.success_url


# Альтернативно, можно использовать функциональное представление:
def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')  # AuthenticationForm использует 'username' для email
            password = form.cleaned_data.get('password')

            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {user.full_name}!')

                # Проверяем, есть ли параметр next
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('index')
            else:
                messages.error(request, 'Неверный email или пароль.')
    else:
        form = AuthenticationForm()

    return render(request, 'users/login.html', {'form': form})