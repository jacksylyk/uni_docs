from django import template
from django.utils.html import format_html

register = template.Library()

@register.filter
def add_class(field, css_class):
    """
    Добавляет CSS класс к полю формы.
    Пример использования: {{ field|addclass:"my-class" }}
    """
    return field.as_widget(attrs={"class": " ".join([field.css_classes(), css_class])})