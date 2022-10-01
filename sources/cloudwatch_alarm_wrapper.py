import boto3
import json

class CloudWatchAlarmWrapper():
    def __init__(self,
                 service_name,
                 value_mapping,
                 config_file_path="config"):

        self.value_mapping = value_mapping
        self.config_file = "/".join([config_file_path, service_name + ".json"])

    def render_alarm_template(self):
        with open(self.config_file, "r") as config_fp:
            alarm_template = config_fp.read()
        
        for key, value in self.value_mapping.items():
            alarm_template = alarm_template.replace(key, value)

        return json.loads(alarm_template)["Alarms"]
        
    def create_metric_alarm(self,
                            metric_namespace,
                            metric_name,
                            dimensions,
                            alarm_name,
                            stat_type,
                            threshold,
                            comparison_op,
                            actions,
                            period,
                            eval_periods):   
        cloudwatch = boto3.client('cloudwatch')
        alarm = cloudwatch.put_metric_alarm(
            Namespace=metric_namespace,
            MetricName=metric_name,
            AlarmName=alarm_name,
            Statistic=stat_type,
            Period=period,
            EvaluationPeriods=eval_periods,
            Threshold=threshold,
            ComparisonOperator=comparison_op,
            Dimensions=dimensions,
            AlarmActions=[actions]
        )
    
        return alarm
