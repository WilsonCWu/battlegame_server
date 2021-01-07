from django.db import models


class Event(models.Model):
    # We don't rely on the foreign key relation since it's not guaranteed to
    # exist, nor is it immediately important for this model.
    user_id = models.IntegerField()
    timestamp = models.DateTimeField()
    # https://docs.unity3d.com/ScriptReference/SystemInfo-deviceUniqueIdentifier.html.
    device_id = models.CharField(max_length=50)

    # Main event which can be aggregated over.
    event = models.CharField(max_length=30)
    # Additional data about the event to be carried over.
    tags = models.CharField(max_length=100)

    def __str__(self):
        return "%d: (%s) @ %s" % (self.user_id, self.event, self.timestamp)
