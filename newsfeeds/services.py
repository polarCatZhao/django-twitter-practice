from django.contrib.auth.models import User
from friendships.services import FriendshipService
from gatekeeper.models import GateKeeper
from newsfeeds.models import NewsFeed, HBaseNewsFeed
from newsfeeds.tasks import fanout_newsfeeds_main_task
from tweets.models import Tweet
from twitter.cache import USER_NEWSFEEDS_PATTERN
from utils.redis_helper import RedisHelper
from utils.redis_serializers import DjangoModelSerializer, HBaseModelSerializer


def lazy_load_newsfeeds(user_id):
    def _lazy_load(limit):
        if GateKeeper.is_switch_on('switch_newsfeed_to_hbase'):
            return HBaseNewsFeed.filter(prefix=(user_id,), limit=limit, reverse=True)
        return NewsFeed.objects.filter(user_id=user_id).order_by('-created_at')[:limit]
    return _lazy_load


class NewsFeedService:

    @classmethod
    def fanout_to_followers(cls, tweet):
        if tweet.user.profile.is_superstar:
            return

        # print(f'type(tweet.created_at): {type(tweet.created_at)}')  # <class 'datetime.datetime'>
        # print(f'tweet.created_at: {tweet.created_at}')  # 2021-07-23 16:18:10.208012+00:00

        if GateKeeper.is_switch_on('switch_newsfeed_to_hbase'):
            fanout_newsfeeds_main_task.delay(tweet.id, tweet.timestamp, tweet.user_id)
        else:
            fanout_newsfeeds_main_task.delay(tweet.id, tweet.created_at, tweet.user_id)

    @classmethod
    def inject_newsfeeds(cls, user_id, followed_user_id):
        followed_user = User.objects.filter(id=followed_user_id).first()
        if followed_user and followed_user.profile.is_superstar:
            return
        tweets = Tweet.objects.filter(user_id=followed_user_id)
        newsfeeds = [
            NewsFeed(user_id=user_id, tweet=tweet, created_at=tweet.created_at)
            for tweet in tweets
        ]
        NewsFeed.objects.bulk_create(newsfeeds)

        # invalidate redis cache
        key = USER_NEWSFEEDS_PATTERN.format(user_id=user_id)
        RedisHelper.invalidate_cache(key)

    @classmethod
    def remove_newsfeeds(cls, user_id, followed_user_id):
        # feasible query 1
        # It joined the newsfeed table and tweet table
        # newsfeeds = NewsFeed.objects.filter(
        #     user_id=user_id,
        #     tweet__user_id=followed_user_id,
        # )
        # feasible query 2
        tweets = Tweet.objects.filter(user_id=followed_user_id)
        tweet_ids = [tweet.id for tweet in tweets]
        # The ('user', 'tweet') index is not used
        # because the values of IN query are quite scattered.
        NewsFeed.objects.filter(
            user_id=user_id,
            tweet_id__in=tweet_ids,
        ).delete()

        # invalidate redis cache
        key = USER_NEWSFEEDS_PATTERN.format(user_id=user_id)
        RedisHelper.invalidate_cache(key)

    @classmethod
    def get_superstar_newsfeeds(cls, user):
        """
        Returns newsfeeds of tweets posted by the superstars followed by {user}.
        """
        # superstars: a list of User objects
        superstars = FriendshipService.get_followed_superstars(user)
        if user.profile.is_superstar:
            superstars.append(user)
        superstar_ids = [superstar.id for superstar in superstars]
        superstars_tweets = Tweet.objects.filter(
            user_id__in=superstar_ids
        ).order_by('-created_at')
        newsfeeds = [
            NewsFeed(tweet=tweet, user=user, created_at=tweet.created_at)
            for tweet in superstars_tweets
        ]
        return newsfeeds

    @classmethod
    def merge_feeds(cls, normal_feeds, superstar_feeds):
        """
        normal_feeds: a queryset of NewsFeed objects ordered by -created_at
        superstar_feeds: a list of NewsFeed objects ordered by -created_at
        return: a list of NewsFeed objects
        """
        feeds = []
        i, j = 0, 0
        while i < len(normal_feeds) and j < len(superstar_feeds):
            if normal_feeds[i].created_at >= superstar_feeds[j].created_at:
                feeds.append(normal_feeds[i])
                i += 1
            else:
                feeds.append(superstar_feeds[j])
                j += 1

        while i < len(normal_feeds):
            feeds.append(normal_feeds[i])
            i += 1

        while j < len(superstar_feeds):
            feeds.append(superstar_feeds[j])
            j += 1

        return feeds

    @classmethod
    def get_cached_newsfeeds(cls, user_id):
        key = USER_NEWSFEEDS_PATTERN.format(user_id=user_id)
        if GateKeeper.is_switch_on('switch_newsfeed_to_hbase'):
            serializer = HBaseModelSerializer
        else:
            serializer = DjangoModelSerializer
        return RedisHelper.load_objects(key, lazy_load_newsfeeds(user_id), serializer=serializer)

    @classmethod
    def push_newsfeed_to_cache(cls, newsfeed):
        key = USER_NEWSFEEDS_PATTERN.format(user_id=newsfeed.user_id)
        RedisHelper.push_object(key, newsfeed, lazy_load_newsfeeds(newsfeed.user_id))

    @classmethod
    def create(cls, **kwargs):
        if GateKeeper.is_switch_on('switch_newsfeed_to_hbase'):
            newsfeed = HBaseNewsFeed.create(**kwargs)
            # 需要手动触发 cache 更改，因为没有 listener 监听 hbase create
            cls.push_newsfeed_to_cache(newsfeed)
        else:
            # if not isinstance(kwargs['created_at'], datetime):
            #     kwargs['created_at'] = datetime.fromtimestamp(int(kwargs['created_at']) / 10 ** 6, tz=pytz.utc)
            newsfeed = NewsFeed.objects.create(**kwargs)
        return newsfeed

    @classmethod
    def batch_create(cls, batch_params):
        if GateKeeper.is_switch_on('switch_newsfeed_to_hbase'):
            newsfeeds = HBaseNewsFeed.batch_create(batch_params)
        else:
            newsfeeds = [NewsFeed(**params) for params in batch_params]
            NewsFeed.objects.bulk_create(newsfeeds)
        # bulk create does not trigger post_save signal, so push newsfeeds to cache manually
        for newsfeed in newsfeeds:
            cls.push_newsfeed_to_cache(newsfeed)
        return newsfeeds
