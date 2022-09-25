import boto3

STAT_AVERAGE = "Average"
STAT_MAXIMUM = "Maximum"
COMPARISON_OP_GREATER_THAN = "GreaterThanThreshold"
COMPARISON_OP_LESS_THAN = "LessThanThreshold"

class CloudWatchAlarmWrapper():
    def __init__(self, 
                 metric_namespace,
                 metric_name,
                 dimensions,
                 alarm_name,
                 stat_type,
                 threshold,
                 comparison_op,
                 actions,
                 period=300,
                 eval_periods=1):
        self.metric_namespace = metric_namespace
        self.metric_name = metric_name
        self.dimensions = dimensions
        self.alarm_name = alarm_name
        self.stat_type = stat_type
        self.period = period
        self.eval_periods = eval_periods
        self.threshold = threshold
        self.comparison_op = comparison_op
        self.actions = actions

    def create_metric_alarm(self):   
        cloudwatch = boto3.client('cloudwatch')
        alarm = cloudwatch.put_metric_alarm(
            Namespace=self.metric_namespace,
            MetricName=self.metric_name,
            AlarmName=self.alarm_name,
            Statistic=self.stat_type,
            Period=self.period,
            EvaluationPeriods=self.eval_periods,
            Threshold=self.threshold,
            ComparisonOperator=self.comparison_op,
            Dimensions=self.dimensions,
            AlarmActions=[self.actions]
        )
    
        return alarm
