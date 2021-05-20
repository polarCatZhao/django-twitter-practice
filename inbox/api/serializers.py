from rest_framework import serializers
from notifications.models import Notification
from accounts.api.serializers import UserSerializer


class NotificationSerializer(serializers.ModelSerializer):
    recipient = UserSerializer()
    actor = UserSerializer()


    class Meta:
        model = Notification
        fields = (
            'id',
            'recipient',
            'actor_content_type',
            'actor_object_id',
            'actor',
            'verb',
            'action_object_content_type',
            'action_object_object_id',
            'target_content_type',
            'target_object_id',
            'timestamp',
            'unread',
        )


class NotificationSerializerForUpdate(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('unread',)

    def update(self, instance, validated_data):
        instance.unread = validated_data['unread']
        instance.save()
        return instance
