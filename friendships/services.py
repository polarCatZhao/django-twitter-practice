from friendships.models import Friendship


class FriendshipService:

    @classmethod
    def get_followers(cls, user):
        friendships = Friendship.objects.filter(
            to_user=user,
        ).prefetch_related('from_user')
        return [friendship.from_user for friendship in friendships]

    @classmethod
    def get_followed_superstars(cls, user):
        """
        Returns the superstars followed by user.
        return: a list of User objects
        """
        friendships = Friendship.objects.filter(
            from_user=user,
            to_user__userprofile__is_superstar=True,
        ).prefetch_related('to_user')
        return [friendship.to_user for friendship in friendships]
