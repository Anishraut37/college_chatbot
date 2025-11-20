from django.db import models
from django.contrib.auth.models import User

# -----------------------------
# USER PROFILE MODEL
# -----------------------------
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=20,
        choices=(
            ("student", "Student"),
            ("teacher", "Teacher")
        )
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


# -----------------------------
# CHAT HISTORY MODEL
# -----------------------------
class ChatHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.question[:30]}"
