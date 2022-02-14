import botocore.exceptions
import click
import boto3

fields_translation = {
    "Id": "InstanceId",
    "Type": "InstanceType",
    "ImageId": "ImageId",
    "LaunchTime": "LaunchTime",
    "SubnetId": "SubnetId",
    "VpcId": "VpcId",
    "PrivateDnsName": "PrivateDnsName",
    "PrivateIpAddress": "PrivateIpAddress",
    "PublicDnsName": "PublicDnsName",
    "RootDeviceName": "RootDeviceName",
    "RootDeviceType": "RootDeviceType",
    "SecurityGroups": "SecurityGroups",
    "Tags": "Tags",
}


def get_instance_state_data(instance_data_dict, instance):
    if instance["State"]["Name"] == "running":
        instance_data_dict["StateReason"] = None
        if "PublicIpAddress" not in instance:
            instance_data_dict["PublicIpAddress"] = None
        else:
            instance_data_dict["PublicIpAddress"] = instance["PublicIpAddress"]
    elif instance["State"]["Name"] == "pending":
        instance_data_dict["PublicIpAddress"] = None
    else:
        instance_data_dict["StateReason"] = instance["StateReason"]["Message"]
        instance_data_dict["PublicIpAddress"] = None


def get_instances_boto(ec2_client):
    my_instances = ec2_client.describe_instances()

    instances_data = []
    instance_data_dict_list = []

    for instance in my_instances["Reservations"]:
        for data in instance["Instances"]:
            instances_data.append(data)

    for instance in instances_data:
        try:
            instance_data_dict = {}
            for key, value in fields_translation.items():
                if value in instance:
                    instance_data_dict[key] = instance[value]
            instance_data_dict["Cloud"] = "aws"
            instance_data_dict["Region"] = ec2_client.meta.region_name
            instance_data_dict["State"] = instance["State"]["Name"]

            network_interfaces = instance["NetworkInterfaces"]
            if len(network_interfaces) > 0:
                instance_data_dict["MacAddress"] = network_interfaces[0][
                    "MacAddress"
                ]
                instance_data_dict["NetworkInterfaceId"] = network_interfaces[0][
                    "NetworkInterfaceId"
                ]
            get_instance_state_data(instance_data_dict, instance)
            instance_data_dict_list.append(instance_data_dict)
        except Exception as ex:
            exception_print(ex)
    return instance_data_dict_list


def stop_instance_boto(ec2_client, instance_id):
    ec2_client.stop_instances(InstanceIds=[instance_id])


def start_instance_boto(ec2_client, instance_id):
    ec2_client.start_instances(InstanceIds=[instance_id])


def terminate_instance_boto(ec2_client, instance_id):
    ec2_client.terminate_instances(InstanceIds=[instance_id])


def exception_print(ex):
    click.secho("Error!", fg="red", bold=True)
    click.secho((str(ex).split(':', 1)[1])[1:], fg="red")


@click.group()
@click.option('--debug/--no-debug', is_flag=True, default=False, help="Print debugging messages")
@click.option('--dry/--no-dry', is_flag=True, default=True, help="")
@click.pass_context
def kancli(ctx, debug, dry):
    click.secho('Welcome to kancli \n', fg="cyan", bold=True, underline=True)
    ctx.obj['DEBUG'] = debug
    ctx.obj['DRY'] = dry
    ctx.obj['ec2_client'] = boto3.client('ec2')


@kancli.command()
@click.pass_context
def get_instances(ctx):
    """Get Instance ID and State"""
    instances = get_instances_boto(ctx.obj['ec2_client'])
    for instance in instances:
        click.echo(f"Instance ID: {instance['Id']}")
        click.echo(f"Instance State: {instance['State']} \n")


@kancli.command()
@click.pass_context
@click.option('-I', '--instance-id', help="Instance ID", type=str, required=True, prompt="Enter instance ID")
def stop_instance(ctx, instance_id):
    """Stop Instnace"""
    click.echo(f"Are you sure you want to stop instance: {instance_id}?")
    value = click.confirm('Are you sure?')
    if value:
        try:
            stop_instance_boto(ctx.obj['ec2_client'], instance_id)
        except Exception as ex:
            exception_print(ex)
    else:
        click.echo("Cancelling")


@kancli.command()
@click.pass_context
@click.option('-I', '--instance-id', help="Instance ID", type=str, required=True, prompt="Enter instance ID")
def start_instance(ctx, instance_id):
    """Start Instnace"""
    click.echo(f"Are you sure you want to start instance: {instance_id}?")
    value = click.confirm('Are you sure?')
    if value:
        try:
            start_instance_boto(ctx.obj['ec2_client'], instance_id)
        except Exception as ex:
            exception_print(ex)
    else:
        click.echo("Cancelling")


@kancli.command()
@click.pass_context
@click.option('-I', '--instance-id', help="Instance ID", type=str, required=True, prompt="Enter instance ID")
def terminate_instance(ctx, instance_id):
    """Terminate Instnace"""
    click.echo(f"Are you sure you want to terminate instance: {instance_id}?")
    value = click.confirm('Are you sure?')
    if value:
        try:
            terminate_instance_boto(ctx.obj['ec2_client'], instance_id)
            click.secho("Done!", fg="green")
        except Exception as ex:
            exception_print(ex)
    else:
        click.echo("Cancelling")


if __name__ == '__main__':
    kancli(obj={})
