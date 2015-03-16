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
import requests
from requests import auth as req_auth

from oslo.config import cfg
from oss_framework.plugins import base


LOG = logging.getLogger(__name__)
CONF = cfg.CONF
DATA = """
<execution-context  xmlns="http://www.vmware.com/vco">
<parameters>
<parameter name="nodeDetails" type="string">
<string>%(node_detail)s</string>
</parameter>
</parameters>
</execution-context>"""


class RESTNotify(base.BasePlugin):
    """Plugin for sending of instance data via REST API."""
    def __init__(self, *args, **kwargs):
        super(RESTNotify, self).__init__(*args, **kwargs)
        self.host, self.port = CONF.rest.host, CONF.rest.port
        self.user, self.password = CONF.rest.user, CONF.rest.password

    def notify(self, node_detail, created):
        """Make API call with event's info."""
        url = CONF.rest.url_creation if created else CONF.rest.url_deletion
        headers = {'Content-Type': 'application/xml'}
        data = DATA % {'node_detail': json.dumps(node_detail)}
        data = data.replace('\n', '')
        url = ':'.join((self.host, str(self.port))) + url
        _auth = req_auth.HTTPBasicAuth(self.user, self.password)
        LOG.info("\n POST request\n URL: %s,\n DATA: '%s'\n" % (url, data))
        try:
            r = requests.post(url, auth=_auth, data=data, headers=headers,
                              verify=False)
            LOG.info(r.status_code)
            LOG.info(r.text)
        except Exception as e:
            LOG.error(e.message)
