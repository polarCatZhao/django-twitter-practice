from django.conf import settings
from django_hbase.models import HBaseModel
from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer, HBaseModelSerializer


class RedisHelper:

    @classmethod
    def _load_objects_to_cache(cls, key, objects, serializer):
        conn = RedisClient.get_connection()

        serialized_list = []
        # 最多只 cache REDIS_LIST_LENGTH_LIMIT 那么多个 objects
        # 超过这个限制的 objects，就去数据库里读取。一般这个限制会比较大，比如 1000
        # 因此翻页翻到 1000 的用户访问量会比较少，从数据库读取也不是大问题
        for obj in objects:
            serialized_data = serializer.serialize(obj)
            serialized_list.append(serialized_data)

        if serialized_list:
            conn.rpush(key, *serialized_list)
            conn.expire(key, settings.REDIS_KEY_EXPIRE_TIME)

    @classmethod
    def load_objects(cls, key, lazy_load_objects, serializer=DjangoModelSerializer):
        conn = RedisClient.get_connection()

        # If {key} exists in cache, get the values and return.
        if conn.exists(key):
            serialized_list = conn.lrange(key, 0, -1)
            objects = []
            for serialized_data in serialized_list:
                deserialized_obj = serializer.deserialize(serialized_data)
                objects.append(deserialized_obj)
            # print(f'cache hit {key}, len(objects)={len(objects)}')
            return objects

        objects = lazy_load_objects(settings.REDIS_LIST_LENGTH_LIMIT)
        cls._load_objects_to_cache(key, objects, serializer)

        # transform it to list to make sure that the return type is always list
        # print(f'cache miss {key}, len(objects)={len(objects)}')
        return list(objects)

    @classmethod
    def push_object(cls, key, obj, lazy_load_objects):
        if isinstance(obj, HBaseModel):
            serializer = HBaseModelSerializer
        else:
            serializer = DjangoModelSerializer
        conn = RedisClient.get_connection()
        # 如果在 cache 里存在，直接把 obj 放在 list 的最前面，然后 trim 一下长度
        if conn.exists(key):
            # print(f'push cache hit {key}')
            serialized_data = serializer.serialize(obj)
            conn.lpush(key, serialized_data)
            conn.ltrim(key, 0, settings.REDIS_LIST_LENGTH_LIMIT - 1)
            return

        # 如果 key 不存在， 直接从数据库里 load
        # 就不走单个 push 的方式加到 cache 里了
        objects = lazy_load_objects(settings.REDIS_LIST_LENGTH_LIMIT)
        cls._load_objects_to_cache(key, objects, serializer)
        # print(f'push cache miss {key}, len={len(objects)}')

    @classmethod
    def invalidate_cache(cls, key):
        conn = RedisClient.get_connection()
        conn.delete(key)

    @classmethod
    def get_count_key(cls, model_name, object_id, attr):
        return '{}.{}:{}'.format(model_name, attr, object_id)

    @classmethod
    def _load_count_to_cache(cls, obj, attr, key, conn):
        obj.refresh_from_db()
        count = getattr(obj, attr)
        conn.set(key, count)
        # We wish the counts to exist in redis forever.
        # It does not take up to much space anyway.
        # conn.expire(key, settings.REDIS_KEY_EXPIRE_TIME)
        return count

    @classmethod
    def incr_count(cls, queryset_of_one, model_name, object_id, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(model_name, object_id, attr)
        if not conn.exists(key):
            obj = queryset_of_one.first()
            cls._load_count_to_cache(obj, attr, key, conn)
            return
        return conn.incr(key)

    @classmethod
    def decr_count(cls, queryset_of_one, model_name, object_id, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(model_name, object_id, attr)
        if not conn.exists(key):
            obj = queryset_of_one.first()
            cls._load_count_to_cache(obj, attr, key, conn)
            return
        return conn.decr(key)

    @classmethod
    def get_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj.__class__.__name__, obj.id, attr)
        count = conn.get(key)
        if count is not None:
            return int(count)

        count = cls._load_count_to_cache(obj, attr, key, conn)
        return count
