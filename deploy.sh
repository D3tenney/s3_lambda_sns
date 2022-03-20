#!/usr/bin/env bash

sam deploy \
    -g \
    --region us-east-1 \
    --profile default \
    --template-file template.yaml \
    --stack-name s3-lambda-sns-example \
    --parameter-overrides \
        SubscriptionEmail=YOUR_EMAIL \
    --tags \
        project_name=s3-lambda-sns-example
