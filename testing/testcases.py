from comments.models import Comment
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import caches
from django.test import TestCase as DjangoTestCase
from django_hbase.models import HBaseModel
from friendships.services import FriendshipService
from likes.models import Like
from newsfeeds.models import NewsFeed
from rest_framework.test import APIClient
from tweets.models import Tweet
from utils.redis_client import RedisClient


class TestCase(DjangoTestCase):
    hbase_tables_created = False

    def setUp(self):
        self.clear_cache()
        try:
            self.hbase_tables_created = True
            for hbase_model_class in HBaseModel.__subclasses__():
                hbase_model_class.create_table()
        except Exception:
            self.tearDown()
            raise

    def tearDown(self):
        if not self.hbase_tables_created:
            return
        for hbase_model_class in HBaseModel.__subclasses__():
            hbase_model_class.drop_table()

    def clear_cache(self):
        RedisClient.clear()
        caches['testing'].clear()

    @property
    def anonymous_client(self):
        if hasattr(self, '_anonymous_client'):
            return self._anonymous_client
        self._anonymous_client = APIClient()
        return self._anonymous_client

    def create_user(self, username, email=None, password=None):
        if email is None:
            email = '{}@example.com'.format(username)
        if password is None:
            password = 'generic password'
        return User.objects.create_user(username, email, password)

    def create_friendship(self, from_user, to_user):
        return FriendshipService.follow(from_user.id, to_user.id)

    def create_tweet(self, user, content=None):
        if content is None:
            content = 'default tweet content'
        return Tweet.objects.create(user=user, content=content)

    def create_newsfeed(self, user, tweet):
        return NewsFeed.objects.create(
            user=user,
            tweet=tweet,
            created_at=tweet.created_at,
        )

    def create_comment(self, user, tweet, content=None):
        if content is None:
            content = 'default comment content'
        return Comment.objects.create(user=user, tweet=tweet, content=content)

    def create_like(self, user, target):
        instance, _ = Like.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(target.__class__),
            object_id=target.id,
            user=user,
        )
        return instance

    def create_user_and_client(self, *args, **kwargs):
        user = self.create_user(*args, **kwargs)
        client = APIClient()
        client.force_authenticate(user)
        return user, client
