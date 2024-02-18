import os
import sys
import logging

from dotenv import load_dotenv
import boto3
from httpx import get

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


REQUERED_ENV_VARS = [
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY',
    'AWS_REGION',
    'ROUTE53_DOMAIN_NAME',
    'ROUTE53_TYPE',
    'ROUTE53_TTL',
    'CRON_SCHEDULE',
]

def validate_env_vars():
    for var in REQUERED_ENV_VARS:
        if var not in os.environ:
            logger.error(f"Missing environment variable: {var}")
            sys.exit(1)

def get_public_ip():
    try:
        response = get('https://api.ipify.org')
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Failed to get public IP: {e}")
        sys.exit(1)

def get_route53_client():
    try:
        return boto3.client(
            'route53',
            aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
            region_name=os.environ['AWS_REGION'],
        )
    except Exception as e:
        logger.error(f"Failed to get Route53 client: {e}")
        sys.exit(1)

def get_hosted_zone_id(client):
    try:
        response = client.list_hosted_zones_by_name(DNSName=os.environ['ROUTE53_DOMAIN_NAME'])
        return response['HostedZones'][0]['Id']
    except Exception as e:
        logger.error(f"Failed to get hosted zone ID: {e}")
        sys.exit(1)

def get_current_dns_ip(client, hosted_zone_id, domain_name, record_type):
    try:
        response = client.list_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            StartRecordName=domain_name,
            StartRecordType=record_type,
            MaxItems="1"
        )
        for record_set in response['ResourceRecordSets']:
            if record_set['Name'].startswith(domain_name) and record_set['Type'] == record_type:
                return record_set['ResourceRecords'][0]['Value']
    except Exception as e:
        logger.error(f"Failed to get current DNS IP: {e}")
        sys.exit(1)
    return None

def update_record_set(client, hosted_zone_id, record_set):
    try:
        response = client.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={
                'Changes': [
                    {
                        'Action': 'UPSERT',
                        'ResourceRecordSet': record_set,
                    },
                ],
            },
        )
        return response
    except Exception as e:
        logger.error(f"Failed to update record set: {e}")
        sys.exit(1)

def main():
    load_dotenv()
    validate_env_vars()

    public_ip = get_public_ip()
    logger.info(f"Public IP: {public_ip}")

    client = get_route53_client()
    hosted_zone_id = get_hosted_zone_id(client)
    logger.info(f"Hosted zone ID: {hosted_zone_id}")

    current_dns_ip = get_current_dns_ip(client, hosted_zone_id, os.environ['ROUTE53_DOMAIN_NAME'], os.environ['ROUTE53_TYPE'])
    logger.info(f"Current DNS IP: {current_dns_ip}")

    if public_ip != current_dns_ip:
        logger.info("IP has changed. Updating DNS record.")
        record_set = {
            'Name': os.environ['ROUTE53_DOMAIN_NAME'],
            'Type': os.environ['ROUTE53_TYPE'],
            'TTL': int(os.environ['ROUTE53_TTL']),
            'ResourceRecords': [
                {
                    'Value': public_ip,
                },
            ],
        }
        response = update_record_set(client, hosted_zone_id, record_set)
        logger.info(f"DNS update response: {response}")
    else:
        logger.info("IP has not changed. No update needed.")

if __name__ == '__main__':
    main()