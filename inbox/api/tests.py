from notifications.models import Notification
from testing.testcases import TestCase


COMMENT_URL = '/api/comments/'
LIKE_URL = '/api/likes/'
NOTIFICATION_URL = '/api/notifications/'
NOTIFICATION_UNREAD_COUNT_URL = '/api/notifications/unread-count/'
NOTIFICATION_MARK_ALL_AS_READ_URL = '/api/notifications/mark-all-as-read/'


class NotificationTests(TestCase):

    def setUp(self):
        self.linghu, self.linghu_client = self.create_user_and_client('linghu')
        self.dongxie, self.dongxie_client = self.create_user_and_client('dongxie')
        self.dongxie_tweet = self.create_tweet(self.dongxie)

    def test_comment_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        self.linghu_client.post(COMMENT_URL, {
            'tweet_id': self.dongxie_tweet.id,
            'content': 'hi',
        })
        self.assertEqual(Notification.objects.count(), 1)

    def test_like_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        self.linghu_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.dongxie_tweet.id,
        })
        self.assertEqual(Notification.objects.count(), 1)


class NotificationApiTests(TestCase):

    def setUp(self):
        self.linghu, self.linghu_client = self.create_user_and_client('linghu')
        self.dongxie, self.dongxie_client = self.create_user_and_client('dongxie')
        self.linghu_tweet = self.create_tweet(self.linghu)

    def test_unread_count(self):
        self.dongxie_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.linghu_tweet.id,
        })

        response = self.linghu_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['unread_count'], 1)

        comment = self.create_comment(self.linghu, self.linghu_tweet)
        self.dongxie_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })
        response = self.linghu_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.data['unread_count'], 2)

    def test_mark_all_as_read(self):
        self.dongxie_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.linghu_tweet.id,
        })
        comment = self.create_comment(self.linghu, self.linghu_tweet)
        self.dongxie_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })

        response = self.linghu_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.data['unread_count'], 2)

        response = self.linghu_client.get(NOTIFICATION_MARK_ALL_AS_READ_URL)
        self.assertEqual(response.status_code, 405)
        response = self.linghu_client.post(NOTIFICATION_MARK_ALL_AS_READ_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['marked_count'], 2)
        response = self.linghu_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.data['unread_count'], 0)

    def test_list(self):
        self.dongxie_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.linghu_tweet.id,
        })
        comment = self.create_comment(self.linghu, self.linghu_tweet)
        self.dongxie_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })

        # anonymous users cannot visit this url
        response = self.anonymous_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, 403)

        # dongxie cannot see any notifications
        response = self.dongxie_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        # linghu can see two notifications
        response = self.linghu_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)

        # after marking one, linghu can see only one notification
        notification = self.linghu.notifications.first()
        notification.unread = False
        notification.save()
        response = self.linghu_client.get(NOTIFICATION_URL)
        self.assertEqual(response.data['count'], 2)
        response = self.linghu_client.get(NOTIFICATION_URL, {'unread': True})
        self.assertEqual(response.data['count'], 1)
        response = self.linghu_client.get(NOTIFICATION_URL, {'unread': False})
        self.assertEqual(response.data['count'], 1)
