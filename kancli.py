from asyncio.windows_events import NULL
from os import getlogin
import click
import boto3
import logging
import logging.handlers
import sys
from tabulate import tabulate

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
    logger = logging.getLogger()
    logger.debug("Running function 'get_instances_boto'")
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
            logger.critical(ex)
            exception_print(ex)
    return instance_data_dict_list


def stop_instance_boto(ec2_client, instance_id):
    logger = logging.getLogger()
    logger.debug("Running function 'stop_instance_boto'")
    logger.info(f"Stopping Instance: {instance_id}")
    ec2_client.stop_instances(InstanceIds=[instance_id])


def start_instance_boto(ec2_client, instance_id):
    logger = logging.getLogger()
    logger.debug("Running function 'start_instance_boto'")
    logger.info(f"Starting Instance: {instance_id}")
    ec2_client.start_instances(InstanceIds=[instance_id])


def terminate_instance_boto(ec2_client, instance_id):
    logger = logging.getLogger()
    logger.debug("Running function 'terminate_instance_boto'")
    logger.info(f"Terminating Instance: {instance_id}")
    ec2_client.terminate_instances(InstanceIds=[instance_id])


def exception_print(ex):
    click.secho("Error!", fg="red", bold=True)
    click.secho((str(ex).split(':', 1)[1])[1:], fg="red")


def init_logging(debug_enabled: bool):
    # Find way to disable print to console
    logging.getLogger('boto3').setLevel(logging.CRITICAL)
    logging.getLogger('botocore').setLevel(logging.CRITICAL)
    logging.getLogger('s3transfer').setLevel(logging.CRITICAL)

    logging.basicConfig(
        format='%(asctime)s %(filename)s[%(levelname)s]: %(message)s')
    logger = logging.getLogger()
    logging.StreamHandler(stream=None)
    logger.setLevel(logging.INFO)
    file_handler = logging.handlers.RotatingFileHandler(
        filename='kandula.log', maxBytes=5000000, backupCount=10)
    logger.addHandler(file_handler)
    if debug_enabled:
        logger.setLevel(logging.DEBUG)
    logger.propagate = False


@click.group()
@click.option('--debug/--no-debug', is_flag=True, default=False, help="Print debugging messages")
@click.pass_context
def kancli(ctx, debug):
    click.secho('Welcome to kancli \n', fg="cyan", bold=True, underline=True)
    ctx.obj['DEBUG'] = debug
    ctx.obj['ec2_client'] = boto3.client('ec2')
    init_logging(debug)
    ctx.obj['logger'] = logging.getLogger()


@kancli.command()
@click.pass_context
def get_instances(ctx):
    """Get Instance ID and State"""
    ctx.obj['logger'].debug("Running function 'get_instances'")
    try:
        ctx.obj['logger'].debug(f"Request to get instances")
        instances = get_instances_boto(ctx.obj['ec2_client'])
        ctx.obj['logger'].debug(f"Successfully retrieved instances")
        instances_table = []
        for instance in instances:
            data = []
            data.append(instance['Id'])
            data.append(instance['Type'])
            data.append(instance['Region'])
            data.append(instance['State'])
            if instance['State'] == "running":
                data.append(instance['PrivateIpAddress'])
            instances_table.append(data)
        click.echo(tabulate(instances_table, headers=[
                   "ID", "Type", "Region", "State", "IP Address"]))
        ctx.obj['logger'].info(instances_table)
    except Exception as ex:
        ctx.obj['logger'].error(ex)
        exception_print(ex)


@kancli.command()
@click.pass_context
@click.option('-I', '--instance-id', help="Instance ID", type=str, required=True, prompt="Enter instance ID")
def stop_instance(ctx, instance_id):
    """Stop Instnace"""
    ctx.obj['logger'].debug("Running function 'stop_instance'")
    click.echo(f"Are you sure you want to stop instance: {instance_id}?")
    value = click.confirm('Are you sure?')
    if value:
        try:
            ctx.obj['logger'].debug(f"Request to stop instance: {instance_id}")
            stop_instance_boto(ctx.obj['ec2_client'], instance_id)
            ctx.obj['logger'].info(f"Instance: {instance_id} has been stopped")
        except Exception as ex:
            ctx.obj['logger'].error(ex)
            exception_print(ex)
    else:
        click.echo("Cancelling")


@kancli.command()
@click.pass_context
@click.option('-I', '--instance-id', help="Instance ID", type=str, required=True, prompt="Enter instance ID")
def start_instance(ctx, instance_id):
    """Start Instnace"""
    ctx.obj['logger'].debug("Running function 'start_instance'")
    click.echo(f"Are you sure you want to start instance: {instance_id}?")
    value = click.confirm('Are you sure?')
    if value:
        try:
            ctx.obj['logger'].debug(
                f"Request to start instance: {instance_id}")
            start_instance_boto(ctx.obj['ec2_client'], instance_id)
            ctx.obj['logger'].info(f"Instance: {instance_id} has been started")
        except Exception as ex:
            ctx.obj['logger'].error(ex)
            exception_print(ex)
    else:
        click.echo("Cancelling")


@ kancli.command()
@ click.pass_context
@ click.option('-I', '--instance-id', help="Instance ID", type=str, required=True, prompt="Enter instance ID")
def terminate_instance(ctx, instance_id):
    """Terminate Instnace"""
    ctx.obj['logger'].debug("Running function 'terminate_instance'")
    click.echo(f"Are you sure you want to terminate instance: {instance_id}?")
    value = click.confirm('Are you sure?')
    if value:
        try:
            ctx.obj['logger'].debug(
                f"Request to terminate instance: {instance_id}")
            terminate_instance_boto(ctx.obj['ec2_client'], instance_id)
            ctx.obj['logger'].info(
                f"Instance: {instance_id} has been terminated")
            click.secho("Done!", fg="green")
        except Exception as ex:
            ctx.obj['logger'].error(ex)
            exception_print(ex)
    else:
        click.echo("Cancelling")


if __name__ == '__main__':
    kancli(obj={})
