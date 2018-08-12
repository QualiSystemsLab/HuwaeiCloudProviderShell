import cloudHandler
import json
import driver
import cloudshell.helpers.scripts.cloudshell_dev_helpers as dev_help
import cloudshell.helpers.scripts.cloudshell_scripts_helpers as script_help
from cloudshell.shell.core.driver_context import InitCommandContext, AutoLoadCommandContext, ResourceCommandContext, \
    AutoLoadAttribute, AutoLoadDetails, CancellationContext, ResourceRemoteCommandContext
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface

# Debug Script



dev_help.attach_to_cloudshell_as(
    user='admin',
    password='admin',
    domain='Global',
    reservation_id='c3f09270-58a6-4188-a11d-19239d73a0d8',
    server_address='192.168.85.15',
    resource_name='HWC'

)
driver_interface = ResourceDriverInterface


context = ResourceCommandContext(
    connectivity=script_help.get_connectivity_context_details(),
    reservation=script_help.get_reservation_context_details(),
    resource=script_help.get_resource_context_details(),
    connectors=None
)
with open('request.json', 'r') as file:
    my_request = json.load(file)

my_hwc_driver = driver.HuaweicloudDriver()
my_hwc_driver.initialize(context)
my_hwc_driver.Deploy(context, request=my_request)
pass

