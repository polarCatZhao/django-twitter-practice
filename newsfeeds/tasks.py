from celery import shared_task
from dateutil import parser
from friendships.services import FriendshipService
from newsfeeds.constants import FANOUT_BATCH_SIZE
from utils.time_constants import ONE_HOUR


@shared_task(routing_key='newsfeeds', time_limit=ONE_HOUR)
def fanout_newsfeeds_batch_task(tweet_id, created_at, follower_ids):
    # import placed inside to avoid circular dependency
    from newsfeeds.services import NewsFeedService

    # if not GateKeeper.is_switch_on('switch_newsfeed_to_hbase'):
    #     created_at = datetime.fromtimestamp(created_at / 10 ** 6, tz=pytz.utc)
    try:
        created_at = parser.isoparse(created_at)
    except TypeError:
        pass

    batch_params = [
        {'user_id': follower_id, 'created_at': created_at, 'tweet_id': tweet_id}
        for follower_id in follower_ids
    ]
    newsfeeds = NewsFeedService.batch_create(batch_params)
    return "{} newsfeeds created.".format(len(newsfeeds))


@shared_task(routing_key='default', time_limit=ONE_HOUR)
def fanout_newsfeeds_main_task(tweet_id, created_at, tweet_user_id):
    # print('type(created_at): ', type(created_at)) # type(created_at) is int
    # print(f'type(created_at): {type(created_at)}') # type(created_at) is str
    # print(f'created_at: {created_at}') # created_at is 2021-07-23T15:32:06.657243Z
    # from newsfeeds.models import NewsFeed
    # NewsFeed.objects.create(tweet_id=tweet_id, user_id=tweet_user_id, created_at=created_at) # created_at can be str

    # import placed inside to avoid circular dependency
    from newsfeeds.services import NewsFeedService

    # if GateKeeper.is_switch_on('switch_newsfeed_to_hbase'):
    #     created_at_param = created_at
    # else:
    #     created_at_param = datetime.fromtimestamp(created_at / 10 ** 6, tz=pytz.utc)
    try:
        created_at = parser.isoparse(created_at)
    except TypeError:
        pass

    # 将推给自己的 Newsfeed 率先创建，确保自己能最快看到
    NewsFeedService.create(
        user_id=tweet_user_id,
        tweet_id=tweet_id,
        created_at=created_at,
    )

    # 获得所有的 follower ids，按照 batch size 拆分开
    follower_ids = FriendshipService.get_follower_ids(tweet_user_id)
    index = 0
    while index < len(follower_ids):
        batch_ids = follower_ids[index: index + FANOUT_BATCH_SIZE]
        fanout_newsfeeds_batch_task.delay(tweet_id, created_at, batch_ids)
        index += FANOUT_BATCH_SIZE

    return '{} newsfeeds going to fanout, {} batches created.'.format(
        len(follower_ids),
        (len(follower_ids) - 1) // FANOUT_BATCH_SIZE + 1,
    )
