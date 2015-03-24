#    Copyright 2015 Mirantis, Inc
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import json
import logging
import sys
import time

from keystoneclient.auth.identity import v2
from keystoneclient import session
from neutronclient.neutron import client as neutron_cli
from novaclient import client as nova_cli
from oslo.config import cfg
from oslo_utils import importutils
import pika
from pika import exceptions

from oss_framework import cfg as config
from oss_framework import logger


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class Handler(object):
    """Base class to handle events."""
    def __init__(self, events_creation, events_deletion):
        auth = v2.Password(auth_url=CONF.openstack.auth_url,
                           username=CONF.openstack.user,
                           password=CONF.openstack.password,
                           tenant_name=CONF.openstack.tenant)
        sess = session.Session(auth=auth)
        self.nova_cli = nova_cli.Client(2, session=sess)
        self.neutron_cli = neutron_cli.Client(2.0, session=sess)
        self.events_creation = events_creation
        self.events_deletion = events_deletion
        self.plugins = []
        plugins = CONF.enabled_plugins
        for plugin in plugins:
            plugin_class = 'oss_framework.plugins.%s' % plugin
            self.plugins.append(
                importutils.import_class(plugin_class)())
            LOG.info('Plugin `%s`is loaded.' % plugin_class)

    def _get_network_info_from_neutron(self, payload, created):
        address = payload['floatingip']['floating_ip_address']
        type_address = 'Public'
        return address, type_address

    def _get_network_info(self, payload, *args):
        network_info = payload.get('fixed_ips')
        address = None
        type_address = None
        for nw_info in network_info:
            floating_ips = nw_info.get('floating_ips')
            address = nw_info['address']
            type_address = 'Private'
            if floating_ips:
                address = floating_ips[0]['address']
                type_address = 'Public'
            return address, type_address

    def _convert_to_node_detail(self, payload, nw_info):
        """Convert payload to node's info for plugins."""
        ip, type_ip = nw_info
        os_name = payload.get('image_meta', {}).get('os', None)
        result = {
            "FQDN": payload['hostname'],
            "IP": ip,
            "ID": payload['instance_id'],
            "IPType": "Public",
            "OS": os_name,
            "Storage": payload['disk_gb'],
            "Ram": payload['memory_mb'],
            "CPU": payload['vcpus'],
            "Datacenter": "KDC",
            "SecurityDomain": "DQT",
            "Metadata": payload['metadata'],
            "CreationDate": payload['created_at']}
        return result

    def get_data(self, body):
        """Get instance data from payload."""
        decoded = json.loads(body)
        return decoded

    def _update_payload(self, payload):
        port_id = payload['port_id']
        port = self.neutron_cli.show_port(port_id)
        instance_id = port['port']['device_id']
        instance = self.nova_cli.servers.get(instance_id)
        flavor_id = instance.flavor['id']
        flavor = self.nova_cli.flavors.get(flavor_id)
        image = self.nova_cli.images.get(instance.image['id'])
        payload.update({
            'instance_id': instance.id,
            'hostname': instance.name,
            'metadata': instance.metadata,
            'image_meta': image.metadata,
            'created_at': instance.created,
            'disk_gb': flavor.disk,
            'memory_mb': flavor.ram,
            'vcpus': flavor.vcpus,
        })

    def callback(self, ch, method, properties, body):
        """Handle event."""
        data = self.get_data(body)
        event = data['event_type']
        created = event in self.events_creation
        deleted = event in self.events_deletion
        if created or deleted:
            LOG.info('Handle event `%s`.' % event)
            payload = data['payload']
            floating = event == 'floatingip.update.end'
            if floating:
                created = payload['floatingip']['router_id'] is not None
                deleted = not created
                get_nw_info = self._get_network_info_from_neutron
                self._update_payload(payload)
            else:
                get_nw_info = self._get_network_info
            try:
                nw_info = get_nw_info(payload, created)
            except Exception:
                LOG.error("Wrong format of payload in network info.")
                return
            try:
                node_detail = self._convert_to_node_detail(payload, nw_info)
            except Exception:
                LOG.error("Wrong format of payload.")
                return
            for plugin in self.plugins:
                plugin.notify(node_detail, created)


def main():
    config.parse_args(sys.argv)
    logger.setup(log_file=CONF.log_file)

    host, port = CONF.rabbit.host, CONF.rabbit.port
    user, password = CONF.rabbit.user, CONF.rabbit.password
    queue = CONF.rabbit.watch_queue
    LOG.info('Listen queue %s' % (queue))
    events_creation = CONF.events_creation
    events_deletion = CONF.events_deletion
    LOG.info('Handled events of creation: %s' % ''.join(events_creation))
    LOG.info('Handled events of deletion: %s' % ''.join(events_deletion))
    handler = Handler(events_creation, events_deletion)
    while True:
        try:
            credentials = pika.PlainCredentials(user, password)
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host,
                                          port,
                                          '/',
                                          credentials))
            channel = connection.channel()

            channel.basic_consume(handler.callback,
                                  queue=queue,
                                  no_ack=True)

            channel.start_consuming()
        except (exceptions.AMQPConnectionError, exceptions.ChannelClosed):
            LOG.warning('Rabbit service is unavailable', exc_info=True)
            time.sleep(10)
            continue
