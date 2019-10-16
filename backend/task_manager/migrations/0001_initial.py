# Generated by Django 2.1.4 on 2019-10-16 04:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('user_model', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.CharField(db_index=True, max_length=50, unique=True)),
                ('status', models.PositiveSmallIntegerField(default=0)),
                ('create_time', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='TaskSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.CharField(db_index=True, max_length=50, unique=True)),
                ('name', models.CharField(db_index=True, max_length=255, unique=True)),
                ('concurrency', models.PositiveIntegerField(default=1)),
                ('task_config', models.TextField()),
                ('create_time', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
        ),
        migrations.AddField(
            model_name='task',
            name='settings',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='task_manager.TaskSettings'),
        ),
        migrations.AddField(
            model_name='task',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user_model.UserModel'),
        ),
    ]
