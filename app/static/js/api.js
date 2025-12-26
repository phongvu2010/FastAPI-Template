/* --- static/js/api.js --- */

// 1. Hàm hiển thị thông báo (Global Utility)
window.showToast = (message, type = "success") => {
    if (typeof Toastify !== 'undefined') {
        Toastify({
            text: message,
            duration: 3000,
            gravity: "top",
            position: "right",
            style: { background: type === "success" ? "#10B981" : "#EF4444" },
            stopOnFocus: true
        }).showToast();
    } else {
        alert(message); // Fallback nếu Toastify chưa load
    }
};

const API = {
    // Cache element spinner để không phải query lại nhiều lần
    spinnerElement: null,

    init() {
        this.spinnerElement = document.getElementById('global-loading-overlay');
    },

    getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    },

    // Hiển thị Spinner
    showLoading() {
        if (this.spinnerElement) {
            this.spinnerElement.classList.remove('hidden');
            this.spinnerElement.classList.add('flex');
        }
    },

    // Ẩn Spinner
    hideLoading() {
        if (this.spinnerElement) {
            this.spinnerElement.classList.add('hidden');
            this.spinnerElement.classList.remove('flex');
        }
    },

    /**
     * Hàm gọi API trung tâm (Wrapper cho fetch)
     * Tự động xử lý CSRF, JSON parsing và Loading UI.
     */
    async request(url, method = 'GET', data = null) {
        // 1. Bật Loading
        this.showLoading();

        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': this.getCsrfToken()
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        try {
            // 2. Thực hiện gọi API
            const response = await fetch(url, options);

            // 3. Xử lý lỗi xác thực (Token hết hạn/Không hợp lệ)
            if (response.status === 401) {
                window.showToast("Phiên đăng nhập hết hạn via. Vui lòng đăng nhập lại.", "error");
                setTimeout(() => {
                    window.location.href = '/login';
                }, 1500);
                throw new Error("Unauthorized"); // Dừng flow hiện tại
            }

            // 4. Xử lý lỗi HTTP (4xx, 5xx)
            if (!response.ok) {
                // Cố gắng đọc lỗi từ JSON trả về
                let errorDetail = 'Lỗi không xác định';
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || errorDetail;
                } catch (e) {
                    errorDetail = response.statusText;
                }
                throw new Error(errorDetail);
            }

            // 5. Trả về kết quả (nếu có body)
            if (response.status === 204) return null;
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error; // Ném tiếp để file JS gọi nó xử lý (hiện toast lỗi cụ thể)
        } finally {
            // 5. Tắt Loading (Dù thành công hay thất bại)
            this.hideLoading();
        }
    }
};

// Khởi tạo API khi trang load xong
document.addEventListener('DOMContentLoaded', () => {
    API.init();
});