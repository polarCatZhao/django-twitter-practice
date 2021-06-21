from utils.memcached_helper import MemcachedHelper
from utils.redis_helper import RedisHelper


def incr_comments_count(sender, instance, created, **kwargs):
    from tweets.models import Tweet
    from django.db.models import F

    if not created:
        return

    # handle new comment
    # queryset.update() doesn't call obj.save() =>
    # doesn't send post_save signal =>
    # doesn't trigger post_save listeners =>
    # doesn't invalidate cached tweet in memcached
    Tweet.objects.filter(id=instance.tweet_id)\
        .update(comments_count=F('comments_count') + 1)
    # It's not necessary to invalidate cached tweet in memcached
    # because comments_count will come from the separately cached counts in redis.
    # MemcachedHelper.invalidate_cached_object(Tweet, instance.tweet_id)
    # RedisHelper.incr_count(instance.tweet, 'comments_count')
    queryset_of_one = Tweet.objects.filter(id=instance.tweet_id)
    RedisHelper.incr_count(queryset_of_one, Tweet.__name__, instance.tweet_id, 'comments_count')
    # correct denormalized counts only appear in 2 places:
    # tweet table and separately cached counts in redis


def decr_comments_count(sender, instance, **kwargs):
    from tweets.models import Tweet
    from django.db.models import F

    # handle comment deletion
    Tweet.objects.filter(id=instance.tweet_id)\
        .update(comments_count=F('comments_count') - 1)
    # It's not necessary to invalidate cached tweet in memcached
    # because comments_count will come from the separately cached counts in redis.
    # MemcachedHelper.invalidate_cached_object(Tweet, instance.tweet_id)
    # RedisHelper.decr_count(instance.tweet, 'comments_count')
    queryset_of_one = Tweet.objects.filter(id=instance.tweet_id)
    RedisHelper.decr_count(queryset_of_one, Tweet.__name__, instance.tweet_id, 'comments_count')
