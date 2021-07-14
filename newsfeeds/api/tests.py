from django.conf import settings
from friendships.models import Friendship
from newsfeeds.models import NewsFeed
from newsfeeds.services import NewsFeedService
from rest_framework.test import APIClient
from testing.testcases import TestCase
from utils.paginations import EndlessPagination


NEWSFEEDS_URL = '/api/newsfeeds/'
POST_TWEETS_URL = '/api/tweets/'
FOLLOW_URL = '/api/friendships/{}/follow/'


class NewsFeedApiTests(TestCase):

    def setUp(self):
        super(NewsFeedApiTests, self).setUp()
        self.linghu = self.create_user('linghu')
        self.linghu_client = APIClient()
        self.linghu_client.force_authenticate(self.linghu)

        self.dongxie = self.create_user('dongxie')
        self.dongxie_client = APIClient()
        self.dongxie_client.force_authenticate(self.dongxie)

        # create followings and followers for dongxie
        for i in range(2):
            follower = self.create_user('dongxie_follower{}'.format(i))
            self.create_friendship(from_user=follower, to_user=self.dongxie)
        for i in range(3):
            following = self.create_user('dongxie_following{}'.format(i))
            self.create_friendship(from_user=self.dongxie, to_user=following)

    def test_list(self):
        # 需要登录
        response = self.anonymous_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, 403)
        # 不能用 post
        response = self.linghu_client.post(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, 405)
        # 一开始啥都没有
        response = self.linghu_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        # 自己发的信息是可以看到的
        self.linghu_client.post(POST_TWEETS_URL, {'content': 'Hello World'})
        response = self.linghu_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 1)
        # 关注之后可以看到别人发的
        self.linghu_client.post(FOLLOW_URL.format(self.dongxie.id))
        response = self.dongxie_client.post(POST_TWEETS_URL, {
            'content': 'Hello Twitter',
        })
        posted_tweet_id = response.data['id']
        response = self.linghu_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['tweet']['id'], posted_tweet_id)

    def test_pagination(self):
        page_size = EndlessPagination.page_size
        followed_user = self.create_user('followed')
        newsfeeds = []
        for i in range(page_size * 2):
            tweet = self.create_tweet(followed_user)
            newsfeed = self.create_newsfeed(user=self.linghu, tweet=tweet)
            newsfeeds.append(newsfeed)

        newsfeeds = newsfeeds[::-1]

        # pull the first page
        response = self.linghu_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.data['has_next_page'], True)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['results'][0]['id'], newsfeeds[0].id)
        self.assertEqual(response.data['results'][1]['id'], newsfeeds[1].id)
        self.assertEqual(
            response.data['results'][page_size - 1]['id'],
            newsfeeds[page_size - 1].id,
        )

        # pull the second page
        response = self.linghu_client.get(NEWSFEEDS_URL, {
            'created_at__lt': newsfeeds[page_size - 1].created_at,
        })
        self.assertEqual(response.data['has_next_page'], False)
        results = response.data['results']
        self.assertEqual(len(results), page_size)
        self.assertEqual(results[0]['id'], newsfeeds[page_size].id)
        self.assertEqual(results[1]['id'], newsfeeds[page_size + 1].id)
        self.assertEqual(
            results[page_size - 1]['id'],
            newsfeeds[2 * page_size - 1].id,
        )

        # pull latest newsfeeds
        response = self.linghu_client.get(
            NEWSFEEDS_URL,
            {'created_at__gt': newsfeeds[0].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 0)

        tweet = self.create_tweet(followed_user)
        new_newsfeed = self.create_newsfeed(user=self.linghu, tweet=tweet)

        response = self.linghu_client.get(
            NEWSFEEDS_URL,
            {'created_at__gt': newsfeeds[0].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], new_newsfeed.id)

    def test_user_cache(self):
        # create dongxie's profile in database and load it in cache
        profile = self.dongxie.profile
        profile.nickname = 'huanglaoxie'
        # invalidate profile cache
        profile.save()

        self.assertEqual(self.linghu.username, 'linghu')
        self.create_newsfeed(self.dongxie, self.create_tweet(self.linghu))
        self.create_newsfeed(self.dongxie, self.create_tweet(self.dongxie))

        # get linghu user: from db, get linghu profile: from db
        # get dongxie user: from db, get dongxie profile: from db
        response = self.dongxie_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'dongxie')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'huanglaoxie')
        self.assertEqual(results[1]['tweet']['user']['username'], 'linghu')

        self.linghu.username = 'linghuchong'
        # invalidate cached linghu
        self.linghu.save()
        profile.nickname = 'huangyaoshi'
        # invalidate cached dongxie' profile
        profile.save()
        # cache: linghu profile, dongxie user

        # get linghu user: from db, get linghu profile: from cache
        # get dongxie user: from cache, get dongxie profile: from db
        response = self.dongxie_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'dongxie')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'huangyaoshi')
        self.assertEqual(results[1]['tweet']['user']['username'], 'linghuchong')

    def test_tweet_cache(self):
        tweet = self.create_tweet(self.linghu, 'content1')
        self.create_newsfeed(self.dongxie, tweet)
        # get tweet from db
        response = self.dongxie_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'linghu')
        self.assertEqual(results[0]['tweet']['content'], 'content1')

        # get tweet from cache
        response = self.dongxie_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'linghu')
        self.assertEqual(results[0]['tweet']['content'], 'content1')

        # update username
        self.linghu.username = 'linghuchong'
        self.linghu.save()
        # get tweet from cache
        response = self.dongxie_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'linghuchong')

        # update content
        tweet.content = 'content2'
        tweet.save()
        # get tweet from db
        response = self.dongxie_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['content'], 'content2')

    def _paginate_to_get_newsfeeds(self, client):
        # paginate until the end
        # first get data from cache and then from database
        response = client.get(NEWSFEEDS_URL)
        results = response.data['results']
        while response.data['has_next_page']:
            created_at__lt = response.data['results'][-1]['created_at']
            response = client.get(NEWSFEEDS_URL, {'created_at__lt': created_at__lt})
            results.extend(response.data['results'])
        return results

    def test_redis_list_limit(self):
        list_limit = settings.REDIS_LIST_LENGTH_LIMIT
        page_size = 20
        users = [self.create_user(f'user{i}') for i in range(5)]
        newsfeeds = []
        for i in range(list_limit + page_size):
            tweet = self.create_tweet(user=users[i % 5], content=f'feed{i}')
            feed = self.create_newsfeed(self.linghu, tweet)
            newsfeeds.append(feed)
        newsfeeds = newsfeeds[::-1]

        # only cached list_limit objects
        cached_newsfeeds = NewsFeedService.get_cached_newsfeeds(self.linghu.id)
        self.assertEqual(len(cached_newsfeeds), list_limit)
        queryset = NewsFeed.objects.filter(user=self.linghu)
        self.assertEqual(queryset.count(), list_limit + page_size)

        results = self._paginate_to_get_newsfeeds(self.linghu_client)
        self.assertEqual(len(results), list_limit + page_size)
        for i in range(list_limit + page_size):
            self.assertEqual(newsfeeds[i].id, results[i]['id'])

        # a followed user create a new tweet
        self.create_friendship(self.linghu, self.dongxie)
        new_tweet = self.create_tweet(self.dongxie, 'a new tweet')
        NewsFeedService.fanout_to_followers(new_tweet)

        def _test_newsfeeds_after_new_feed_pushed():
            results = self._paginate_to_get_newsfeeds(self.linghu_client)
            self.assertEqual(len(results), list_limit + page_size + 1)
            self.assertEqual(results[0]['tweet']['id'], new_tweet.id)
            for i in range(list_limit + page_size):
                self.assertEqual(newsfeeds[i].id, results[i + 1]['id'])

        _test_newsfeeds_after_new_feed_pushed()

        # cache expired
        self.clear_cache()
        _test_newsfeeds_after_new_feed_pushed()


class NewsFeedPushPlusPullApiTests(TestCase):

    def setUp(self):
        super(NewsFeedPushPlusPullApiTests, self).setUp()
        self.user1, self.user1_client = self.create_user_and_client('john')
        self.user2, self.user2_client = self.create_user_and_client('teresa')
        self.star1, self.star1_client = self.create_user_and_client('star1')
        self.star1.profile.is_superstar = True
        self.star1.profile.save()
        self.star2, self.star2_client = self.create_user_and_client('star2')
        self.star2.profile.is_superstar = True
        self.star2.profile.save()

    def test_push_plus_pull_model(self):
        # user1 followed user2, star2
        # star1 followed user2, star2
        response = self.user1_client.post(FOLLOW_URL.format(self.user2.id))
        self.assertEqual(response.status_code, 201)
        self.user1_client.post(FOLLOW_URL.format(self.star2.id))
        self.star1_client.post(FOLLOW_URL.format(self.user2.id))
        self.star1_client.post(FOLLOW_URL.format(self.star2.id))

        # test the newsfeeds of user1
        # user2 posts a tweet
        response = self.user2_client.post(POST_TWEETS_URL, {'content': 'nothing'})
        self.assertEqual(response.status_code, 201)
        tweet_id1 = response.data['id']
        self.assertEqual(
            NewsFeed.objects.filter(user=self.user1, tweet_id=tweet_id1).exists(),
            True,
        )
        response = self.user1_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['tweet']['id'], tweet_id1)

        # star2 posts a tweet
        response = self.star2_client.post(POST_TWEETS_URL, {'content': 'nothing'})
        self.assertEqual(response.status_code, 201)
        tweet_id2 = response.data['id']
        self.assertEqual(
            NewsFeed.objects.filter(user=self.user1, tweet_id=tweet_id2).exists(),
            False,
        )
        response = self.user1_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['tweet']['id'], tweet_id2)

        # user1 herself posts a tweet
        response = self.user1_client.post(POST_TWEETS_URL, {'content': 'nothing'})
        self.assertEqual(response.status_code, 201)
        tweet_id3 = response.data['id']
        self.assertEqual(
            NewsFeed.objects.filter(user=self.user1, tweet_id=tweet_id3).exists(),
            True,
        )
        response = self.user1_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(response.data['results'][0]['tweet']['id'], tweet_id3)

        # user2 can only see her own tweet in her newsfeeds
        response = self.user2_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(
            response.data['results'][0]['tweet']['user']['id'],
            self.user2.id,
        )

        # star2 can only see her own tweet in her newsfeeds
        response = self.star2_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(
            response.data['results'][0]['tweet']['user']['id'],
            self.star2.id,
        )

        # test the newsfeeds of star1
        # user2's tweet was pushed to star1
        self.assertEqual(
            NewsFeed.objects.filter(user=self.star1, tweet_id=tweet_id1).exists(),
            True,
        )
        # star2's tweet was not pushed to star1
        self.assertEqual(
            NewsFeed.objects.filter(user=self.star1, tweet_id=tweet_id2).exists(),
            False,
        )
        # star1 can see the tweets of user2 and star2 in her newsfeeds
        response = self.star1_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(
            response.data['results'][0]['tweet']['user']['id'],
            self.star2.id,
        )
        self.assertEqual(
            response.data['results'][1]['tweet']['user']['id'],
            self.user2.id,
        )

        # star1 posts a tweet
        response = self.star1_client.post(POST_TWEETS_URL, {'content': 'nothing'})
        self.assertEqual(response.status_code, 201)
        tweet_id4 = response.data['id']
        self.assertEqual(
            NewsFeed.objects.filter(user=self.star1, tweet_id=tweet_id4).exists(),
            False,
        )
        response = self.star1_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(response.data['results'][0]['tweet']['id'], tweet_id4)

    def test_inject_newsfeeds_when_follow(self):
        # user2 and star2 tweeted
        response = self.user2_client.post(POST_TWEETS_URL, {'content': 'nothing'})
        tweet_id1 = response.data['id']
        response = self.star2_client.post(POST_TWEETS_URL, {'content': 'nothing'})
        tweet_id2 = response.data['id']

        # When user1 followed user2,
        # user2's tweets will be injected to user1's newsfeeds.
        self.assertEqual(
            NewsFeed.objects.filter(user=self.user1, tweet_id=tweet_id1).exists(),
            False,
        )
        response = self.user1_client.post(FOLLOW_URL.format(self.user2.id))
        self.assertEqual(
            NewsFeed.objects.filter(user=self.user1, tweet_id=tweet_id1).exists(),
            True,
        )

        # When user1 followed star2,
        # star2's tweets will not be injected to user1's newsfeeds.
        self.assertEqual(
            NewsFeed.objects.filter(user=self.user1, tweet_id=tweet_id2).exists(),
            False,
        )
        response = self.user1_client.post(FOLLOW_URL.format(self.star2.id))
        self.assertEqual(
            NewsFeed.objects.filter(user=self.user1, tweet_id=tweet_id2).exists(),
            False,
        )
