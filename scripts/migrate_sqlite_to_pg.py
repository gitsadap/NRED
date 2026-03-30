
import asyncio
import aiosqlite
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.models import Base, User, Staff, Page, Menu, Setting, Appeal, Tag, News, Activity, FacultyCV

# SQLite (Source)
SQLITE_DB_PATH = "./data/cms.db"

# PostgreSQL (Target)
PG_URL = (os.getenv("DATABASE_URL") or "")

async def migrate_data():
    print("Starting migration from SQLite to PostgreSQL...")

    # connect to postgres
    engine = create_async_engine(PG_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with aiosqlite.connect(SQLITE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with async_session() as session:
            try:
                # 1. Migrate Users
                print("Migrating Users...")
                async with db.execute("SELECT * FROM users") as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        # Check exist
                        result = await session.execute(text("SELECT id FROM users WHERE id = :id"), {"id": row['id']})
                        if not result.scalar():
                            new_user = User(
                                id=row['id'],
                                username=row['username'],
                                password_hash=row['password_hash'],
                                # created_at handled by default or copied? created_at is strictly server_default
                            )
                            session.add(new_user)
                await session.commit()
                
                # 2. Migrate Staff
                print("Migrating Staff...")
                async with db.execute("SELECT * FROM staff") as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        result = await session.execute(text("SELECT id FROM staff WHERE id = :id"), {"id": row['id']})
                        if not result.scalar():
                            new_staff = Staff(
                                id=row['id'],
                                name=row['name'],
                                position=row['position'],
                                email=row['email'],
                                image=row['image'],
                                expertise=row['expertise'],
                                type=row['type'],
                                order_index=row['order_index']
                            )
                            session.add(new_staff)
                await session.commit()

                # 3. Migrate Pages
                print("Migrating Pages...")
                async with db.execute("SELECT * FROM pages") as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        result = await session.execute(text("SELECT id FROM pages WHERE id = :id"), {"id": row['id']})
                        if not result.scalar():
                            new_page = Page(
                                id=row['id'],
                                slug=row['slug'],
                                title=row['title'],
                                content=row['content'],
                                template=row['template'],
                                is_published=row['is_published']
                            )
                            session.add(new_page)
                await session.commit()

                # 4. Migrate Menus
                print("Migrating Menus...")
                async with db.execute("SELECT * FROM menus") as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        result = await session.execute(text("SELECT id FROM menus WHERE id = :id"), {"id": row['id']})
                        if not result.scalar():
                            new_menu = Menu(
                                id=row['id'],
                                name=row['name'],
                                data_json=row['data_json']
                            )
                            session.add(new_menu)
                await session.commit()

                # 5. Migrate Settings
                print("Migrating Settings...")
                async with db.execute("SELECT * FROM settings") as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        result = await session.execute(text("SELECT key FROM settings WHERE key = :key"), {"key": row['key']})
                        if not result.scalar():
                            new_setting = Setting(
                                key=row['key'],
                                value=row['value']
                            )
                            session.add(new_setting)
                await session.commit()

                # 6. Migrate Appeals
                print("Migrating Appeals...")
                async with db.execute("SELECT * FROM appeals") as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        result = await session.execute(text("SELECT id FROM appeals WHERE id = :id"), {"id": row['id']})
                        if not result.scalar():
                            new_appeal = Appeal(
                                id=row['id'],
                                sender_name=row['sender_name'],
                                email=row['email'],
                                topic=row['topic'],
                                message=row['message'],
                                is_anonymous=row['is_anonymous'],
                                status=row['status']
                            )
                            session.add(new_appeal)
                await session.commit()

                # 7. Migrate Tags
                print("Migrating Tags...")
                async with db.execute("SELECT * FROM tags") as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        result = await session.execute(text("SELECT id FROM tags WHERE id = :id"), {"id": row['id']})
                        if not result.scalar():
                            new_tag = Tag(
                                id=row['id'],
                                name=row['name']
                            )
                            session.add(new_tag)
                await session.commit()

                # 8. Migrate News
                print("Migrating News...")
                async with db.execute("SELECT * FROM news") as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        result = await session.execute(text("SELECT id FROM news WHERE id = :id"), {"id": row['id']})
                        if not result.scalar():
                            new_news = News(
                                id=row['id'],
                                title=row['title'],
                                content=row['content'],
                                image_url=row['image_url'],
                                category=row['category'],
                                tags=row['tags']
                                # event_date handled if exists, check schema
                            )
                            session.add(new_news)
                await session.commit()

                # 9. Migrate Activities
                print("Migrating Activities...")
                async with db.execute("SELECT * FROM activities") as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        result = await session.execute(text("SELECT id FROM activities WHERE id = :id"), {"id": row['id']})
                        if not result.scalar():
                            new_activity = Activity(
                                id=row['id'],
                                title=row['title'],
                                content=row['content'],
                                image_url=row['image_url'],
                                category=row['category'],
                                tags=row['tags']
                            )
                            session.add(new_activity)
                await session.commit()

                # 10. Migrate FacultyCV
                print("Migrating FacultyCV...")
                async with db.execute("SELECT * FROM faculty_cv") as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                         result = await session.execute(text("SELECT id FROM faculty_cv WHERE id = :id"), {"id": row['id']})
                         if not result.scalar():
                            new_cv = FacultyCV(
                                id=row['id'],
                                user_id=row['user_id'],
                                cv_file=row['cv_file']
                            )
                            session.add(new_cv)
                await session.commit()

                print("Migration completed successfully!")

            except Exception as e:
                print(f"Error migrating: {e}")
                await session.rollback()

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_data())
