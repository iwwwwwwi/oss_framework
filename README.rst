=============
OSS Framework
=============

Overview
--------

This application makes possible to handle events based on openstack notifications.
Each supported event parsed and send by supported plugins.

List of events:
 - compute.instance.create.end
 - compute.instance.delete.end
 - floatingip.update.end
 - floatingip.update.end

These events are splited by groups:
 - operations of creation (creation of instance and floating IP),
 - operations of deletion (deletion of instance and dissassociation of IP).

This system is plugable. Each event can be handled by few plugins.
For example, after creation of instance we can send some API call,
email, publish new message for RabbitMQ queue, etc.

List of supported plugins:
 - rest_plugin.RESTNotify (Make a REST call with data from rabbit's queue).

Example of config
-----------------
Default section of config is described by supported events and enabled plugins.
If we want to use few plugins we should split them by common.
For example:
enabled_plugins=rest_plugin.RESTNotify,some_another_plugin.Plugin
Adding of new plugin will be described in Extending of plugins section.

.. code-block:: bash

  [DEFAULT]
  enabled_plugins=rest_plugin.RESTNotify
  log_file=/var/logs/oss.log
  events_creation=compute.instance.create.end,floatingip.update.end
  events_deletion=compute.instance.delete.end,floatingip.update.end

For listening of events we should turn on of notification by adding of lines
in service config file (for example, /etc/nova/nova.conf):

.. code-block:: bash

  notification_driver = messaging
  notification_topics = monitoring

After that we should restart service.
For successfully connection to queue we should configure [rabbit] section.

.. code-block:: bash

  [rabbit]
  host=localhost
  port=5672
  password=passwprd
  user=user
  watch_queue=monitoring.info

Config section for rest_plugin.RESTNotify plugin

.. code-block:: bash

  [rest]
  host=https://some_host
  port=80
  user=user
  password=password
  url_creation=/some_url
  url_deletion=/some_url2

For some of events we should do some extra call to nova, neutron.
We should specify admin credentials for opensack services due to
this reason.

.. code-block:: bash

  [openstack]
  auth_url=http://localhost:5000/v2.0
  user=user
  password=password
  tenant=admin


Usage
-----
.. code-block:: bash

  $ oss_watcher --config-file=../oss.conf
  2015-03-19 18:44:01 INFO (service) Listen queue monitoring.info
  2015-03-19 18:44:01 INFO (service) Handled events of creation: compute.instance.create.endfloatingip.update.end
  2015-03-19 18:44:01 INFO (service) Handled events of deletion: compute.instance.delete.endfloatingip.update.end
  2015-03-19 18:44:01 INFO (service) Plugin `oss_framework.plugins.rest_plugin.RESTNotify`is loaded.
  2015-03-19 18:44:01 INFO (base_connection) Connecting to 172.18.66.110:5672

rest_plugin.RESTNotify plugin
-----------------------------

This plugin make API calls for each enabled event.
For each group of event we can have separated url.
Operation of creation will be hadled by url_creation and
operation of deletion will be handled by url_deletion.
For each of event will be done POST query with prepeared data.

Example of data for plugins
---------------------------
After parsing of events each plugin will take a json

.. code-block:: bash

  {
    "FQDN": "fake.hostname.com",
    "IP": "172.18.66.54",
    "IPType": "Public", // static
    "OS": "Ubuntu", // from image metadata
    "Storage": 80,
    "Ram": 8,
    "CPU": 2,
    "Datacenter": "KDC", //static
    "SecurityDomain": "DQT", //static
    "Owner": "some_owner", //from instance metadata
    "AdditionalUsers": [], //from instance metadata
    "ApplicationName": "Fake name", //from instance metadata
    "EnvironmentCI": "Environment info", //from instance metadata
    "Description":"Description of VM", //from instance metadata
    "CreationDate": "2015-03-19"
  }

Extending of plugins section
----------------------------
For adding of new plugin you should crete new directory in project folder.
For example:

.. code-block:: bash

   > git clone https://github.com/sshturm/oss_framework.git
   > cd oss_framework
   > mkdir oss_framework/plugins/new_plugin
   > touch oss_framework/plugins/new_plugin/__init__.py

Edit __init__.py file and add new hadler for event:

.. code-block:: bash

  > vim oss_framework/plugins/new_plugin/__init__.py

.. code-block:: bash

  import json
  import logging

  from oslo.config import cfg
  from oss_framework.plugins import base


  LOG = logging.getLogger(__name__)
  CONF = cfg.CONF


  class YourPlugin(base.BasePlugin):
      """Plugin for handling of events"""

      def notify(self, node_detail, created):
          """Make some operation after event."""
          # node_detail has a json format and described in section above.
          data = json.dumps(node_detail)
          # Here the main logic of plugin should be implemented.
          # created param is boolean and make possible to separate logic
          # for allocation or release of resource.
          LOG.info("Handled by YourPlugin.")
          LOG.info(node_detail)

For turn on new plugin edit your oss.conf file and change

.. code-block:: bash

  enabled_plugins=rest_plugin.RESTNotify,new_plugin.YourPlugin

Reinstall this service by command

.. code-block:: bash

  > python setup.py install

After that restart oss_watcher service.
Now each event will handled by two plugins.
