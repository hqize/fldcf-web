from tortoise.models import Model
from tortoise import fields

class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True)
    password_hash = fields.CharField(max_length=64)
    role = fields.CharField(max_length=20, default='user')
    avatar_url = fields.CharField(max_length=512, null=True)

    class Meta:
        table = "user"