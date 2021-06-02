from newsfeeds.models import NewsFeed
from friendships.services import FriendshipService
from tweets.models import Tweet
from django.contrib.auth.models import User


class NewsFeedService:

    @classmethod
    def fanout_to_followers(cls, tweet):
        if tweet.user.profile.is_superstar:
            return

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
        followed_user = User.objects.filter(id=followed_user_id).first()
        if followed_user and followed_user.profile.is_superstar:
            return
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
