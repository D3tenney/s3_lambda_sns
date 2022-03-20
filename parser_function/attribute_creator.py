from urllib import parse


def create_message_attrs(event):
    message = event['Records'][0]

    if 'ObjectCreated' not in message['eventName']:
        return None

    object_key = parse.unquote(message["s3"]["object"]["key"])
    key_parts = object_key.split('/')

    attribute_dict = dict()
    for part in key_parts[:-1]:
        key = part.split('=')[0]
        value = part.split('=')[1]

        attribute_dict[key] = {'StringValue': str(value),
                               'DataType': 'String'}
    return attribute_dict
