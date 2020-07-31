import uuid
from django.db import models


# Create your models here.
class Face(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to='static/images')
