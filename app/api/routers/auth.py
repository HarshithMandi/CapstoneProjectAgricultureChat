from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, require_admin
from app.core.security import create_access_token, hash_password, verify_password
from app.db.repositories.user import UserRepository
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserPublic, UserUpdate

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserCreate):
    repo = UserRepository()
    email = request.email.strip().lower()
    if "@" not in email:
        raise HTTPException(status_code=422, detail="Valid email is required")

    existing = await repo.get_by_email(email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    role = "admin" if await repo.count() == 0 else "user"
    user = await repo.create(
        email=email,
        password_hash=hash_password(request.password),
        role=role,
        full_name=request.full_name,
    )
    token = create_access_token(user["_id"], user["role"])
    return TokenResponse(access_token=token, user=UserPublic(**user))


@router.post("/auth/login", response_model=TokenResponse)
async def login(request: UserLogin):
    repo = UserRepository()
    user = await repo.get_by_email(request.email.strip().lower())
    if not user or not verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="User account is inactive")

    token = create_access_token(user["_id"], user["role"])
    return TokenResponse(access_token=token, user=UserPublic(**user))


@router.get("/auth/me", response_model=UserPublic)
async def me(current_user: dict = Depends(get_current_user)):
    return UserPublic(**current_user)


@router.get("/admin/users", response_model=list[UserPublic])
async def list_users(_admin: dict = Depends(require_admin)):
    return [UserPublic(**user) for user in await UserRepository().list()]


@router.patch("/admin/users/{user_id}", response_model=UserPublic)
async def update_user(user_id: str, request: UserUpdate, admin: dict = Depends(require_admin)):
    updates = request.model_dump(exclude_unset=True)
    if user_id == admin["_id"] and updates.get("role") == "user":
        raise HTTPException(status_code=400, detail="Admins cannot demote their own account")
    user = await UserRepository().update(user_id, updates)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic(**user)
