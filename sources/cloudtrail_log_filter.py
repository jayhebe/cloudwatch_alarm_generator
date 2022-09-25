import json
import boto3
import logging
import gzip

logger = logging.getLogger()

def unzip_log_files(s3_bucket, s3_object_key):
    '''
    Extract the .gz log files on S3 and return
    a list of CloudTrail logs in string format
    '''

    log_contents = []
    s3 = boto3.client('s3')
    for object_key in s3_object_key:
        log_file = s3.get_object(Bucket=s3_bucket, Key=object_key)["Body"]
        logger.info("Extract file {}".format(object_key))
        with gzip.open(log_file, "rb") as fp_log:
            log_contents.append(fp_log.read().decode("utf8"))
            
    return log_contents
            
def filter_trail_logs(log_contents, event_list):
    '''
    Filter out the CloudTrail logs and 
    return specified event types list from CloudTrail logs
    with the format like [(eventName, eventContent)]
    '''

    target_events = []
    for content in log_contents:
        events = json.loads(content)["Records"]
        for event in events:
            logger.debug("Event Name: {}".format(event["eventName"]))
            if event["eventName"] in event_list.values():
                target_events.append((event["eventName"], event))
            
    return target_events
