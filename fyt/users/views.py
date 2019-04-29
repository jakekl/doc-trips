from django.contrib import auth
from django.contrib.auth.mixins import LoginRequiredMixin
from vanilla import UpdateView

from fyt.users.models import DartmouthUser, UserProfile
from fyt.utils.forms import crispify


class UpdateEmail(LoginRequiredMixin, UpdateView):
    model = DartmouthUser
    fields = ['email']
    template_name = 'users/email_form.html'

    def get_object(self):
        return self.request.user

    def get_form(self, **kwargs):
        return crispify(super().get_form(**kwargs), 'Update')

    def get_success_url(self):
        return self.request.GET.get(auth.REDIRECT_FIELD_NAME, '/')


class UpdateProfile(LoginRequiredMixin, UpdateView):
    model = UserProfile
    fields = ['photo']
    template_name = 'users/profile_form.html'

    def get_object(self):
        return self.request.user

    def get_form(self, **kwargs):
        return crispify(super().get_form(**kwargs), 'Update')

    # TODO: return next redirect
    def get_success_url(self):
        return self.request.path
