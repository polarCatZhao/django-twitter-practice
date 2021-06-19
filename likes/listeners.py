from utils.memcached_helper import MemcachedHelper
from utils.redis_helper import RedisHelper


def incr_likes_count(sender, instance, created, **kwargs):
    from tweets.models import Tweet
    from django.db.models import F

    if not created:
        return

    model_class = instance.content_type.model_class()
    if model_class != Tweet:
        # TODO HOMEWORK 给 Comment 使用类似的方法进行 likes_count 的统计
        return

    Tweet.objects.filter(id=instance.object_id).update(likes_count=F('likes_count') + 1)
    # It's not necessary to invalidate cached tweet in memcached
    # because likes_count will come from the separately cached counts in redis.
    # MemcachedHelper.invalidate_cached_object(Tweet, instance.object_id)
    tweet = instance.content_object
    RedisHelper.incr_count(tweet, 'likes_count')
    # correct denormalized counts only appear in 2 places:
    # tweet table and separately cached counts in redis


def decr_likes_count(sender, instance, **kwargs):
    from tweets.models import Tweet
    from django.db.models import F

    model_class = instance.content_type.model_class()
    if model_class != Tweet:
        # TODO HOMEWORK 给 Comment 使用类似的方法进行 likes_count 的统计
        return

    # handle tweet likes cancel
    Tweet.objects.filter(id=instance.object_id).update(likes_count=F('likes_count') - 1)
    # It's not necessary to invalidate cached tweet in memcached
    # because likes_count will come from the separately cached counts in redis.
    # MemcachedHelper.invalidate_cached_object(Tweet, instance.object_id)
    tweet = instance.content_object
    RedisHelper.decr_count(tweet, 'likes_count')
