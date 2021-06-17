from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.services import NewsFeedService
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from utils.paginations import EndlessPagination


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination

    def list(self, request):
        normal_feeds = NewsFeedService.get_cached_newsfeeds(request.user.id)
        superstar_feeds = NewsFeedService.get_superstar_newsfeeds(request.user)
        feeds = NewsFeedService.merge_feeds(normal_feeds, superstar_feeds)
        page = self.paginate_queryset(feeds)
        serializer = NewsFeedSerializer(
            page,
            many=True,
            context={'request': request},
        )
        return self.get_paginated_response(serializer.data)
