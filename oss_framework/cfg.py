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


from oslo.config import cfg

from oss_framework import version


common_opts = [
    cfg.ListOpt("enabled_plugins", default=['rest_plugin.RESTNotify']),
    cfg.StrOpt("log_file", default='/var/log/oss.log'),
    cfg.ListOpt("events_creation", default=['compute.instance.create.end',
                                            'floatingip.update.end']),
    cfg.ListOpt("events_deletion", default=['compute.instance.delete.end',
                                            'floatingip.update.end']),
]

rabbit_group = cfg.OptGroup("rabbit", "Rabbit configuration group.")
restnotify_group = cfg.OptGroup("rest", "REST configuration group.")
openstack_group = cfg.OptGroup("openstack", "Openstack configuration group.")


rabbit_opts = [
    cfg.StrOpt('host',
               default='127.0.0.1',
               help="Rabbit host"),
    cfg.IntOpt('port',
               default=5672,
               help="Rabbit port number"),
    cfg.StrOpt('user',
               default='nova',
               help="Rabbit user"),
    cfg.StrOpt('password',
               default='password',
               help="Rabbit password"),
    cfg.StrOpt('watch_queue',
               default='notifications.info',
               help="Rabbit queue"),
]


rest_opts = [
    cfg.StrOpt('host',
               default='127.0.0.1',
               help="Host for REST notifications"),
    cfg.IntOpt('port',
               default=80,
               help="REST port number"),
    cfg.StrOpt('user',
               default='nova',
               help="REST user"),
    cfg.StrOpt('password',
               default='password',
               help="REST password"),
    cfg.StrOpt('url_creation',
               default='/',
               help="Default url for sending notifications "
                    "in event of creation case."),
    cfg.StrOpt('url_deletion',
               default='/',
               help="Default url for sending notifications "
                    "in event of deletion case."),
]


openstack_opts = [
    cfg.StrOpt('auth_url',
               default='http://localhost:5000/v2.0',
               help="Auth url"),
    cfg.StrOpt('user',
               default='user',
               help="Openstack user"),
    cfg.StrOpt('password',
               default='password',
               help="Openstack password"),
    cfg.StrOpt('tenant',
               default='admin',
               help="Openstack tenant"),
]


CONF = cfg.CONF
CONF.register_opts(common_opts)

CONF.register_group(rabbit_group)
CONF.register_group(restnotify_group)
CONF.register_group(openstack_group)

CONF.register_opts(rabbit_opts, rabbit_group)
CONF.register_opts(rest_opts, restnotify_group)
CONF.register_opts(openstack_opts, openstack_group)


def parse_args(argv, default_config_files=None):
    cfg.CONF(args=argv[1:],
             project='oss_framework',
             version=version.version,
             default_config_files=default_config_files)
