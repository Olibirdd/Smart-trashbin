from djongo import models 
from bson import ObjectId

# Users collection
class User(models.Model):
    _id = models.ObjectIdField(primary_key=True, default=ObjectId, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255) 
    role = models.CharField(max_length=10, choices=[("user", "User"), ("admin", "Admin")], default="user")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"

    def save(self, *args, **kwargs):
        # If _id doesn't exist (new user), let MongoDB create it
        if not self._id:
            self._id = None  # Let MongoDB generate the _id
        super().save(*args, **kwargs)

    @property
    def user_id(self):
        """Property to safely access the MongoDB _id"""
        return str(self._id) if self._id else None

    def __str__(self):
        return self.username

# Vouchers collection
class Voucher(models.Model):
    _id = models.ObjectIdField(primary_key=True, default=ObjectId, editable=False)
    voucher_code = models.CharField(max_length=50, unique=True)  
    voucher_duration = models.IntegerField(null=True, blank=True)
    redeemed = models.BooleanField(default=False)    
    redeemed_by_email = models.EmailField(null=True, blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)  
    redeemed_at = models.DateTimeField(null=True, blank=True)   

    class Meta:
        db_table = "vouchers"

    def save(self, *args, **kwargs):
        # If _id doesn't exist (new user), let MongoDB create it
        if not self._id:
            self._id = None  # Let MongoDB generate the _id
        super().save(*args, **kwargs)

    @property
    def voucher_id(self):
        """Property to safely access the MongoDB _id"""
        return str(self._id) if self._id else None

    def __str__(self):
        return self.voucher_code

# Activity Logs collection
class ActivityLog(models.Model):
    action = models.CharField(max_length=50) 
    voucher_code = models.CharField(max_length=50)
    email = models.EmailField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activity_logs"