# Generated by Django 3.1.3 on 2021-06-02 18:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tweets', '0002_tweetphoto'),
    ]

    operations = [
        migrations.AddField(
            model_name='tweet',
            name='retweet_from',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='tweets.tweet'),
        ),
    ]
