"""创建默认管理员用户脚本"""
import asyncio
import sys
import os

# 添加 backend 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal, async_engine
from app.models import Base, User
from app.core.security import get_password_hash


async def create_admin():
    """创建默认管理员账号，如果不存在则创建"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        # 检查是否已有管理员
        result = await session.execute(
            select(User).where(User.email == "admin@bubbleradar.com")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print("管理员账号已存在：")
            print(f"  邮箱: admin@bubbleradar.com")
            print(f"  超级用户: {existing.is_superuser}")
            print(f"  状态: {'已激活' if existing.is_active else '已禁用'}")
            return
        
        # 创建新管理员
        admin = User(
            email="admin@bubbleradar.com",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            is_superuser=True,
        )
        session.add(admin)
        await session.commit()
        
        print("✅ 默认管理员账号创建成功！")
        print("=" * 40)
        print("  邮箱: admin@bubbleradar.com")
        print("  密码: admin123")
        print("  权限: 超级管理员")
        print("=" * 40)
        print("⚠️  请登录后立即修改默认密码！")


if __name__ == "__main__":
    asyncio.run(create_admin())
