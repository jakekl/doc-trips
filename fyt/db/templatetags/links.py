from functools import wraps

from django import template
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse

from fyt.db.models import TripsYear
from fyt.db.urlhelpers import reverse_update_url, reverse_delete_url, reverse_create_url, reverse_detail_url

register = template.Library()

def _make_link(url, text):
    """ Format a link. """
    html = '<a href="{}">{}</a>'.format(url, text)
    return mark_safe(html)

make_link = _make_link


def pass_null(func):
    """ 
    Decorator

    If the first argument is False, return the
    argument. Otherwise call func.
    """
    def wrapper(obj, *args, **kwargs):
        if not obj:
            return obj
        return func(obj, *args, **kwargs)
    # used by django template parser to introspect args
    wrapper._decorated_function = getattr(func, '_decorated_function', func)
    return wraps(func)(wrapper)


@register.filter
@pass_null
def edit_link(db_object, text=None):
    """ Insert html link to edit db_object. """
    if text is None:
        text = 'edit'
    return _make_link(reverse_update_url(db_object), text)

        
@register.filter
@pass_null
def delete_link(db_object, text=None):
    """ Insert html link to delete db_object. """
    if text is None:
        text = 'delete'
    return _make_link(reverse_delete_url(db_object), text)


@register.simple_tag
def create_url(model, trips_year_str):
    """ Give the create url for the given model and trips_year """

    trips_year = TripsYear.objects.get(pk=trips_year_str)

    return reverse_create_url(model, trips_year)
   

@register.filter
@pass_null
def detail_link(db_obj, text=None):
    """
    Html link to detailed view for object.
    """
    def to_str(obj):
        if text is None:
            return str(obj)
        return text

    to_link = lambda obj: _make_link(reverse_detail_url(obj), to_str(obj))
    return mark_safe(', '.join(map(to_link, as_list(db_obj))))


# Lifted from googlemaps.convert

def as_list(arg):
    """
    Coerces arg into a list. If arg is already list-like, returns arg.
    Otherwise, returns a one-element list containing arg.
    """
    if _is_list(arg):
        return arg
    return [arg]


def _is_list(arg):
    """
    Checks if arg is list-like. This excludes strings and dicts.
    """
    if isinstance(arg, dict):
        return False
    if isinstance(arg, str): # Python 3-only, as str has __iter__
        return False
    return (not _has_method(arg, "strip")
            and _has_method(arg, "__getitem__")
            or _has_method(arg, "__iter__"))


def _has_method(arg, method):
    """
    Returns true if the given object has a method with the given name.
    """
    return hasattr(arg, method) and callable(getattr(arg, method))