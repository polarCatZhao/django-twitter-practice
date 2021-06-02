from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True)
    avatar = models.FileField(null=True)
    nickname = models.CharField(null=True, max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # TODO: Right now the is_superstar status can't be changed.
    #   When a non-superstar is made a superstar,
    #   all the tweets he posted need to be removed from the NewsFeed table.
    is_superstar = models.BooleanField(default=False)

    def __str__(self):
        return '{} {}'.format(self.user, self.nickname)


def get_profile(user):
    if hasattr(user, '_cached_user_profile'):
        return getattr(user, '_cached_user_profile')
    profile, _ = UserProfile.objects.get_or_create(user=user)
    setattr(user, '_cached_user_profile', profile)
    return profile


User.profile = property(get_profile)
