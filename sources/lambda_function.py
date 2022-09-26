import json
import logging
import os

from resource_helper import get_event_list, get_memory_by_class
from cloudtrail_log_filter import unzip_log_files, filter_trail_logs
from cloudwatch_alarm_wrapper import CloudWatchAlarmWrapper
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

EC2_EVENT = "RunInstances"
RDS_EVENT = "CreateDBInstance"
RDS_ENGINE_MYSQL = "mysql"
RDS_ENGINE_POSTGRES = "postgres"

actions = os.getenv("cloudwatch_alarm_sns_topic")

def lambda_handler(event, context):
    message = event["Records"][0]["Sns"]["Message"]
    message = json.loads(message)
    s3_bucket = message["s3Bucket"]
    s3_object_key = message["s3ObjectKey"]

    event_list = get_event_list()
    log_contents = unzip_log_files(s3_bucket, s3_object_key)
    target_events = filter_trail_logs(log_contents, event_list)

    for ev in target_events:
        if ev[0] == EC2_EVENT:
            tag_set = ev[1]["responseElements"]["instancesSet"]["items"][0]["tagSet"]["items"]
            enable_alarms = "True"
            for tag in tag_set:
                if tag["key"] == "EnableAlarms":
                    enable_alarms = tag["value"]
                    break
            
            if enable_alarms != "False":
                instance_id = ev[1]["responseElements"]["instancesSet"]["items"][0]["instanceId"]
                instance_type = ev[1]["responseElements"]["instancesSet"]["items"][0]["instanceType"]
                image_id = ev[1]["responseElements"]["instancesSet"]["items"][0]["imageId"]

                with open("config/ec2.json", "r") as ec2_fp:
                    ec2_alarms = ec2_fp.read()

                ec2_alarms = ec2_alarms.replace("$instance_id", instance_id)
                ec2_alarms = ec2_alarms.replace("$instance_type", instance_type)
                ec2_alarms = ec2_alarms.replace("$image_id", image_id)
                ec2_alarms = json.loads(ec2_alarms)["Alarms"]

                for alarm in ec2_alarms:
                    ec2_alarm_wrapper = CloudWatchAlarmWrapper(
                        metric_namespace=alarm["MetricNameSpace"],
                        metric_name=alarm["MetricName"],
                        dimensions=alarm["Dimensions"],
                        alarm_name="_".join([instance_id, alarm["MetricName"]]),
                        stat_type=alarm["StatType"],
                        threshold=alarm["Threshold"],
                        comparison_op=alarm["ComparisonOp"],
                        actions=actions,
                        period=alarm["Period"],
                        eval_periods=alarm["EvaluationPeriods"]
                    )

                    try:
                        ec2_alarm_wrapper.create_metric_alarm()
                        logger.info(
                            "Created alarm {} to track metric {}.{}".format(
                                "_".join([instance_id, alarm["MetricName"]]),
                                alarm["MetricNameSpace"],
                                alarm["MetricName"]
                            )
                        )
                    except ClientError as e:
                        logger.error(
                            "Couldn't create alarm {} to metric {}.{}".format(
                                "_".join([instance_id, alarm["MetricName"]]),
                                alarm["MetricNameSpace"],
                                alarm["MetricName"]
                            )
                        )
                        logger.debug(e)
                
        if ev[0] == RDS_EVENT:
            tag_list = ev[1]["responseElements"]["tagList"]
            enable_alarms = "True"
            for tag in tag_list:
                if tag["key"] == "EnableAlarms":
                    enable_alarms = tag["value"]
                    break

            if enable_alarms != "False":
                db_instance_identifier = ev[1]["responseElements"]["dBInstanceIdentifier"]
                engine = ev[1]["responseElements"]["engine"]
                db_instance_class = ev[1]["responseElements"]["dBInstanceClass"]
                db_memory = get_memory_by_class(db_instance_class.replace("db.", ""))
                
                if engine in (RDS_ENGINE_MYSQL, RDS_ENGINE_POSTGRES):
                    allocated_storage = ev[1]["responseElements"]["allocatedStorage"]

                    with open("config/rds.json", "r") as rds_fp:
                        rds_alarms = rds_fp.read()
                    
                    rds_alarms = rds_alarms.replace("$db_instance_identifier", db_instance_identifier)
                    rds_alarms = rds_alarms.replace("$memory_size", db_memory)
                    rds_alarms = rds_alarms.replace("$disk_size", allocated_storage)
                    rds_alarms = json.loads(rds_alarms)["Alarms"]

                    for alarm in rds_alarms:
                        rds_alarm_wrapper = CloudWatchAlarmWrapper(
                            metric_namespace=alarm["MetricNameSpace"],
                            metric_name=alarm["MetricName"],
                            dimensions=alarm["Dimensions"],
                            alarm_name="_".join([db_instance_identifier, alarm["MetricName"]]),
                            stat_type=alarm["StatType"],
                            threshold=(
                                alarm["Threshold"]["percentage"] * 
                                alarm["Threshold"]["size"] * 
                                alarm["Threshold"]["conversion"]
                            ),
                            comparison_op=alarm["ComparisonOp"],
                            actions=actions,
                            period=alarm["Period"],
                            eval_periods=alarm["EvaluationPeriods"]
                        )

                        try:
                            rds_alarm_wrapper.create_metric_alarm()
                            logger.info(
                                "Created alarm {} to track metric {}.{}".format(
                                    "_".join([db_instance_identifier, alarm["MetricName"]]),
                                    alarm["MetricNameSpace"],
                                    alarm["MetricName"]
                                )
                            )
                        except ClientError as e:
                            logger.error(
                                "Couldn't create alarm {} to metric {}.{}".format(
                                    "_".join([db_instance_identifier, alarm["MetricName"]]),
                                    alarm["MetricNameSpace"],
                                    alarm["MetricName"]
                                )
                            )
                            logger.debug(e)
