# Generated by Django 3.1.3 on 2021-06-17 22:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tweets', '0003_tweet_retweet_from'),
    ]

    operations = [
        migrations.AddField(
            model_name='tweet',
            name='comments_count',
            field=models.IntegerField(default=0, null=True),
        ),
        migrations.AddField(
            model_name='tweet',
            name='likes_count',
            field=models.IntegerField(default=0, null=True),
        ),
    ]
