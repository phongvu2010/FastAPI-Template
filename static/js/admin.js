/* --- static/js/admin.js --- */

const AdminManager = {
    // Cập nhật trạng thái Active/Inactive
    async toggleUserStatus(userId, isActive, toggleElement) {
        try {
            await API.request(`/api/v1/users/${userId}/status`, 'PATCH', { is_active: isActive });
            window.showToast(`Đã ${isActive ? 'kích hoạt' : 'vô hiệu hóa'} user thành công.`);
        } catch (error) {
            window.showToast(`Lỗi: ${error.message}`, "error");
            toggleElement.checked = !isActive; // Hoàn tác checkbox
        }
    },

    // Thêm quyền (Role)
    async addRole(userId) {
        const select = document.getElementById(`role-select-${userId}`);
        const roleName = select.value;
        const roleContainer = document.getElementById(`role-list-${userId}`); // Cần thêm ID này trong HTML

        if (!roleName) {
            window.showToast("Vui lòng chọn một vai trò.", "error");
            return;
        }

        // Kiểm tra xem quyền đã tồn tại trên giao diện chưa (tránh add trùng về mặt UI)
        if (roleContainer.querySelector(`[data-role="${roleName}"]`)) {
            window.showToast("Người dùng đã có quyền này rồi.", "error");
            return;
        }

        try {
            await API.request(`/api/v1/users/${userId}/role`, 'POST', { role_name: roleName });

            // Tạo phần tử Badge HTML mới
            const newBadge = document.createElement('span');
            newBadge.className = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200 mr-2 mb-1";
            newBadge.setAttribute('data-role', roleName);
            newBadge.innerHTML = `
                ${roleName}
                <button onclick="removeRole('${userId}', '${roleName}', this)" class="ml-1.5 text-blue-400 hover:text-red-600 focus:outline-none transition-colors" title="Gỡ quyền">
                    <i class="fa-solid fa-circle-xmark"></i>
                </button>
            `;

            // Append vào container
            roleContainer.appendChild(newBadge);

            // Reset select box
            select.value = "";
            window.showToast(`Đã thêm quyền ${roleName}.`);
        } catch (error) {
            window.showToast(`Lỗi thêm quyền: ${error.message}`, "error");
        }
    },

    // Xóa quyền (Role)
    async removeRole(userId, roleName, btnElement) {
        if (!confirm(`Bạn chắc chắn muốn xóa quyền ${roleName}?`)) return;

        try {
            await API.request(`/api/v1/users/${userId}/role`, 'DELETE', { role_name: roleName });

            // Tìm thẻ cha (span badge) và xóa nó
            const badge = btnElement.closest('span');
            if (badge) {
                badge.remove();
            }
            window.showToast(`Đã xóa quyền ${roleName}.`);
        } catch (error) {
            window.showToast(`Lỗi xóa quyền: ${error.message}`, "error");
        }
    }
};

// Gán sự kiện (Event Delegation)
document.addEventListener('DOMContentLoaded', () => {
    // Lắng nghe sự kiện change trên tất cả checkbox status
    document.querySelectorAll('.status-toggle').forEach(toggle => {
        toggle.addEventListener('change', function() {
            AdminManager.toggleUserStatus(this.dataset.userId, this.checked, this);
        });
    });
});

// Expose các hàm cần gọi từ onclick trong HTML ra global scope
window.addRole = AdminManager.addRole;
window.removeRole = AdminManager.removeRole;