from django.test import TestCase
from django.contrib.auth.models import User
from datetime import timedelta
from tweets.models import Tweet
from utils.time_helpers import utc_now


class TweetTests(TestCase):

    def test_hours_to_now(self):
        linghu = User.objects.create_user(username='linghu')
        tweet = Tweet.objects.create(user=linghu, content='hello world')
        tweet.created_at = utc_now() - timedelta(hours=10)
        tweet.save()
        self.assertEqual(tweet.hours_to_now, 10)

