from botocore.config import Config

config = Config(
    # See https://docs.aws.amazon.com/boto3/latest/guide/retries.html for detail on retries
    retries={
        "mode": "standard",
        "total_max_attempts": 2,
    },
    signature_version="s3v4",
)
