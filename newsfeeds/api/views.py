from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from newsfeeds.models import NewsFeed
from newsfeeds.api.serializers import NewsFeedSerializer
from rest_framework.response import Response
from newsfeeds.services import NewsFeedService


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return NewsFeed.objects.filter(user=self.request.user)

    def list(self, request):
        normal_feeds = self.get_queryset()
        superstar_feeds = NewsFeedService.get_superstar_newsfeeds(request.user)
        feeds = NewsFeedService.merge_feeds(normal_feeds, superstar_feeds)
        serializer = NewsFeedSerializer(
            feeds,
            many=True,
            context={'request': request},
        )
        return Response({
            'newsfeeds': serializer.data,
        }, status=status.HTTP_200_OK)
