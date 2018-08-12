from cloudshell.cp.core import DriverRequestParser
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.cp.core.models import DriverResponse, DeployApp, DeployAppResult, VmDetailsProperty, VmDetailsData, \
    VmDetailsNetworkInterface
from cloudshell.shell.core.driver_context import InitCommandContext, AutoLoadCommandContext, ResourceCommandContext, \
    AutoLoadAttribute, AutoLoadDetails, CancellationContext, ResourceRemoteCommandContext
from cloudshell.api.cloudshell_api import CloudShellAPISession
import cloudHandler
from cloudshell.cp.core.utils import single
from cloudshell.core.logger import qs_logger
from data_model import *  # run 'shellfoundry generate' to generate data model classes
from openstack.compute.v2.server import Server


import json
import uuid

class HuaweicloudDriver (ResourceDriverInterface):

    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
        self.request_parser = DriverRequestParser()

    def initialize(self, context):
        """
        Initialize the driver session, this function is called everytime a new instance of the driver is created
        This is a good place to load and cache the driver configuration, initiate sessions etc.
        :param InitCommandContext context: the context the command runs on
        """
        self._connect_to_cloud(context)
        self.logger = qs_logger._create_logger(
            log_group='Huawei',
            log_category='Huawei_Cloud',
            log_file_prefix='HWC'
        )

    # <editor-fold desc="Discovery">

    def _get_api_session(self, context):
        try:
            domain = context.reservation.domain
        except:
            domain = 'Global'
        try:
            session = CloudShellAPISession(host=context.connectivity.server_address,
                                   token_id=context.connectivity.admin_auth_token,
                                   domain=domain
                                       )
        except:
            session = CloudShellAPISession(
                host='192.168.85.15',
                username='admin',
                password='admin',
                domain=domain
            )

        return session


    def _connect_to_cloud(self, context):

        # resource = Huaweicloud.create_from_context(context)
        session = self._get_api_session(context)
        try:
            cloud = cloudHandler.huawei_cloud_provider(
                username=context.resource.attributes.get('Huaweicloud.user'),
                password=session.DecryptPassword(context.resource.attributes.get('Huaweicloud.password')).Value,
                projectId=context.resource.attributes.get('Huaweicloud.projectId'),
                userDomainId=context.resource.attributes.get('Huaweicloud.userDomainID')
            )

        except Exception as e:
            if e.message.__contains__('401'):
                raise (Exception('can not connect. credentials are wrong'))
            elif e.message.__contains__('400'):
                raise (Exception('can not connect. project ID is wrong'))
            else:
                raise(e)
        return cloud

    def get_inventory(self, context):
        """
        Discovers the resource structure and attributes.
        :param AutoLoadCommandContext context: the context the command runs on
        :return Attribute and sub-resource information for the Shell resource you can return an AutoLoadDetails object
        :rtype: AutoLoadDetails
        """

        # run 'shellfoundry generate' in order to create classes that represent your data model

        return AutoLoadDetails([], [])

    # </editor-fold>

    # <editor-fold desc="Mandatory Commands">

    def Deploy(self, context, request=None, cancellation_context=None):
        """
        Deploy
        :param ResourceCommandContext context:
        :param str request: A JSON string with the list of requested deployment actions
        :param CancellationContext cancellation_context:
        :return:
        :rtype: str
        """

        '''
        # parse the json strings into action objects
        actions = self.request_parser.convert_driver_request_to_actions(request)
        
        # extract DeployApp action
        deploy_action = single(actions, lambda x: isinstance(x, DeployApp))
        
        # if we have multiple supported deployment options use the 'deploymentPath' property 
        # to decide which deployment option to use. 
        deployment_name = deploy_action.actionParams.deployment.deploymentPath
        
        deploy_result = _my_deploy_method(context, actions, cancellation_context)
        return DriverResponse(deploy_result).to_driver_response_json()
        '''

        self.logger.info('got into deploy')

        json_req = json.dumps(request, default=lambda o: o.__dict__,
                   sort_keys=True, indent=4)

        self.logger.info(json_req)
        actions = self.request_parser.convert_driver_request_to_actions(request)
        self.logger.info('connecting')

        cloud = self._connect_to_cloud(context)

        self.logger.info('deploying')
        self.logger.info('deployed')

        deploy_action = single(actions, lambda x: isinstance(x, DeployApp))
        self.logger.info('deploy action JSON')

        #delete me
        if(isinstance(deploy_action,DeployApp)):
            pass

        deployment_name = deploy_action.actionParams.deployment.deploymentPath

        raw_result = self.deploy_hwc_from_image(context, deploy_action, cancellation_context, cloud)
        #delete me
        if(isinstance(raw_result,Server)):
            pass
        deploy_result = DeployAppResult(
            vmName=raw_result.name,
            actionId=deploy_action.actionId,
            vmUuid='',
            success=True,
            deployedAppAddress=raw_result.addresses.get(raw_result.addresses.keys()[0])[0].get('addr'),
            deployedAppAttributes=[],
            vmDetailsData=None
            # VmDetailsCreator.extract_vm_details(raw_result)
        )

        # handle if Elastic IP is needed
        # if deploy_action.actionParams.deployment.attributes.get('Huaweicloud.HWC_deploy_from_image.EIP') == 'True':
        #     new_ip = cloud.createEIP(cloud.get_vm_port_id(raw_result))

        my_response = DriverResponse([deploy_result]).to_driver_response_json()
        self.logger.info('my response is : {0}'.format(my_response))
        return my_response
        # return DriverResponse('none')

    def deploy_hwc_from_image(self, context, deploy_action, cancellation_context, cloud):
        my_uuid = str(uuid.uuid4())[:8]
        my_app_name = '{0}_{1}'.format(deploy_action.actionParams.appName, my_uuid)
        self.logger.info(my_app_name)
        vm_obj = cloud.create_vm(name=my_app_name,
                                 image=deploy_action.actionParams.deployment.attributes.get('Huaweicloud.HWC_deploy_from_image.image'))
        return vm_obj

    def PowerOn(self, context, ports):
        """
        Will power on the compute resource
        :param ResourceRemoteCommandContext context:
        :param ports:
        """
        pass

    def PowerOff(self, context, ports):
        """
        Will power off the compute resource
        :param ResourceRemoteCommandContext context:
        :param ports:
        """
        pass

    def PowerCycle(self, context, ports, delay):
        pass

    def DeleteInstance(self, context, ports):
        """
        Will delete the compute resource
        :param ResourceRemoteCommandContext context:
        :param ports:
        """
        self.logger.info('started delete')
        cloud = self._connect_to_cloud(context)
        self.logger.info('got session to cloud')
        resource_name_to_delete = context.remote_endpoints[0].name
        server_to_delete = cloud.conn.compute.find_server(resource_name_to_delete)
        self.logger.info('deleting server {}'.format(resource_name_to_delete))
        cloud.delete_vm(server_to_delete)
        self.logger.info('server {} deleted'.format(resource_name_to_delete))

    def GetVmDetails(self, context, requests, cancellation_context):
        """

        :param ResourceCommandContext context:
        :param str requests:
        :param CancellationContext cancellation_context:
        :return:
        """
        pass

    def remote_refresh_ip(self, context, ports, cancellation_context):
        """
        Will update the address of the computer resource on the Deployed App resource in cloudshell
        :param ResourceRemoteCommandContext context:
        :param ports:
        :param CancellationContext cancellation_context:
        :return:
        """
        pass

    # </editor-fold>


    ### NOTE: According to the Connectivity Type of your shell, remove the commands that are not
    ###       relevant from this file and from drivermetadata.xml.

    # <editor-fold desc="Mandatory Commands For L2 Connectivity Type">

    def ApplyConnectivityChanges(self, context, request):
        """
        Configures VLANs on multiple ports or port-channels
        :param ResourceCommandContext context: The context object for the command with resource and reservation info
        :param str request: A JSON string with the list of requested connectivity changes
        :return: a json object with the list of connectivity changes which were carried out by the driver
        :rtype: str
        """
        pass

    # </editor-fold> 

    # <editor-fold desc="Mandatory Commands For L3 Connectivity Type">

    def PrepareSandboxInfra(self, context, request, cancellation_context):
        """

        :param ResourceCommandContext context:
        :param str request:
        :param CancellationContext cancellation_context:
        :return:
        :rtype: str
        """
        '''
        # parse the json strings into action objects
        actions = self.request_parser.convert_driver_request_to_actions(request)
        
        action_results = _my_prepare_connectivity(context, actions, cancellation_context)
        
        return DriverResponse(action_results).to_driver_response_json()    
        '''
        pass

    def CleanupSandboxInfra(self, context, request):
        """

        :param ResourceCommandContext context:
        :param str request:
        :return:
        :rtype: str
        """
        '''
        # parse the json strings into action objects
        actions = self.request_parser.convert_driver_request_to_actions(request)
        
        action_results = _my_cleanup_connectivity(context, actions)

        return DriverResponse(action_results).to_driver_response_json()    
        '''
        pass

    # </editor-fold>

    # <editor-fold desc="Optional Commands For L3 Connectivity Type">

    def SetAppSecurityGroups(self, context, request):
        """

        :param ResourceCommandContext context:
        :param str request:
        :return:
        :rtype: str
        """
        pass

    # </editor-fold>

    def cleanup(self):
        """
        Destroy the driver session, this function is called everytime a driver instance is destroyed
        This is a good place to close any open sessions, finish writing to log files, etc.
        """
        pass


class VmDetailsCreator(object):
    @staticmethod
    def extract_vm_details(vm_instance):
        vm_instance_data = VmDetailsCreator.extract_vm_instance_data(vm_instance)
        vm_network_data = VmDetailsCreator.extract_vm_instance_network_data(vm_instance)

        return VmDetailsData(vmInstanceData=vm_instance_data, vmNetworkData=vm_network_data)

    @staticmethod
    def extract_vm_instance_data(instance):
        data = [
            VmDetailsProperty(key='Cloud Name', value="HWI"),
            VmDetailsProperty(key='Cloud Index', value='0'),
            VmDetailsProperty(key='Cloud Size', value='not so big'),
            VmDetailsProperty(key='Instance Name', value="app name"),
        ]

        return data

    @staticmethod
    def extract_vm_instance_network_data(instance):
        network_interfaces = []

        # for each network interface
        for i in range(2):
            network_data = [
                VmDetailsProperty(key='MaxSpeed', value='1KB'),
                VmDetailsProperty(key='Network Type', value='Ethernet'),
            ]

            current_interface = VmDetailsNetworkInterface(interfaceId=i, networkId=i,
                                                          isPrimary=i == 0,  # if nic is the primary interface
                                                          isPredefined=False,
                                                          # if the network existed before reservation
                                                          networkData=network_data,
                                                          privateIpAddress='10.0.0.' + str(i),
                                                          publicIpAddress='8.8.8.' + str(i))
            network_interfaces.append(current_interface)

        return network_interfaces
