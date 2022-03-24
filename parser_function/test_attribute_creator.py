import unittest


class TestLambdaFunction(unittest.TestCase): # based on https://hands-on.cloud/how-to-test-python-lambda-functions/
    def test_create_message_attrs(self):
        from attribute_creator import create_message_attrs

        test_message = {'eventName': 'ObjectCreated',
                        's3': {'object': {'key': 'foo=bar/hello_world.txt'},
                               'bucket': {'name': 'bucket_42'}}}

        EXPECTED_ATTRIBUTE_DICT = {'foo': {'DataType': 'String',
                                           'StringValue': 'bar'}}

        test_attribute_dict = create_message_attrs(test_message)

        self.assertEqual(EXPECTED_ATTRIBUTE_DICT, test_attribute_dict)
