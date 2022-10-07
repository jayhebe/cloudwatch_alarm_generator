import json
import logging
import os

from resource_helper import (get_event_list,
                             get_memory_by_class,
                             is_enable_alarms)
from cloudtrail_log_wrapper import CloudTrailLogWrapper
from cloudwatch_alarm_wrapper import CloudWatchAlarmWrapper
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

actions = os.getenv("cloudwatch_alarm_sns_topic")

def lambda_handler(event, context):
    message = event["Records"][0]["Sns"]["Message"]
    message = json.loads(message)
    s3_bucket = message["s3Bucket"]
    s3_object_key = message["s3ObjectKey"]

    event_list = get_event_list()
    log_wrapper = CloudTrailLogWrapper(s3_bucket, s3_object_key)
    target_events = log_wrapper.filter_trail_logs(event_list)

    for ev in target_events:
        if ev[0] == event_list["ec2"]:
            tag_set = ev[1]["responseElements"]["instancesSet"]["items"][0]["tagSet"]["items"]
            
            if is_enable_alarms(tag_set):
                instance_id = ev[1]["responseElements"]["instancesSet"]["items"][0]["instanceId"]
                instance_type = ev[1]["responseElements"]["instancesSet"]["items"][0]["instanceType"]
                image_id = ev[1]["responseElements"]["instancesSet"]["items"][0]["imageId"]

                ec2_value_mapping = {
                    "$instance_id": instance_id,
                    "$instance_type": instance_type,
                    "$image_id": image_id
                }

                ec2_alarm_wrapper = CloudWatchAlarmWrapper("ec2", ec2_value_mapping)
                ec2_alarms = ec2_alarm_wrapper.render_alarm_template()

                for alarm in ec2_alarms:
                    try:
                        ec2_alarm_wrapper.create_metric_alarm(
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
                        logger.error(e)
                
        if ev[0] == event_list["rds"]:
            tag_list = ev[1]["responseElements"]["tagList"]

            if is_enable_alarms(tag_list):
                db_instance_identifier = ev[1]["responseElements"]["dBInstanceIdentifier"]
                engine = ev[1]["responseElements"]["engine"]
                db_instance_class = ev[1]["responseElements"]["dBInstanceClass"]
                db_memory = get_memory_by_class(db_instance_class.replace("db.", ""))
                
                if engine in ("mysql", "postgres"):
                    allocated_storage = ev[1]["responseElements"]["allocatedStorage"]

                    rds_value_mapping = {
                        "$db_instance_identifier": db_instance_identifier,
                        "$memory_size": str(db_memory),
                        "$disk_size": str(allocated_storage)
                    }

                    rds_alarm_wrapper = CloudWatchAlarmWrapper("rds", rds_value_mapping)
                    rds_alarms = rds_alarm_wrapper.render_alarm_template()

                    for alarm in rds_alarms:
                        try:
                            rds_alarm_wrapper.create_metric_alarm(
                                metric_namespace=alarm["MetricNameSpace"],
                                metric_name=alarm["MetricName"],
                                dimensions=alarm["Dimensions"],
                                alarm_name="_".join([db_instance_identifier, alarm["MetricName"]]),
                                stat_type=alarm["StatType"],
                                threshold=(
                                    alarm["Threshold"]["percentage"] * 
                                    int(alarm["Threshold"]["size"]) * 
                                    alarm["Threshold"]["conversion"]
                                ),
                                comparison_op=alarm["ComparisonOp"],
                                actions=actions,
                                period=alarm["Period"],
                                eval_periods=alarm["EvaluationPeriods"]
                            )

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
                            logger.error(e)

        if ev[0] == event_list["elb"]:
            tags = ev[1]["requestParameters"].get("tags")

            if not tags or is_enable_alarms(tags):
                load_balancer_type = ev[1]["responseElements"]["loadBalancers"][0]["type"]
                load_balancer_name = ev[1]["responseElements"]["loadBalancers"][0]["loadBalancerName"]
                load_balancer_arn = ev[1]["responseElements"]["loadBalancers"][0]["loadBalancerArn"]
                load_balancer_id = load_balancer_arn.split("/", maxsplit=1)[1]

                elb_value_mapping = {
                    "$load_balancer_id": load_balancer_id
                }

                if load_balancer_type == "application":
                    elb_alarm_wrapper = CloudWatchAlarmWrapper("alb", elb_value_mapping)
                elif load_balancer_type == "network":
                    elb_alarm_wrapper = CloudWatchAlarmWrapper("nlb", elb_value_mapping)
                
                elb_alarms = elb_alarm_wrapper.render_alarm_template()

                for alarm in elb_alarms:
                    try:
                        elb_alarm_wrapper.create_metric_alarm(
                            metric_namespace=alarm["MetricNameSpace"],
                            metric_name=alarm["MetricName"],
                            dimensions=alarm["Dimensions"],
                            alarm_name="_".join([load_balancer_name, alarm["MetricName"]]),
                            stat_type=alarm["StatType"],
                            threshold=alarm["Threshold"],
                            comparison_op=alarm["ComparisonOp"],
                            actions=actions,
                            period=alarm["Period"],
                            eval_periods=alarm["EvaluationPeriods"]
                        )

                        logger.info(
                            "Created alarm {} to track metric {}.{}".format(
                                "_".join([load_balancer_name, alarm["MetricName"]]),
                                alarm["MetricNameSpace"],
                                alarm["MetricName"]
                            )
                        )
                    except ClientError as e:
                        logger.error(
                            "Couldn't create alarm {} to metric {}.{}".format(
                                "_".join([load_balancer_name, alarm["MetricName"]]),
                                alarm["MetricNameSpace"],
                                alarm["MetricName"]
                            )
                        )
                        logger.error(e)
