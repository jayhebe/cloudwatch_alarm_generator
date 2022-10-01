import boto3
import json

def get_event_list(config_file_path="config/settings.json"):
    event_list = {}
    with open(config_file_path, "r") as config_fp:
        config = json.load(config_fp)
        services = config["Services"]
        for service in services:
            event_list[service["ServiceName"]] = service["ServiceEventName"]

    return event_list

def is_enable_alarms(tag_list):
    enable_alarms = "True"
    for tag in tag_list:
        if tag["key"] == "EnableAlarms":
            enable_alarms = tag["value"]
            break

    if enable_alarms == "False":
        return False
    else:
        return True

# def get_ec2_info_by_id(instance_id):
#     ec2 = boto3.resource("ec2")
#     instance = ec2.Instance(instance_id)

#     instance_type = instance.instance_type
#     image_id = instance.image_id
#     tags = instance.tags
#     for tag in tags:
#         if tag["Key"] == "Name":
#             instance_name = tag["Value"]

#     return (instance_name, image_id, instance_type)

def get_memory_by_class(class_name):
    ec2 = boto3.client("ec2")
    class_info = ec2.describe_instance_types(InstanceTypes=[class_name])
    
    return class_info["InstanceTypes"][0]["MemoryInfo"]["SizeInMiB"]
