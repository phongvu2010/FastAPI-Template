// /**
//  * Lấy token từ localStorage và gọi API /users/me.
//  * Hiển thị kết quả trong console (hoặc DOM).
//  */
// async function fetchUserData() {
//     const token = localStorage.getItem('access_token');
//     const tokenType = localStorage.getItem('token_type');
    
//     // 1. Kiểm tra Token
//     if (!token) {
//         console.error("Không tìm thấy token. Chuyển hướng đến trang đăng nhập.");
//         // Nếu không có token, chuyển hướng đến trang đăng nhập
//         window.location.href = '/auth/login'; 
//         return;
//     }

//     // 2. Gọi API bảo mật
//     try {
//         const response = await fetch('/users/me', {
//             method: 'GET',
//             headers: {
//                 // Đính kèm token vào header Authorization
//                 'Authorization': `${tokenType} ${token}`, 
//                 'Content-Type': 'application/json',
//             },
//         });

//         // 3. Xử lý phản hồi
//         if (response.ok) {
//             const data = await response.json();
//             console.log("✅ Thông tin người dùng (từ /users/me):", data);
            
//             // TODO: Triển khai logic cập nhật DOM tại đây, ví dụ:
//             // document.getElementById('user-info').textContent = data.full_name;
//             return data;
//         } else if (response.status === 401 || response.status === 403) {
//             console.error("Token không hợp lệ hoặc không có quyền. Đăng xuất và chuyển hướng.");
//             // Token hết hạn, xóa token và chuyển hướng
//             localStorage.removeItem('access_token');
//             localStorage.removeItem('token_type');
//             window.location.href = '/auth/login';
//         } else {
//             console.error("Lỗi khi gọi API /users/me:", response.status);
//         }
//     } catch (error) {
//         console.error("Lỗi mạng:", error);
//     }
// }
