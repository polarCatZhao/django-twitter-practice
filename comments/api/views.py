from rest_framework import viewsets, status
from comments.api.serializers import (
    CommentSerializerForCreate,
    CommentSerializer,
    CommentSerializerForUpdate,
)
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from comments.api.permissions import IsObjectOwner
from comments.models import Comment
from tweets.models import Tweet


class CommentViewSet(viewsets.GenericViewSet):
    serializer_class = CommentSerializerForCreate
    queryset = Comment.objects.all()
    filterset_fields = ('tweet_id',)

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        if self.action in ['update', 'destroy']:
            return [IsAuthenticated(), IsObjectOwner()]
        return [AllowAny()]

    def create(self, request):
        data = {
            'user_id': request.user.id,
            'tweet_id': request.data.get('tweet_id'),
            'content': request.data.get('content'),
        }
        serializer = CommentSerializerForCreate(data=data)
        if not serializer.is_valid():
            return Response({
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        comment = serializer.save()
        return Response(
            CommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        # POST /api/comments/<pk>/
        comment = self.get_object()
        serializer = CommentSerializerForUpdate(comment, data=request.data)
        if not serializer.is_valid():
            return Response({
                'message': 'Please check input',
            }, status=status.HTTP_400_BAD_REQUEST)

        updated_comment = serializer.save()
        return Response(
            CommentSerializer(updated_comment).data,
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        deleted, _ = comment.delete()
        return Response({
            'success': True,
            'deleted': deleted,
        }, status=status.HTTP_200_OK)

    def list(self, request):
        if 'tweet_id' not in request.query_params:
            return Response({
                'message': 'missing tweet_id in request',
                'success': False,
            }, status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset()
        comments = self.filter_queryset(queryset).order_by('created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response(
            {'comments': serializer.data},
            status=status.HTTP_200_OK,
        )




