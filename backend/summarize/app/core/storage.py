from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aioboto3

from app.core.config import (
    S3_ACCESS_KEY_ID,
    S3_BUCKET_NAME,
    S3_ENDPOINT_URL,
    S3_SECRET_ACCESS_KEY,
)


def get_s3_config() -> dict:
    return {
        "endpoint_url": S3_ENDPOINT_URL,
        "aws_access_key_id": S3_ACCESS_KEY_ID,
        "aws_secret_access_key": S3_SECRET_ACCESS_KEY,
        "bucket_name": S3_BUCKET_NAME
    }

@asynccontextmanager
async def get_s3_client() -> AsyncGenerator:
    config = get_s3_config()
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=config["endpoint_url"],
        aws_access_key_id=config["aws_access_key_id"],
        aws_secret_access_key=config["aws_secret_access_key"],
    ) as client:
        yield client

async def upload_file_stream(file_stream, object_name: str) -> None:
    """Uploads a file stream directly to object storage."""
    config = get_s3_config()
    async with get_s3_client() as s3:
        await s3.upload_fileobj(file_stream, config["bucket_name"], object_name)

async def upload_file_bytes(file_bytes: bytes, object_name: str) -> None:
    """Uploads bytes directly to object storage."""
    config = get_s3_config()
    async with get_s3_client() as s3:
        await s3.put_object(Bucket=config["bucket_name"], Key=object_name, Body=file_bytes)

async def download_file_bytes(object_name: str) -> bytes:
    """Downloads an object from storage into memory."""
    config = get_s3_config()
    async with get_s3_client() as s3:
        response = await s3.get_object(Bucket=config["bucket_name"], Key=object_name)
        async with response["Body"] as stream:
            return await stream.read()

async def delete_file(object_name: str) -> None:
    """Deletes an object from storage."""
    config = get_s3_config()
    async with get_s3_client() as s3:
        await s3.delete_object(Bucket=config["bucket_name"], Key=object_name)
