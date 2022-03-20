from attribute_creator import create_message_attrs
import boto3
import json
from os import environ

TOPIC_ARN = environ.get("TOPIC_ARN")

sns_client = boto3.client('sns')


def event_handler(event, context):

    msg_attrs = create_message_attrs(event)

    sns_client.publish(TopicArn=TOPIC_ARN,
                       Message=json.dumps(event),
                       MessageAttributes=msg_attrs)
