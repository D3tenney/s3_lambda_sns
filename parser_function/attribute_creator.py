from urllib import parse


def create_message_attrs(message):
    object_key = parse.unquote(message["s3"]["object"]["key"])
    key_parts = object_key.split('/')

    attribute_dict = dict()
    for part in key_parts[:-1]:
        key = part.split('=')[0]
        value = part.split('=')[1]

        attribute_dict[key] = {'StringValue': str(value),
                               'DataType': 'String'}
    return attribute_dict
