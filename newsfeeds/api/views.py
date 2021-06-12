from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed
from newsfeeds.services import NewsFeedService
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from utils.paginations import EndlessPagination, ListForPagination


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination

    def get_queryset(self):
        return NewsFeed.objects.filter(user=self.request.user)

    def paginate_queryset(self, list_):
        list_for_pagination = ListForPagination(list_)
        new_list_for_pagination = super().paginate_queryset(list_for_pagination)
        list_of_newsfeeds = new_list_for_pagination.to_list()
        return list_of_newsfeeds

    def list(self, request):
        normal_feeds = self.get_queryset()
        superstar_feeds = NewsFeedService.get_superstar_newsfeeds(request.user)
        feeds = NewsFeedService.merge_feeds(normal_feeds, superstar_feeds)
        page = self.paginate_queryset(feeds)
        serializer = NewsFeedSerializer(
            page,
            many=True,
            context={'request': request},
        )
        return self.get_paginated_response(serializer.data)
