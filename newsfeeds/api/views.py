from django.utils.decorators import method_decorator
from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed
from newsfeeds.services import NewsFeedService
from ratelimit.decorators import ratelimit
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from utils.paginations import EndlessPagination


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination

    def get_queryset(self):
        return NewsFeed.objects.filter(user_id=self.request.user.id)

    @method_decorator(ratelimit(key='user', rate='5/s', method='GET', block=True))
    def list(self, request):
        normal_feeds = NewsFeedService.get_cached_newsfeeds(request.user.id)
        superstar_feeds = NewsFeedService.get_superstar_newsfeeds(request.user)
        feeds = NewsFeedService.merge_feeds(normal_feeds, superstar_feeds)
        page = self.paginator.paginate_cached_list(feeds, request)
        if page is None:
            queryset = NewsFeed.objects.filter(user=request.user)
            page = self.paginate_queryset(queryset)
        serializer = NewsFeedSerializer(
            page,
            many=True,
            context={'request': request},
        )
        return self.get_paginated_response(serializer.data)
