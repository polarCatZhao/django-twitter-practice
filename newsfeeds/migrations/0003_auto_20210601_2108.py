# Generated by Django 3.1.3 on 2021-06-01 21:08

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tweets', '0002_tweetphoto'),
        ('newsfeeds', '0002_auto_20210601_2027'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='newsfeed',
            index_together={('user', 'created_at'), ('user', 'tweet')},
        ),
    ]
