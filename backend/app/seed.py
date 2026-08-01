import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import Role, User


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        roles: dict[str, Role] = {}
        for name, description in {
            "user": "Người dùng tiêu chuẩn",
            "admin": "Quản trị hệ thống",
        }.items():
            role = (await db.scalars(select(Role).where(Role.name == name))).first()
            if not role:
                role = Role(name=name, description=description)
                db.add(role)
                await db.flush()
            roles[name] = role

        email = settings.admin_email.lower()
        admin = (await db.scalars(select(User).where(User.email == email))).first()
        if not admin:
            admin = User(
                email=email,
                password_hash=hash_password(settings.admin_password),
                full_name="System Administrator",
                timezone=settings.default_timezone,
                roles=[roles["user"], roles["admin"]],
            )
            db.add(admin)
        elif not admin.has_role("admin"):
            admin.roles.append(roles["admin"])
        await db.commit()
        print(f"Seed completed. Admin: {email}")


if __name__ == "__main__":
    asyncio.run(seed())
