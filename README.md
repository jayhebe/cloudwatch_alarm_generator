# CloudWatch Alarm Generator

## 1. Purpose
As a beginner of the AWS Cloud player, when you create a brand new project or migrate an existing environment (aka. Lift and Shift) to the Cloud, I believe you have to create a lot of EC2 or RDS which are the most common used resources on the AWS Cloud. After that it is a nightmare to create the CloudWatch alarms for the resources by manual accordingly or sometimes we forget to create alarm for the resources. That is why this CloudWatch Alarm Generator is here.

## 2. Architecture
![solution architecture](https://github.com/jayhebe/cloudwatch_alarm_generator/raw/main/images/cag.png)
The CloudTrail will capture all the API calls and store the logs in a S3 bucket, then a SNS notification was sent to notify the S3 bucket name and key. The Lambda function will use the SNS notification as a trigger and use the S3 bucket name and key to parse the log file. If the event of creating EC2 or RDS is found, the dedicated alarms will be created automatically.

## 3. Deployments
### 3.1 Prerequisites
In the deployments folder, there is a CloudFormation json file. To use this CloudFormation file, the following prerequisites should be satisfied:
a. You should have an existing S3 bucket which will be used to upload the lambda deployment package in the packages folder.
b. You should have an existing SNS topic which will be used as the notification for the CloudWatch alarm.

The CloudFormation will primarily create the following resources:
a. A S3 bucket for CloudTrail log files.
b. A SNS topic for CloudTrail SNS notification.
c. A Lambda function for creating CloudWatch alarms.
d. A trail for logging all API calls.
e. Additional S3 bucket policy, SNS policy and IAM role to make everything working properly.

### 3.2 Parameters
* CloudwatchSNSTopicARN - An existing SNS topic which will be used as the notification for the CloudWatch alarm, in ARN format.
* LambdaDeploymentPackageName - The lambda deployment package name, the default value is cloudwatch_alarm_generator.zip which the same as the file name in packages folder.
* LambdaDeploymentS3BucketName - An existing S3 bucket which will be used to upload the lambda deployment package.
* LambdaFunctionName - The lambda function name, the default value is cloudwatch-alarm-generator.
* LambdaRoleName - The role for lambda function which including the permissions of read file from S3 bucket, creating alarms in CloudWatch etc.
* S3BucketName - The S3 bucket for CloudTrail logs, **please note this bucket will be created by CloudFormation, so the bucket name should be globally unique, otherwise the CloudFormation will report that the specified resource already exists.**
* S3KeyPrefix - This parameter is optional, if you want to use prefix to organize objects, you can specify this value.
* SnsTopicName - The SNS notification for CloudTrail logs, it will also be created by CloudFormation, the default value is cloudtrail-sns-topic.
* TrailName - The CloudTrail name, the default value is management-events.

## 4. Manually Deployment
You can also opt to deployment the componments manually due to maybe you want to make everything in control. This section will describe all the steps in details. According to your situation, you can start from any part.
a. Create a trail from CloudTrail console or AWS CLI, specify a S3 bucket (create a new one or choose existing) to save the logs, meantime enable the SNS notification delivery.
b. Create a Lambda function and upload the deployment package. In the Environment variables of Configuration tab, create a variable which has 'cloudwatch_alarm_sns_topic' as Key, and the SNS topic ARN for CloudWatch alarm notification as Value. A new Lambda function role will be created as well. You have to change and add the following permissions in the role policy:
* s3:GetObject permission of your CloudTrail log bucket:
```json
{
    "Effect": "Allow",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::{bucket name}/*"
}
```
* cloudwatch:PutMetricAlarm permission of your CloudWatch:
```json
{
    "Effect": "Allow",
    "Action": "cloudwatch:PutMetricAlarm",
    "Resource": "arn:aws:cloudwatch:{region}:{account id}:*"
}
```
* ec2:DescribeInstanceTypes permission of your EC2 instance.
```json
{
    "Effect": "Allow",
    "Action": "ec2:DescribeInstanceTypes",
    "Resource": "*"
}
```
c. If you want to fine-tune the threshold of the alarm, at the time of this writing, it is not good enough - you have to change the code in lambda_function.py file. The details of each variable is described as below:
* ec2_cpu_threshold_percentage - Self-explanation, the EC2 CPU percentage in integer.
* ec2_memory_threshold_percentage - Self-explanation, the EC2 memory percentage in integer.
* ec2_disk_usage_percentage - Self-explanation, the EC2 disk percentage in integer.
* rds_cpu_threshold_percentage - Self-explanation, the RDS CPU percentage in integer.
* rds_memory_threshold_percentage - Self-explanation, the RDS memory percetage, because it has to specify bytes in alarm, this value is in float format which 0.2 means 20%.
* rds_storage_threshold_percentage - Self-explantation, the same as RDS memory percetage, which 0.2 means 20%.
d. Use the SNS topic in step a. as trigger of the Lambda function.
e. Enjoy.

## 5. Limitation
As the initial version of this solution, there are many limitations as follows:
a. For now the solution only supports EC2 and RDS alarms.
For EC2, the following metrics are supported:
* CPUUtilization
* StatusCheckFailed_System
* StatusCheckFailed_Instance
* mem_used_percent
* disk_used_percent
In order to make mem_used_percent and disk_used_percent working properly, please make sure the CloudWatch Agent is installed and at least the default configuration has been applied, otherwise the alarm will report with 'Insufficient Data'.
For RDS, only MySQL and PostgreSQL engine with following metrics are supported:
* CPUUtilization
* FreeableMemory
* FreeStorageSpace
More features are under development.
b. This solution is only used for region-wide which means that all resources should be located in the same region of the same AWS account. Cross-region or organization trail feature might be supported in the future.

## 6. Change Logs
| Date | Version | Author | Comments |
| 2022-05-10 | 0.1 | Jay | Initial version |