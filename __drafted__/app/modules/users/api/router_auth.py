router = APIRouter(prefix="/auth", tags=["Auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/login_page")
async def login_page(request: Request):
    """Hiển thị trang đăng nhập."""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/login")
async def google_login():
    """Redirect sang Google Login."""
    return RedirectResponse(url=auth.create_google_auth_url(), status_code=302)


@router.get("/logout")
async def logout():
    """Đăng xuất: Xóa Cookie và về trang login."""
    response = RedirectResponse(url="/auth/login_page", status_code=302)
    response.delete_cookie("access_token")
    return response


# @router.get("/callback")
# async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
#     """Xử lý Callback từ Google: Tạo User, Check Admin, Set Cookie."""
#     try:
#         # 1. Lấy Token & Info từ Google
#         token_res = await auth.exchange_code_for_token(code)
#         user_info = auth.get_google_user_info(token_res["id_token"])

#         google_sub = user_info.get("sub")
#         email = user_info.get("email")

#         # 2. Check Domain (nếu cấu hình)
#         if settings.ALLOWED_EMAIL_DOMAINS:
#             domain = email.split("@")[-1]
#             if domain not in settings.ALLOWED_EMAIL_DOMAINS:
#                 raise HTTPException(
#                     status_code=403, detail="Email domain không được phép."
#                 )

#         # 3. Tìm hoặc Tạo User
#         user = await user_crud.get_user_by_google_sub(db, google_sub)
#         if not user:
#             user_in = UserCreateInternal(
#                 google_sub=google_sub,
#                 email=email,
#                 full_name=user_info.get("name"),
#                 picture_url=user_info.get("picture"),
#             )
#             user = await user_crud.create_user_from_sso(db, user_in)

#             # --- LOGIC TỰ ĐỘNG SET ROLE ---
#             if email == settings.INITIAL_ADMIN_EMAIL:
#                 await user_crud.assign_role_to_user(db, user, UserRole.ADMIN)
#                 print(f"👑 New User {email} auto-promoted to ADMIN.")
#             else:
#                 await user_crud.assign_role_to_user(db, user, UserRole.SENDER)
#                 print(f"👤 New User {email} assigned SENDER role.")

#         if not user.is_active:
#             raise HTTPException(status_code=403, detail="Tài khoản bị khóa.")

#         # 4. Tạo JWT & Cookie
#         access_token = auth.create_access_token(data={"sub": user.google_sub})
#         response = RedirectResponse(url="/app", status_code=302)
#         response.set_cookie(
#             key="access_token",
#             value=access_token,
#             httponly=True,
#             secure=False,  # Đổi thành True khi lên Production (HTTPS)
#             max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
#             samesite="lax",
#         )
#         return response

#     except Exception as e:
#         print(f"Auth Error: {e}")
#         raise HTTPException(status_code=500, detail="Lỗi xác thực hệ thống.")
