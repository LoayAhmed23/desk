import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Category(models.Model):
    """Support request categories (e.g. IT, HR, Facilities)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fa-tag', help_text='FontAwesome icon class')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Ticket(models.Model):
    """Internal support request ticket."""

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In Progress'
        IN_REVIEW = 'in_review', 'In Review'
        BLOCKED = 'blocked', 'Blocked'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    # Auto-generated unique request ID
    request_id = models.CharField(
        max_length=12, unique=True, editable=False, db_index=True
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tickets'
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.MEDIUM
    )

    # People
    submitter = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='submitted_tickets'
    )
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_tickets'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.request_id}] {self.title}"

    def save(self, *args, **kwargs):
        if not self.request_id:
            self.request_id = self._generate_request_id()
        # Auto-set resolved_at
        if self.status in (self.Status.RESOLVED, self.Status.CLOSED) and not self.resolved_at:
            self.resolved_at = timezone.now()
        elif self.status not in (self.Status.RESOLVED, self.Status.CLOSED):
            self.resolved_at = None
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_request_id():
        """Generate a unique request ID like HD-A1B2C3."""
        short = uuid.uuid4().hex[:6].upper()
        return f"HD-{short}"


class Note(models.Model):
    """Internal private notes on a ticket (visible only to agents/managers)."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Note on {self.ticket.request_id} by {self.author.username}"


class ActivityLog(models.Model):
    """Tracks status changes and assignment changes on a ticket."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='activity_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=200)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} on {self.ticket.request_id}"
