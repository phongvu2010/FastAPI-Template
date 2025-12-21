/* --- static/js/profile.js --- */

// Helper Loading State
const toggleBtnLoading = (isLoading) => {
    const btn = document.getElementById('btn-save-profile');
    const iconSave = document.getElementById('icon-save');
    const iconLoading = document.getElementById('icon-loading');
    const btnText = document.getElementById('btn-text');

    if (isLoading) {
        btn.disabled = true;
        iconSave.classList.add('hidden');
        iconLoading.classList.remove('hidden');
        btnText.textContent = "Đang lưu...";
    } else {
        btn.disabled = false;
        iconSave.classList.remove('hidden');
        iconLoading.classList.add('hidden');
        btnText.textContent = "Lưu thay đổi";
    }
};

const ProfileManager = {
    async updateProfile(event) {
        event.preventDefault(); // Chặn reload form mặc định

        // 1. Bật loading
        toggleBtnLoading(true);

        // 2. Lấy dữ liệu từ form
        const form = event.target;
        // Lấy dữ liệu ngay từ form người dùng nhập
        const formData = {
            full_name: form.full_name.value.trim(),
            department: form.department.value,
            contact_email: form.contact_email.value.trim() || null
        };

        try {
            // 2. Gọi API (Spinner sẽ tự động hiện nhờ api.js)
            const updatedUser = await API.request('/api/v1/users/me', 'PATCH', formData);

            // 3. Cập nhật giao diện (DOM)
            // Cập nhật tên trên thanh Navbar
            const navName = document.getElementById('nav-user-name');
            if (navName) navName.textContent = formData.full_name;

            // Cập nhật tên và phòng ban ở Card bên trái
            const cardName = document.getElementById('card-full-name');
            const cardDept = document.getElementById('card-department');

            if (cardName) cardName.textContent = formData.full_name;

            if (cardDept) cardDept.textContent = formData.department || 'Chưa cập nhật';

            // 4. Thông báo thành công
            // Dùng window.showToast từ api.js
            window.showToast("Cập nhật hồ sơ thành công!");
        } catch (error) {
            // Lỗi đã được API.request ném ra (hoặc hiển thị alert ở đó)
            let msg = error.detail?.[0]?.msg || error.message || "Lỗi cập nhật";
            msg = msg.replace("Value error, ", "");
            window.showToast(msg, "error");
        } finally {
            // 4. Tắt loading
            toggleBtnLoading(false);
        }
    }
};

// Gán sự kiện
document.addEventListener('DOMContentLoaded', () => {
    const profileForm = document.getElementById('profile-form');
    if (profileForm) {
        profileForm.addEventListener('submit', ProfileManager.updateProfile);
    }
});