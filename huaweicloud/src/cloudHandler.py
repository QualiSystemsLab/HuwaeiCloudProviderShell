from openstack import connection
import time

# create connection

class huawei_cloud_provider():
    def __init__(self, username, password, projectId, userDomainId):
        self.username = username
        self.password = password
        self.projectId = projectId    # tenant ID
        self.userDomainId = userDomainId   # user account ID
        self.auth_url = "https://iam.ap-southeast-1.myhwclouds.com/v3"    # endpoint url
        self.conn = connection.Connection(auth_url=self.auth_url,
                                          user_domain_id=self.userDomainId,
                                          project_id=self.projectId,
                                          username=self.username,
                                          password=self.password)
        nets = [net for net in self.conn.network.networks() if net.name]
        self.internal_net = [net for net in nets if not net.is_router_external][0]
        self.external_net = [net for net in nets if net.is_router_external][0]

    def create_vm(self, name, image, flavor):
        image_obj = self.conn.compute.find_image(image,
                                             ignore_missing=False)
        server = self.conn.compute.create_server(
            name=name,
            flavor_id=flavor,
            image_id=image_obj.id,
           # key_name='QualikeyPair',
            admin_password='Quali!23456',
            networks=[{"uuid": '{}'.format(self.internal_net.id)}]
        )
        self.conn.compute.wait_for_server(server)


        return server

    def get_all_flavors(self):
        for flavor in self.conn.compute.flavors():
            print flavor.name

    def get_all_images(self):
        images = []
        for image in self.conn.compute.images():
            # print image.id, image.name
            images.append(image)
        return images

    def create_security_groups(self):
        # create_SG
        testSGName = "PythonSDKSG"
        createdSG = self.conn.network.create_security_group(
            name=testSGName
        )
        # open a port.
        self.conn.network.security_group_open_port(createdSG.id, 8080, protocol='tcp')
       # allow ping
        self.conn.network.security_group_allow_ping(createdSG.id)
        # More detailed rules
        IPV4 = 'IPv4'
        PROTO = 'tcp'
        PORT = 22
        DIR = 'ingress'
        self.conn.network.create_security_group_rule(
            direction=DIR,
            ethertype=IPV4,
            port_range_max=PORT,
            port_range_min=PORT,
            protocol=PROTO,
            security_group_id=createdSG.id
        )

    def createEIP(self, port_id):
        eip = self.conn.network.create_ip(floating_network_id=self.external_net.id ,port_id=port_id)
        count = 1
        createFlag = False
        while(count < 10):
            if(self.conn.network.get_ip(eip.id).status == 'ACTIVE'):
                createFlag = True
                print 'eip created successfully'
                break
            count = count + 1
            time.sleep(1)
        if(not createFlag):
             print 'eip create failed'
        return eip

    def get_vm_port_id(self, server):
        ifs = list(self.conn.compute.server_interfaces(server))
        port_id = ifs[0].port_id
        return port_id

    def delete_vm(self, server):
        self.conn.compute.delete_server(server.id)
        self.conn.compute.wait_for_delete(server)

    def disassociate_eip(self, server):
        port_id = self.get_vm_port_id(server)
        eip = self.conn.network.create_ip(floating_network_id=self.external_net.id, port_id=port_id)
        self.conn.compute.remove_floating_ip_from_server(server,
                                                    eip.floating_ip_address)
        disCount = 1
        removeFlag = False
        while (disCount < 10):
            if (self.conn.network.get_ip(eip.id).status == 'DOWN'):
                removeFlag = True
                print 'eip disassociate success'
                break
            count = count + 1
            time.sleep(1)

        if (not removeFlag):
            print 'eip disassociate failed'