from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "recorded_videos" ADD COLUMN "cm_analysis_version" VARCHAR(255);
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "recorded_videos" DROP COLUMN "cm_analysis_version";
    """
