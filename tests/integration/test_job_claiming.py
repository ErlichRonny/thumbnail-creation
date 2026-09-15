import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.repository import claim_pending_job, insert_image
from tests.conftest import TEST_DATABASE_URL


async def test_concurrent_claim_only_one_worker_gets_the_row(db_session):
    image = await insert_image(
        db_session,
        original_file_name="cat.jpg",
        original_storage_path="/tmp/cat.jpg",
        original_width=100,
        original_height=100,
        content_type="image/jpeg",
        file_size_bytes=123,
        preset="small",
    )

    # Simulate two separate worker processes, each with their own connection,
    # racing to claim the same single pending row.
    engine = create_async_engine(TEST_DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session_a, session_factory() as session_b:
        results = await asyncio.gather(
            claim_pending_job(session_a),
            claim_pending_job(session_b),
        )

    claimed = [r for r in results if r is not None]
    assert len(claimed) == 1
    assert claimed[0].id == image.id

    await engine.dispose()
