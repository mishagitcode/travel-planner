from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class TravelProject(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def refresh_completion_status(self):
        places = self.places.all()
        is_completed = places.exists() and not places.filter(is_visited=False).exists()
        if self.is_completed != is_completed:
            self.is_completed = is_completed
            self.save(update_fields=["is_completed", "updated_at"])


class ProjectPlace(models.Model):
    project = models.ForeignKey(
        TravelProject, on_delete=models.CASCADE, related_name="places"
    )
    external_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    notes = models.TextField(blank=True, null=True)
    is_visited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["project", "external_id"]
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.name} ({self.project.name})"


@receiver(post_save, sender=ProjectPlace)
def sync_project_completion(sender, instance, **kwargs):
    instance.project.refresh_completion_status()
