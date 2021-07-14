from datetime import datetime
from dateutil import parser
from django.conf import settings
from rest_framework.pagination import BasePagination
from rest_framework.response import Response
from utils.time_constants import MAX_TIMESTAMP

import operator
import pytz


DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'


class EndlessPagination(BasePagination):
    page_size = 20

    def __init__(self):
        super(EndlessPagination, self).__init__()
        self.has_next_page = False

    def to_html(self):
        pass

    def paginate_ordered_list(self, reverse_ordered_list, request):
        if 'created_at__gt' in request.query_params:
            created_at__gt = parser.isoparse(request.query_params['created_at__gt'])
            objects = []
            for obj in reverse_ordered_list:
                if obj.created_at > created_at__gt:
                    objects.append(obj)
                else:
                    break
            self.has_next_page = False
            return objects

        index = 0
        if 'created_at__lt' in request.query_params:
            created_at__lt = parser.isoparse(request.query_params['created_at__lt'])
            for index, obj in enumerate(reverse_ordered_list):
                if obj.created_at < created_at__lt:
                    break
            else:
                # 没找到任何满足条件的 objects，返回空数组
                reverse_ordered_list = []
        self.has_next_page = len(reverse_ordered_list) > index + self.page_size
        return reverse_ordered_list[index: index + self.page_size]

    def paginate_queryset(self, queryset, request, view=None):
        if 'created_at__gt' in request.query_params:
            created_at__gt = request.query_params['created_at__gt']
            queryset = queryset.filter(created_at__gt=created_at__gt)
            self.has_next_page = False
            return queryset.order_by('-created_at')

        if 'created_at__lt' in request.query_params:
            created_at__lt = request.query_params['created_at__lt']
            queryset = queryset.filter(created_at__lt=created_at__lt)

        queryset = queryset.order_by('-created_at')[: self.page_size + 1]
        self.has_next_page = len(queryset) > self.page_size
        return queryset[: self.page_size]

    def paginate_hbase(self, hb_model, row_key_prefix, request):
        if 'created_at__gt' in request.query_params:
            created_at__gt = request.query_params['created_at__gt']
            start = (*row_key_prefix, created_at__gt)
            stop = (*row_key_prefix, MAX_TIMESTAMP)
            objects = hb_model.filter(start=start, stop=stop)
            if len(objects) and objects[0].created_at == int(created_at__gt):
                objects = objects[:0:-1]
            else:
                objects = objects[::-1]
            self.has_next_page = False
            return objects

        if 'created_at__lt' in request.query_params:
            created_at__lt = request.query_params['created_at__lt']
            start = (*row_key_prefix, created_at__lt)
            stop = (*row_key_prefix,)
            objects = hb_model.filter(start=start, stop=stop, limit=self.page_size + 2, reverse=True)
            if len(objects) and objects[0].created_at == int(created_at__lt):
                objects = objects[1:]
            if len(objects) > self.page_size:
                self.has_next_page = True
                objects = objects[:-1]
            else:
                self.has_next_page = False
            return objects

        # 没有任何参数，默认加载最新的一页
        prefix = (*row_key_prefix,)
        objects = hb_model.filter(prefix=prefix, limit=self.page_size + 1, reverse=True)
        if len(objects) > self.page_size:
            self.has_next_page = True
            objects = objects[:-1]
        else:
            self.has_next_page = False
        return objects

    def paginate_cached_list(self, cached_list, request):
        paginated_list = self.paginate_ordered_list(cached_list, request)
        # 如果是上翻页， paginated_list 里是所有的最新的数据，直接返回
        if 'created_at__gt' in request.query_params:
            return paginated_list
        # 如果还有下一页，说明 cached_list 里的数据还没有取完，也直接返回
        if self.has_next_page:
            return paginated_list
        # 如果 cached_list 的长度不足最大限制，说明 cached_list 里已经是所有数据了
        if len(cached_list) < settings.REDIS_LIST_LENGTH_LIMIT:
            return paginated_list
        # 如果进入这里，说明可能存在在数据库里没有 load 在 cache 里的数据，需要直接去数据库查询
        return None

    def get_paginated_response(self, data):
        return Response({
            'has_next_page': self.has_next_page,
            'results': data,
        })


class ListForPagination:
    """
    Wraps a list to make it look like a QuerySet so that it can be used in
    pagination.
    """

    def __init__(self, a_list):
        self._list = a_list

    def filter(self, created_at__gt=None, created_at__lt=None):
        if created_at__gt is not None:
            datetime_string = created_at__gt
            compare_function = operator.__gt__
        elif created_at__lt is not None:
            datetime_string = created_at__lt
            compare_function = operator.__lt__
        datetime_string = datetime_string.split('+')[0]
        datetime_object = datetime.strptime(datetime_string, DATETIME_FORMAT)
        datetime_object = datetime_object.replace(tzinfo=pytz.utc)
        filtered_list = list(filter(
            lambda x: compare_function(x.created_at, datetime_object),
            self._list,
        ))
        return ListForPagination(filtered_list)

    def order_by(self, key='-created_at'):
        reverse = key.startswith('-')
        key = key.strip('-')
        sorted_list = list(sorted(
            self._list,
            key=lambda x: getattr(x, key),
            reverse=reverse,
        ))
        return ListForPagination(sorted_list)

    def __getitem__(self, item):
        start, stop, step = item.start, item.stop, item.step
        return ListForPagination(self._list[start:stop:step])

    def __len__(self):
        return len(self._list)

    def to_list(self):
        return list(self._list)
