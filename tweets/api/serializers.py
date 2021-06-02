from accounts.api.serializers import UserSerializerForTweet
from comments.api.serializers import CommentSerializer
from likes.api.serializers import LikeSerializer
from likes.services import LikeService
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from tweets.constants import TWEET_PHOTOS_UPLOAD_LIMIT
from tweets.models import Tweet
from tweets.services import TweetService


class BaseTweetSerializer(serializers.ModelSerializer):
    user = UserSerializerForTweet()
    comments_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    has_liked = serializers.SerializerMethodField()
    photo_urls = serializers.SerializerMethodField()

    class Meta:
        model = Tweet
        fields = (
            'id',
            'user',
            'content',
            'created_at',
            'comments_count',
            'likes_count',
            'has_liked',
            'photo_urls',
        )

    def get_likes_count(self, obj):
        return obj.like_set.count()

    def get_comments_count(self, obj):
        return obj.comment_set.count()

    def get_has_liked(self, obj):
        return LikeService.has_liked(self.context['request'].user, obj)

    def get_photo_urls(self, obj):
        photo_urls = []
        for photo in obj.tweetphoto_set.all().order_by('order'):
            photo_urls.append(photo.file.url)
        return photo_urls


class RetweetSerializer(BaseTweetSerializer):
    pass


class TweetSerializer(BaseTweetSerializer):
    retweet_from = RetweetSerializer()

    class Meta:
        model = Tweet
        fields = (
            'id',
            'user',
            'content',
            'created_at',
            'comments_count',
            'likes_count',
            'has_liked',
            'photo_urls',
            'retweet_from',
        )


class TweetSerializerForDetail(TweetSerializer):
    # comments = CommentSerializer(source='comment_set', many=True)
    comments = serializers.SerializerMethodField()
    likes = LikeSerializer(source='like_set', many=True)

    class Meta:
        model = Tweet
        fields = (
            'id',
            'user',
            'content',
            'created_at',
            'comments_count',
            'likes_count',
            'has_liked',
            'comments',
            'likes',
            'photo_urls',
            'retweet_from',
        )

    def get_comments(self, obj):
        queryset = obj.comment_set.all().order_by('created_at')
        serializer = CommentSerializer(
            queryset,
            many=True,
            context=self.context,
        )
        return serializer.data


class TweetSerializerForCreate(serializers.ModelSerializer):
    content = serializers.CharField(min_length=6, max_length=140)
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=True,
        required=False,
    )
    retweet_from_id = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = Tweet
        fields = ('content', 'files', 'retweet_from_id')

    def validate(self, data):
        if len(data.get('files', [])) > TWEET_PHOTOS_UPLOAD_LIMIT:
            raise ValidationError({
                'message': f'You can upload {TWEET_PHOTOS_UPLOAD_LIMIT} photos '
                           f'at most'
            })
        retweet_from_id = data.get('retweet_from_id')
        if (retweet_from_id is not None and
                not Tweet.objects.filter(id=retweet_from_id).exists()):
            raise ValidationError({
                'message': 'The tweet you tried to retweet does not exist.'
            })
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        content = validated_data['content']
        retweet_from_id = validated_data.get('retweet_from_id')
        tweet = Tweet.objects.create(
            user=user,
            content=content,
            retweet_from_id=retweet_from_id,
        )
        if validated_data.get('files'):
            TweetService.create_photos_from_files(
                tweet,
                validated_data['files'],
            )

        return tweet
