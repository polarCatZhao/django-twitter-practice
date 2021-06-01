from newsfeeds.models import NewsFeed
from friendships.services import FriendshipService
from tweets.models import Tweet


class NewsFeedService:

    @classmethod
    def fanout_to_followers(cls, tweet):
        newsfeeds = [
            NewsFeed(user=follower, tweet=tweet, created_at=tweet.created_at)
            for follower in FriendshipService.get_followers(tweet.user)
        ]
        newsfeeds.append(NewsFeed(
            user=tweet.user,
            tweet=tweet,
            created_at=tweet.created_at,
        ))
        NewsFeed.objects.bulk_create(newsfeeds)

    @classmethod
    def inject_newsfeeds(cls, user_id, followed_user_id):
        tweets = Tweet.objects.filter(user_id=followed_user_id)
        newsfeeds = [
            NewsFeed(user_id=user_id, tweet=tweet, created_at=tweet.created_at)
            for tweet in tweets
        ]
        NewsFeed.objects.bulk_create(newsfeeds)

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
