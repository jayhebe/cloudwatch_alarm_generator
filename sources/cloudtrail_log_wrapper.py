import json
import boto3
import logging
import gzip

logger = logging.getLogger()

class CloudTrailLogWrapper():
    def __init__(self, s3_bucket, s3_object_key):
        self.s3_bucket = s3_bucket
        self.s3_object_key = s3_object_key

        self.log_content = []

    def _unzip_log_files(self):
        '''
        Extract the .gz log files on S3 and return
        a list of CloudTrail logs in string format
        '''
        s3 = boto3.client('s3')
        for object_key in self.s3_object_key:
            log_file = s3.get_object(Bucket=self.s3_bucket, Key=object_key)["Body"]
            logger.info("Extract file {}".format(object_key))
            with gzip.open(log_file, "rb") as fp_log:
                self.log_content.append(fp_log.read().decode("utf8"))
                                
    def filter_trail_logs(self, event_list):
        '''
        Filter out the CloudTrail logs and 
        return specified event types list from CloudTrail logs
        with the format like [(event_name, event_content)]
        '''
        self._unzip_log_files()

        target_events = []
        for content in self.log_content:
            events = json.loads(content)["Records"]
            for event in events:
                logger.info("Event Name: {}".format(event["eventName"]))
                if event["eventName"] in event_list.values():
                    target_events.append((event["eventName"], event))
                
        return target_events
