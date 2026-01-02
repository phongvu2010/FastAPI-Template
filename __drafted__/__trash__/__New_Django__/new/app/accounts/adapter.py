from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomAccountAdapter(DefaultAccountAdapter):
    """Xử lý adapter cho việc đăng ký thông thường (nếu có)."""
    pass

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Xử lý adapter cho Social Login (Google) để gán role và cập nhật user.
    """
    def pre_social_login(self, request, sociallogin):
        """
        Đồng bộ hóa User khi đăng nhập lại.
        """
        pass # Không làm gì đặc biệt trước khi đăng nhập

    def save_user(self, request, sociallogin, form=None):
        """
        Tạo User mới từ thông tin Google.
        """
        user = super().save_user(request, sociallogin, form)

        # 1. Gán Role mặc định
        if not user.role:
            user.role = "SENDER" # Gán role mặc định SENDER theo blueprint
            user.save()

        # 2. Đồng bộ tên
        if sociallogin.account.extra_data.get('given_name'):
            user.first_name = sociallogin.account.extra_data.get('given_name')
        if sociallogin.account.extra_data.get('family_name'):
            user.last_name = sociallogin.account.extra_data.get('family_name')

        user.save()
        return user
