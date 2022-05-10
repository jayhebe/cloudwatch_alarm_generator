import boto3


def get_memory_by_class(class_name):
    ec2 = boto3.client("ec2")
    class_info = ec2.describe_instance_types(InstanceTypes=[class_name])
    
    return class_info["InstanceTypes"][0]["MemoryInfo"]["SizeInMiB"]
