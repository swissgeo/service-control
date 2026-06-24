from django.contrib.auth.backends import ModelBackend

class CustomUserBackend(ModelBackend):
    def has_perm(self, user_obj, perm, obj=None):
        return user_obj.is_superuser

    def has_module_perms(self, user_obj, app_label):
        return user_obj.is_superuser

# CustomUser sets user_permissions = None
# Override has_perm and has_module_perms to delegate to is_superuser
