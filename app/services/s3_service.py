import json
import os
from typing import Any

import boto3

S3_BUCKET = "pse-uab"
S3_TRANSFERS_KEY = os.getenv("S3_TRANSFERS_KEY", "transfers.json")


def _client():
    kwargs = {"region_name": os.getenv("AWS_REGION", "eu-central-1")}
    key_id = os.getenv("AWS_ACCESS_KEY_ID")
    secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    if key_id and secret:
        kwargs["aws_access_key_id"] = key_id
        kwargs["aws_secret_access_key"] = secret
    return boto3.client("s3", **kwargs)


def fetch_transfers_json(key: str | None = None) -> list[dict[str, Any]]:
    obj = _client().get_object(Bucket=S3_BUCKET, Key=key or S3_TRANSFERS_KEY)
    body = obj["Body"].read()
    data = json.loads(body.decode("utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array at s3://{S3_BUCKET}/{key or S3_TRANSFERS_KEY}")
    return data
