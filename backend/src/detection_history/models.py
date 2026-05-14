"""检测记录表"""

from tortoise import fields
from tortoise.models import Model


class DetectionRecord(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="detection_records",
        on_delete=fields.CASCADE,
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    mode = fields.CharField(max_length=16, description="single | batch")
    preset = fields.CharField(max_length=32)
    source_filename = fields.CharField(max_length=512)
    ok = fields.BooleanField(default=True)
    error_message = fields.CharField(max_length=1024, null=True)

    image_class_index = fields.IntField(null=True)
    fake_probability = fields.FloatField(null=True)
    authentic_probability = fields.FloatField(null=True)
    mask_tamper_ratio = fields.FloatField(null=True)
    localization_override = fields.BooleanField(default=False)
    input_height = fields.IntField(null=True)
    input_width = fields.IntField(null=True)
    mask_height = fields.IntField(null=True)
    mask_width = fields.IntField(null=True)

    class Meta:
        table = "detection_record"
