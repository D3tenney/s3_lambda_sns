# s3_lambda_sns
Example of using a lambda function to parse an s3 notification and add
attributes to an SNS notification.

## Introduction
I want to make bucket notifications available to downstream services,
but not all services will want all notifications.

I could:
- Send all notifications to all downstream queues/services and have the
service do the filtering.
- Have a separate SNS Topic for each type of file. I could have
separate notification configurations for each s3 prefix, so each topic would only
have one type of message. Downstream services could just subscribe to whichever
topic(s) they needed.
- Pass all of the notifications to one SNS topic, then filter the
subscriptions, so downstream services only receive relevant messages.

The first option would be expensive. If, for instance, the downstream services
are lambda functions triggered by SQS Queues subscribed to the topic, and a
certain message only needs to be processed by one of five services, I pay to
spin up four unnecessary lambda contexts, which might be sizable if they are
intended to read/process data described in the message,
just so they can identify a false alarm,
delete the message from their own queue, and spin down. That's a lot of wasted
compute.

The second option would prevent unnecessary lambda processing, but would require
additional resources (new topics) for any new type of message.
Downstream resources that wanted to consume multiple types of messages would
need to manage multiple subscriptions. This could quickly become unwieldy for
me and my downstream consumers.

The third option seems perfect. SNS allows attributes to be attached to messages,
and subscribers can filter based on those attributes. Unfortunately, S3 bucket
notifications don't come pre-configured with any attributes. Thus, an
intermediate step is necessary to parse the S3 notification and add relevant
attributes to the SNS message. This repository is an example of this strategy.

## Deployment
To deploy this stack, you'll need [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html#cliv2-linux-install)
and [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html).

With those command line tools installed, review the `deploy.sh` script.
It's set up to use your default AWS CLI profile to deploy in the `us-east-1`
region. You can change these settings by altering the script.

Run the `deploy.sh` script (on Mac/Linux):
```bash
. ./deploy.sh
```
On Windows, you'll probably want to rename the file as `deploy.bat` and
replace `/` with `^`. This _should_ allow you to run the script, I think. Or you
can copy/paste the commands into your command prompt.

Follow the prompts for the guided deployment.
Input your email address for `SubscriptionEmail` to have
the SNS topic send you messages when you upload files to the bucket
with the prefix `file_type=A`.

Once the deployment completes, check your email for a message from SNS asking
you to confirm your subscription to the topic. Click the link to subscribe.

Note the bucket name that will print at the end of the deployment.

Now run the following command to copy the sample file, using the bucket name:
```bash
aws s3 cp ./sample.txt s3://{BUCKET_NAME}/file_type=A/
```

You should get a notification in your email.

Now try:
```bash
aws s3 cp ./sample.txt s3://{BUCKET_NAME}/file_type=B/
```

You shouldn't get a notification from this one.

Play around with `create_message_attrs` in
`./parser_function/attribute_creator.py`. You could have it add attributes for
file extension, or parse the message differently. It is good to note here that
SNS has a limit of [10 attributes](https://docs.aws.amazon.com/sns/latest/dg/sns-message-attributes.html)
unless you're passing a raw message, such as to SQS.

If you want to alter the subscription, to filter on a different value for
example, look at `TopicSubscription` in `template.yaml`.

## Effectiveness
I've found this approach to be quite adequate for most purposes. In my limited
testing, I've seen the cold startup run around 250ms, about 1/4 of a second.
Subsequent runs are about 20ms, about 1/50 of a second. Some articles indicate
that rewriting the function in Go could speed things up even more.

The cost for the lambda component of this solution is negligible. With ARM
architecture and assuming 250ms for every run with 128MB of memory,
1M invocations in a month would cost $0.62 USD in us-east-1.
You can estimate cost for your use case with
the [AWS Pricing Calculator](https://calculator.aws/#/createCalculator/Lambda).

## Cleanup
You can't delete a bucket with objects in it, so run
```bash
aws s3 rm --recursive s3://{BUCKET_NAME}/
```

Then you can just delete the stack:
```bash
aws cloudformation delete-stack \
    --stack-name s3-lambda-sns-example \
    --profile default \
    --region us-east-1
```

## Extension
This architecture could be used to allow messages from multiple buckets to be
passed to a single lambda for parsing and on to a single topic for distribution.
These buckets could be in a different stack from the lambda and topic.

For this purpose, you would deploy the function, s3permission, topic,
and topic policy in one stack, while exporting the function ARN to be
consumed by as many stacks as had buckets needing to send messages. So the
`Outputs` portion of the template would look like:
```
Outputs:
  FunctionArn:
    Description: "Arn of s3 notification parser function"
    Value: !GetAtt ParserFunction.Arn
    Export:
      Name: !Sub "${AWS::StackName}-FunctionArn"
```

And then a whole separate stack (or two or ten, etc...) with buckets might look
like:
```
Parameters:
  FunctionStackName:
    Type: String
    Default: s3-notification-parser-function-sns

Resources:
  BucketA:
    Type: AWS::S3::Bucket
    Properties:
      AccessControl: Private
      BucketName: !Sub "${AWS::StackName}-bucket-a-${AWS::AccountId}"
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      NotificationConfiguration:
        LambdaConfigurations:
          - Event: s3:ObjectCreated:*
            Function:
              Fn::ImportValue:
                !Sub "${FunctionStackName}-FunctionArn"
```

Many buckets can easily send messages to a single function as long
as their names share a common pattern. The `SourceArn` property of the
AWS::Lambda::Permission resource uses a
[StringLike operator](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-lambda-permission.html) to limit which ARNs can invoke the lambda.
Thus, a pattern can be established, as in the template here, where any bucket
belonging to the same account with an ARN
_like_ `"arn:aws:s3:::${AWS::StackName}-bucket*"` can send a notification and
invoke the lambda.

Thus, a great many buckets could use the same function and topic easily, which
could prevent having duplicate lambdas for each bucket in a project, and
the `create_message_attrs` function could be easily altered to parse
bucket name from the message and add it as an attribute, so downstream
services could filter for just the messages they want from certain buckets.

## References
A reply on [this reddit post](https://www.reddit.com/r/aws/comments/spt2o6/filtering_sqs_subscription_to_sns_topic_for/)
suggested using a lambda to parse the S3 notification. It seems that the
use case there was to have lambda look up in DynamoDB where the message should
go or what attributes should be attached to it. The solution here is a little
different, but I got the idea to use Lambda from `u/Cwiddy`.

Invoking the lambda with messages from S3 was based on a
[Medium Article](https://medium.com/@owentar/how-to-setup-s3-bucket-lambda-notifications-in-cloudformation-without-errors-f7250a6a9460) by Hernán Carrizo. This is more extensible than creating the
relationship using the `Events` property of the AWS::Serverless::Function
resource, since that requires the bucket name and that the bucket be created
in the same template, as documented [here](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-property-function-s3.html).
