from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import PermissionDenied

# Adapter cho Social Account
class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    
    def pre_social_login(self, request, sociallogin):
        """
        Kiểm tra người dùng trước khi đăng nhập.
        Sử dụng email của Google để kiểm tra xem Admin đã cấp vai trò chưa.
        """
        # 1. Lấy email từ Google
        email = sociallogin.user.email
        
        # 2. KIỂM TRA CHÍNH SÁCH EMAIL (Optional nhưng nên có)
        # Nếu chỉ muốn cho phép email nội bộ (ví dụ: @congty.com)
        if not email.endswith('@your_company.com'): # Cần thay bằng domain thực tế
            raise PermissionDenied("Email này không thuộc domain cho phép.")
        
        # 3. Lấy role và gán vào session (hoặc trực tiếp vào user)
        # Nếu user đã tồn tại, Django allauth sẽ tự động liên kết. 
        # Nếu chưa, nó sẽ tạo user mới với role mặc định là 'SENDER'.
        pass 
        
    def save_user(self, request, sociallogin, form=None):
        """
        Ghi đè để đảm bảo email là duy nhất và là username.
        """
        user = super().save_user(request, sociallogin, form)
        if not user.email:
            user.email = sociallogin.account.extra_data.get('email')
        if not user.username:
            user.username = user.email.split('@')[0]
        user.save()
        return user


# Adapter cho Login Response (trả về JWT thay vì session)
class JWTAccountAdapter(DefaultAccountAdapter):
    def get_login_response(self, request, response):
        """
        Trả về JWT Token thay vì Session cookie sau khi đăng nhập thành công.
        """
        user = request.user
        
        # Tạo JWT Token
        refresh = RefreshToken.for_user(user)
        
        response.data['refresh'] = str(refresh)
        response.data['access'] = str(refresh.access_token)
        response.data['user'] = {
            'id': user.id,
            'email': user.email,
            'role': user.role # Trường Role quan trọng cho Phân quyền
        }
        return response
