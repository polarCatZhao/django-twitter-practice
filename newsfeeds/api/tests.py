from friendships.models import Friendship
from newsfeeds.models import NewsFeed
from rest_framework.test import APIClient
from testing.testcases import TestCase
from utils.paginations import EndlessPagination


NEWSFEEDS_URL = '/api/newsfeeds/'
POST_TWEETS_URL = '/api/tweets/'
FOLLOW_URL = '/api/friendships/{}/follow/'


class NewsFeedApiTests(TestCase):

    def setUp(self):
        self.linghu = self.create_user('linghu')
        self.linghu_client = APIClient()
        self.linghu_client.force_authenticate(self.linghu)

        self.dongxie = self.create_user('dongxie')
        self.dongxie_client = APIClient()
        self.dongxie_client.force_authenticate(self.dongxie)

        # create followings and followers for dongxie
        for i in range(2):
            follower = self.create_user('dongxie_follower{}'.format(i))
            Friendship.objects.create(from_user=follower, to_user=self.dongxie)
        for i in range(3):
            following = self.create_user('dongxie_following{}'.format(i))
            Friendship.objects.create(from_user=self.dongxie, to_user=following)

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


class NewsFeedPushPlusPullApiTests(TestCase):

    def setUp(self):
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
