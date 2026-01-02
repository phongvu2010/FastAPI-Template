# Đây là API mà người dùng gọi khi muốn upload file (chỉnh sửa)
# API cho phép người dùng nộp lại file đã sửa
@app.post("/document/{doc_id}/upload")
async def handle_file_upload(doc_id: int, file: UploadFile, user: User = Depends(get_current_user)):
    # 1. Lấy hồ sơ từ DB
    document = await db.get_document(doc_id)

    # 2. Kiểm tra quyền sở hữu
    if document.uploader_id != user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")

    # 3. LOGIC MỞ KHÓA:
    # Chỉ cho phép upload nếu trạng thái là 'SUBMITTED' (hoặc 'REJECTED')
    allowed_statuses = ["SUBMITTED", "REJECTED_BY_INSPECTOR"]

    if document.status not in allowed_statuses:
        raise HTTPException(
            status_code=400, # 400 Bad Request
            detail="Hồ sơ đã được duyệt hoặc ký, không thể chỉnh sửa."
        )

    # 4. Lưu file mới (có thể ghi đè file cũ hoặc lưu phiên bản mới)
    await save_new_file_version(document, file)
    
    # 5. ĐẶT LẠI TRẠNG THÁI (RẤT QUAN TRỌNG)
    # Sau khi nộp lại, trạng thái phải quay về 'SUBMITTED'
    document.status = "SUBMITTED"
    
    # 6. Xóa/cập nhật lý do trả về cũ (nếu cần)
    await db.save(document)
    
    # 7. Ghi log: "User A đã nộp lại file"
    await db.log_audit(doc_id, user.id, "RESUBMITTED")

    # 8. Thông báo cho Người kiểm tra (Inspector) rằng hồ sơ đã được nộp lại
    await trigger_notification(document.inspector_id, "Hồ sơ đã được nộp lại, cần duyệt.")
    
    return {"message": "Cập nhật file và nộp lại thành công"}



# {% if document.status == "SUBMITTED" or document.status == "REJECTED_BY_INSPECTOR" %}
#     <label>Bạn có thể upload phiên bản mới:</label>
#     <input type="file" name="new_version">
#     <button type="submit">Cập nhật</button>
# {% else %}
#     <p>Hồ sơ đang ở trạng thái: <strong>{{ document.get_status_display }}</strong>. Bạn không thể chỉnh sửa.</p>
# {% endif %}
