from django.utils.decorators import method_decorator
from inbox.services import NotificationService
from likes.api.serializers import (
    LikeSerializer,
    LikeSerializerForCreate,
    LikeSerializerForCancel,
)
from ratelimit.decorators import ratelimit
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from utils.decorators import required_params


class LikeViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = LikeSerializerForCreate

    @method_decorator(ratelimit(key='user', rate='10/s', method='POST', block=True))
    @required_params(method='POST', params=['content_type', 'object_id'])
    def create(self, request):
        serializer = LikeSerializerForCreate(
            data=request.data,
            context={'request': request},
        )
        if not serializer.is_valid():
            return Response({
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        instance, created = serializer.get_or_create()
        if created:
            NotificationService.send_like_notification(instance)
        return Response(
            LikeSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    @action(methods=['POST'], detail=False)
    @method_decorator(ratelimit(key='user', rate='10/s', method='POST', block=True))
    @required_params(method='POST', params=['content_type', 'object_id'])
    def cancel(self, request):
        serializer = LikeSerializerForCancel(
            data=request.data,
            context={'request': request},
        )
        if not serializer.is_valid():
            return Response({
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        serializer.cancel()
        return Response({'success': True}, status=status.HTTP_200_OK)
