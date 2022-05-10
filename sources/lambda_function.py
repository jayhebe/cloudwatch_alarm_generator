import json
import logging
import os

from resource_helper import get_memory_by_class
from cloudtrail_log_filter import unzip_log_files, filter_trail_logs
from cloudwatch_alarm_wrapper import (CloudWatchAlarmWrapper,
                                      STAT_AVERAGE,
                                      STAT_MAXIMUM,
                                      COMPARISON_OP_GREATER_THAN,
                                      COMPARISON_OP_LESS_THAN)

from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# The following const should not be modified
EC2_EVENT = "RunInstances"
RDS_EVENT = "CreateDBInstance"
RDS_ENGINE_MYSQL = "mysql"
RDS_ENGINE_POSTGRES = "postgres"
METRIC_NAMESPACE_EC2 = "AWS/EC2"
METRIC_NAMESPACE_RDS = "AWS/RDS"
METRIC_NAMESPACE_CW = "CWAgent"
MB_TO_BYTES = 1024 * 1024
GB_TO_BYTES = 1024 * 1024 * 1024

# The following variables should be modified according to your requirement
ec2_cpu_threshold_percentage = 85
ec2_memory_threshold_percentage = 85
ec2_disk_usage_percentage = 80
rds_cpu_threshold_percentage = 85
rds_memory_threshold_percentage = 0.2
rds_storage_threshold_percentage = 0.2
actions = os.getenv("cloudwatch_alarm_sns_topic")

def lambda_handler(event, context):
    message = event["Records"][0]["Sns"]["Message"]
    message = json.loads(message)
    s3_bucket = message["s3Bucket"]
    s3_object_key = message["s3ObjectKey"]

    event_list = [EC2_EVENT, RDS_EVENT]
    
    log_contents = unzip_log_files(s3_bucket, s3_object_key)
    target_events = filter_trail_logs(log_contents, event_list)

    for ev in target_events:
        if ev[0] == EC2_EVENT:
            instance_id = ev[1]["responseElements"]["instancesSet"]["items"][0]["instanceId"]
                
            dimensions_ec2 = [
                {
                    "Name": "InstanceId",
                    "Value": instance_id
                }
            ]
            
            metrics_ec2 = [
                {
                    "metric_name": "CPUUtilization",
                    "threshold": ec2_cpu_threshold_percentage,
                    "stat_type": STAT_AVERAGE,
                    "comparison_op": COMPARISON_OP_GREATER_THAN
                },
                {
                    "metric_name": "StatusCheckFailed_System",
                    "threshold": 0,
                    "stat_type": STAT_MAXIMUM,
                    "comparison_op": COMPARISON_OP_GREATER_THAN
                },
                {
                    "metric_name": "StatusCheckFailed_Instance",
                    "threshold": 0,
                    "stat_type": STAT_MAXIMUM,
                    "comparison_op": COMPARISON_OP_GREATER_THAN
                }
            ]
            
            for metric in metrics_ec2:
                ec2_alarm_wrapper = CloudWatchAlarmWrapper(
                    metric_namespace=METRIC_NAMESPACE_EC2,
                    metric_name=metric["metric_name"],
                    dimensions=dimensions_ec2,
                    alarm_name="_".join([instance_id, metric["metric_name"]]),
                    stat_type=metric["stat_type"],
                    threshold=metric["threshold"],
                    comparison_op=metric["comparison_op"],
                    actions=actions
                )
                try:
                    ec2_alarm_wrapper.create_metric_alarm()
                    logger.info(
                        "Created alarm {} to track metric {}.{}".format(
                            "_".join([instance_id, metric["metric_name"]]),
                            METRIC_NAMESPACE_EC2,
                            metric["metric_name"]
                        )
                    )
                except ClientError as e:
                    logger.error(
                        "Couldn't create alarm %s to metric %s.%s",
                        "_".join([instance_id, metric["metric_name"]]),
                        METRIC_NAMESPACE_EC2,
                        metric["metric_name"]
                    )
                    logger.debug(e)
                    
            metrics_ec2_cw = [
                {
                    "metric_name": "mem_used_percent",
                    "threshold": ec2_memory_threshold_percentage,
                    "stat_type": STAT_AVERAGE,
                    "comparison_op": COMPARISON_OP_GREATER_THAN
                },
                {
                    "metric_name": "disk_used_percent",
                    "threshold": ec2_disk_usage_percentage,
                    "stat_type": STAT_AVERAGE,
                    "comparison_op": COMPARISON_OP_GREATER_THAN
                }
            ]
            
            for metric in metrics_ec2_cw:
                ec2_alarm_wrapper = CloudWatchAlarmWrapper(
                    metric_namespace=METRIC_NAMESPACE_CW,
                    metric_name=metric["metric_name"],
                    dimensions=dimensions_ec2,
                    alarm_name="_".join([instance_id, metric["metric_name"]]),
                    stat_type=metric["stat_type"],
                    threshold=metric["threshold"],
                    comparison_op=metric["comparison_op"],
                    actions=actions
                )
                try:
                    ec2_alarm_wrapper.create_metric_alarm()
                    logger.info(
                        "Created alarm {} to track metric {}.{}".format(
                            "_".join([instance_id, metric["metric_name"]]),
                            METRIC_NAMESPACE_CW,
                            metric["metric_name"]
                        )
                    )
                except ClientError as e:
                    logger.error(
                        "Couldn't create alarm %s to metric %s.%s",
                        "_".join([instance_id, metric["metric_name"]]),
                        METRIC_NAMESPACE_CW,
                        metric["metric_name"]
                    )
                    logger.debug(e)
                
        if ev[0] == RDS_EVENT:
            db_instance_identifier = ev[1]["responseElements"]["dBInstanceIdentifier"]
            engine = ev[1]["responseElements"]["engine"]
            db_instance_class = ev[1]["responseElements"]["dBInstanceClass"]
            db_memory = get_memory_by_class(db_instance_class.replace("db.", ""))
            
            dimensions_rds = [
                {
                    "Name": "DBInstanceIdentifier",
                    "Value": db_instance_identifier
                }    
            ]
            
            metrics_rds = [
                {
                    "metric_name": "CPUUtilization",
                    "threshold": rds_cpu_threshold_percentage,
                    "stat_type": STAT_AVERAGE,
                    "comparison_op": COMPARISON_OP_GREATER_THAN
                },
                {
                    "metric_name": "FreeableMemory",
                    "threshold": rds_memory_threshold_percentage * db_memory * MB_TO_BYTES,
                    "stat_type": STAT_AVERAGE,
                    "comparison_op": COMPARISON_OP_LESS_THAN
                }
            ]
            
            if engine in (RDS_ENGINE_MYSQL, RDS_ENGINE_POSTGRES):
                allocated_storage = ev[1]["responseElements"]["allocatedStorage"]
                metrics_rds.append({
                    "metric_name": "FreeStorageSpace",
                    "threshold": rds_storage_threshold_percentage * int(allocated_storage) * GB_TO_BYTES,
                    "stat_type": STAT_AVERAGE,
                    "comparison_op": COMPARISON_OP_LESS_THAN
                })
            
            for metric in metrics_rds:
                rds_alarm_wrapper = CloudWatchAlarmWrapper(
                    metric_namespace=METRIC_NAMESPACE_RDS,
                    metric_name=metric["metric_name"],
                    dimensions=dimensions_rds,
                    alarm_name="_".join([db_instance_identifier, metric["metric_name"]]),
                    stat_type=metric["stat_type"],
                    threshold=metric["threshold"],
                    comparison_op=metric["comparison_op"],
                    actions=actions
                )
                try:
                    rds_alarm_wrapper.create_metric_alarm()
                    logger.info(
                        "Created alarm {} to track metric {}.{}".format(
                            "_".join([db_instance_identifier, metric["metric_name"]]),
                            METRIC_NAMESPACE_RDS,
                            metric["metric_name"]
                        )
                    )
                except ClientError as e:
                    logger.error(
                        "Couldn't create alarm %s to metric %s.%s",
                        "_".join([db_instance_identifier, metric["metric_name"]]),
                        METRIC_NAMESPACE_RDS,
                        metric["metric_name"]
                    )
                    logger.debug(e)
