# Creating a near-realtime  Amazon CloudWatch dashboard to track migration status



## Solution Overview

Please check the architecture.png for architectural diagram

1. The solution starts with an AWS Eventbridge cron rule that runs every 1 minute to invoke the AWS Lambda function. 

2. The Lambda code in python (cw_dashboard.py) is customized for the Migration use case. You can use this code to push system-defined and user-defined metrics to Amazon CloudWatch dashboard. The Lambda function will create custom metrics by using MGN APIs and push it to AmazCloudWatch. These will be the user-defined custom metrics.

3. The Lambda function will then publish user-defined and system-defined metrics on to Amazon CloudWatch dashboard. This dashboard can then be used to see performance metrics or other statistics of your migration journey. The red dotted box in the architecture diagram can be generalized for any non-migration use case use case also such as: Data Analytics, IOT, Zero trust etc.


## Step-by-Step Guide

1. Replace the <region> in cw_dashboard.py with the region of your choice. 

2. Zip the Lambda function and upload it on to an S3 bucket of your choice. Use this [link](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html) to learn how to zip the lambda function in python.

3. Use the CW_dashboard.yaml template to launch the infrastructure through AWS Cloudformation in the AWS region of your choice. Replace `<s3-bucket>` with the s3 bucket name where the lambda function is stored. This YAML template when deployed through AWS Cloudformation will launch the Lambda function, AWS Event Bridge rule and necessary Lambda roles and permissions. 

Note that the YAML template creates a Lambda role with policy that is required to access the AWS MGN service. 

Ensure that the AWS region you choose to deploy the Cloudformation YAML template matches the region in your Lambda function code and the S3 bucket you  chose to store the Lambda function zip.

4. Once the environment is deployed by Cloudformation, go to Find Services and search for CloudWatch.

5. On the left navigation pane choose Dashboards, then choose MGN-Dashboard. If you have source machines added in the AWS MGN console, then you will see 5 widgets in total. 

6. The resultant CW dashboard is attached to the report as result.png.
