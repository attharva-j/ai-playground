import boto3
import json
from functools import lru_cache

from botocore.exceptions import ClientError

@lru_cache
def get_secret():

    secret_name = "ai-foundation-dev/bedrock-config"
    region_name = "us-east-1"

    client = boto3.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    secret_dict = json.loads(get_secret_value_response["SecretString"])
    return secret_dict