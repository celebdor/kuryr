# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import abc
import asyncio
import copy
import uuid

import ddt
from mox3 import mox
from oslo_serialization import jsonutils
import requests
import six

from kuryr.common import config
from kuryr.common import constants
from kuryr.raven import raven
from kuryr.raven import watchers
from kuryr.tests.unit import base
from kuryr import utils


class TestK8sAPIWatchers(base.TestKuryrBase):
    """The unit tests for K8sAPIWatcher interface.

    This test checks if k8sApiWatcher works as it's intended. In this class,
    subclasses of K8sAPIWatcher are instantiated but they will not be
    instantiated in the real use cases. These instantiations are considered
    as a sort of the type checking.
    """
    def test_k8s_api_watcher(self):
        """A  watcher implemented K8sAPIWatcher can be instantiated."""
        class SomeWatcher(watchers.K8sAPIWatcher):
            WATCH_ENDPOINT = '/'

            def translate(self, deserialized_json):
                pass
        SomeWatcher()

    def test_k8s_api_watcher_watch_endpoind(self):
        """A watcher without ``WATCH_ENDPOINT`` can't be instantiated."""
        class SomeWatcherWithoutWatchEndpoint(watchers.K8sAPIWatcher):
            def translate(self, deserialized_json):
                pass
        self.assertRaises(TypeError, SomeWatcherWithoutWatchEndpoint)

    def test_k8s_api_watcher_translate(self):
        """A watcher without ``translate`` can't be instantiated."""
        class SomeWatcherWithoutTranslate(watchers.K8sAPIWatcher):
            WATCH_ENDPOINT = '/'
        self.assertRaises(TypeError, SomeWatcherWithoutTranslate)


@ddt.ddt
class TestWatchers(base.TestKuryrBase):
    """The unit tests for the watchers.

    This tests checks the watchers conform to the requirements, register
    appropriately. In this class, the watchers are instantiated but they
    will not be instantiated in the real use cases. These instantiations
    are considered as a sort of the type checking.
    """
    @ddt.data(watchers.K8sPodsWatcher, watchers.K8sServicesWatcher)
    def test_watchers(self, Watcher):
        """Every watcher has ``WATCH_ENDPOINT`` and ``translate``."""
        self.assertIsNotNone(Watcher.WATCH_ENDPOINT)
        self.assertTrue(callable(Watcher.translate))
        Watcher()

    def test_register_watchers(self):
        """``register_watchers`` injects ``WATCH_ENDPOINT`` and ``translate``.

        ``register_watchers`` should inject ``WATCH_ENDPOINT`` attribute (or
        property) and ``translate`` method of the given class into the class
        which is the target of it.
        """
        class DoNothingWatcher(object):
            WATCH_ENDPOINT = '/watch_me'

            def translate(self, deserialized_json):
                pass
        DoNothingWatcher()

        @raven.register_watchers(DoNothingWatcher)
        class Foo(object):
            pass
        Foo()

        self.assertIsNotNone(Foo.WATCH_ENDPOINTS_AND_CALLBACKS)
        self.assertEqual(1, len(Foo.WATCH_ENDPOINTS_AND_CALLBACKS))
        self.assertEqual(DoNothingWatcher.translate,
                         Foo.WATCH_ENDPOINTS_AND_CALLBACKS[
                             DoNothingWatcher.WATCH_ENDPOINT])


class _FakeRaven(raven.Raven):
    def _ensure_networking_base(self):
        self._default_sg = str(uuid.uuid4())
        self._network = {
            'id': str(uuid.uuid4()),
            'name': raven.HARDCODED_NET_NAME,
        }
        subnet_cidr = config.CONF.k8s.cluster_subnet
        fake_subnet = base.TestKuryrBase._get_fake_v4_subnet(
            self._network['id'],
            name=raven.HARDCODED_NET_NAME + '-' + subnet_cidr,
            subnet_v4_id=uuid.uuid4())
        self._subnet = fake_subnet['subnet']

        self._service_network = {
            'id': str(uuid.uuid4()),
            'name': raven.HARDCODED_NET_NAME + '-service'
        }
        service_subnet_cidr = config.CONF.k8s.cluster_service_subnet
        fake_service_subnet = base.TestKuryrBase._get_fake_v4_subnet(
            self._network['id'],
            name=raven.HARDCODED_NET_NAME + '-' + service_subnet_cidr,
            subnet_v4_id=uuid.uuid4())
        self._service_subnet = fake_service_subnet['subnet']

        self._router = {
            "router": {
                "status": "ACTIVE",
                "name": "fake_router",
                "admin_state_up": True,
                "tenant_id": str(uuid.uuid4()),
                "distributed": False,
                "routes": [],
                "ha": False,
                "id": str(uuid.uuid4()),
            },
        }
        self._subnetpool = {'id': str(uuid.uuid4())}


class _FakeSuccessResponse(object):
    status_code = 200
    content = ""


@six.add_metaclass(abc.ABCMeta)
class TestK8sWatchersBase(base.TestKuryrBase):
    """The base class for the unit tests of the K8s watcher classes.

    This class has the common fake data and utility methods for each watcher
    test.
    """
    fake_pod_object = {
        "kind": "Pod",
        "apiVersion": "v1",
        "metadata": {
            "name": "frontend-qr8d6",
            "generateName": "frontend-",
            "namespace": "default",
            "selfLink": "/api/v1/namespaces/default/pods/frontend-qr8d6",  # noqa
            "uid": "8e174673-e03f-11e5-8c79-42010af00003",
            "resourceVersion": "107227",
            "creationTimestamp": "2016-03-02T06:25:27Z",
            "labels": {
                "app": "guestbook",
                "tier": "frontend",
            },
            "annotations": {
                "kubernetes.io/created-by": {
                    "kind": "SerializedReference",
                    "apiVersion": "v1",
                    "reference": {
                        "kind": "ReplicationController",
                        "namespace": "default",
                        "name": "frontend",
                        "uid": "8e1657d9-e03f-11e5-8c79-42010af00003",
                        "apiVersion": "v1",
                        "resourceVersion": "107226",
                    },
                },
            },
        },
    }

    fake_namespace_object = {
        "kind": "Namespace",
        "apiVersion": "v1",
        "metadata": {
            "name": "test",
            "selfLink": "/api/v1/namespaces/test",
            "uid": "f094ea6b-06c2-11e6-8128-42010af00003",
            "resourceVersion": "497821",
            "creationTimestamp": "2016-04-20T06:41:41Z",
            "annotations": {}
        },
        "spec": {
            "finalizers": [
                "kubernetes"
            ]
        },
        "status": {
            "phase": "Active"
        }
    }

    @abc.abstractproperty
    def TEST_WATCHER(self):
        """The watcher class to be tested.

        This is defined as the abstract property and the sub classes derived
        from this class MUST define this class attribute. This class is used
        ``setUp`` method to instantiate the fake Raven instance.
        """

    def setUp(self):
        """Sets up the fake Raven instance registering WATCHER to it.

        This method instantiates the Raven isntance with the watcher class for
        the test registered, holds the translate method of the watcher binding
        it to the fake Raven instance and sets up the cleanup processes. The
        fake Raven instance and the translate method of the watcher class
        specified in ``TEST_WATCHER`` are accessible by ``self.fake_raven``
        and ``self.translate`` for each other.
        """
        super(TestK8sWatchersBase, self).setUp()
        FakeRaven = raven.register_watchers(
            self.TEST_WATCHER)(_FakeRaven)
        self.fake_raven = FakeRaven()
        self.fake_raven._ensure_networking_base()
        self.translate = self.TEST_WATCHER.translate.__get__(
            self.fake_raven, FakeRaven)
        self.addCleanup(self.fake_raven.stop)


class TestK8sNamespaceWatcher(TestK8sWatchersBase):
    """The unit test for the translate method of K8sNamespaceWatcher. """
    TEST_WATCHER = watchers.K8sNamespaceWatcher

    def test_translate_added_create_networks(self):

        # Set the input fake data event
        fake_namespace_added_event = {
            "type": "ADDED",
            "object": self.fake_namespace_object,
        }

        # Return no networks and create a new one
        metadata = fake_namespace_added_event['object']['metadata']
        fake_cluster_network_id = str(uuid.uuid4())

        self.mox.StubOutWithMock(self.fake_raven.neutron, 'list_networks')
        self.mox.StubOutWithMock(self.fake_raven.neutron, 'create_network')
        self.fake_raven.neutron.list_networks(
            name=metadata['name']).AndReturn(
                    {'networks': []})
        fake_cluster_network_req = {
            'network': {
                'name': metadata['name']
            }
        }
        namespace = metadata['name']
        fake_cluster_network_res = {
            'network': {
                'name': namespace,
                'subnets': [],
                'admin_state_up': False,
                'shared': False,
                'status': 'ACTIVE',
                'tenant_id': str(uuid.uuid4()),
                'id': fake_cluster_network_id
            }
        }
        self.fake_raven.neutron.create_network(
            fake_cluster_network_req).AndReturn(
                fake_cluster_network_res)

        # Return no subnets and create a new one
        self.mox.StubOutWithMock(self.fake_raven.neutron, 'list_subnets')
        self.mox.StubOutWithMock(self.fake_raven.neutron, 'create_subnet')

        fake_cluster_subnet_name = utils.get_subnet_name(namespace)
        self.fake_raven.neutron.list_subnets(
                name=fake_cluster_subnet_name).AndReturn({'subnets': []})
        fake_cluster_subnet_id = str(uuid.uuid4())
        fake_cluster_subnet_req = {
            'subnet': {
                'name': fake_cluster_subnet_name,
                'network_id': fake_cluster_network_id,
                'ip_version': 4,
                'subnetpool_id': self.fake_raven._subnetpool['id']
            }
        }
        fake_cluster_subnet_res = copy.deepcopy(
            fake_cluster_subnet_req)

        fake_cluster_subnet_res['subnet']['id'] = fake_cluster_subnet_id
        fake_cluster_subnet_res['subnet']['cidr'] = '192.168.2.0/24'
        fake_cluster_subnet_res['subnet']['enable_dhcp'] = True
        self.fake_raven._router['id'] = str(uuid.uuid4())
        self.fake_raven.neutron.create_subnet(
            fake_cluster_subnet_req).AndReturn(
                fake_cluster_subnet_res)

        # Return no port and create a new one
        self.mox.StubOutWithMock(self.fake_raven.neutron, 'list_ports')
        self.mox.StubOutWithMock(self.fake_raven.neutron,
                                 'add_interface_router')

        self.fake_raven.neutron.list_ports(
                device_owner='network:router_interface',
                device_id=self.fake_raven._router['id'],
                network_id=fake_cluster_network_id).AndReturn({'ports': []})
        self.fake_raven.neutron.add_interface_router(
                self.fake_raven._router['id'],
                {'subnet_id': fake_cluster_subnet_id}).AndReturn(None)

        # Mock the patch call
        self.mox.StubOutWithMock(self.fake_raven, 'delegate')
        fake_patch_response_future = asyncio.Future(
            loop=self.fake_raven._event_loop)
        fake_patch_response_future.set_result(
            _FakeSuccessResponse())

        self.fake_raven.delegate(
            requests.patch,
            constants.K8S_API_ENDPOINT_BASE + metadata['selfLink'],
            data=mox.IgnoreArg(),
            headers=mox.IgnoreArg()).AndReturn(fake_patch_response_future)

        self.mox.ReplayAll()
        self.fake_raven._event_loop.run_until_complete(
            self.translate(fake_namespace_added_event))

    def test_translate_added_networks_already_exist(self):

        # Set the input fake data event
        fake_namespace_added_event = {
            "type": "ADDED",
            "object": self.fake_namespace_object,
        }
        annotations = {
            constants.K8S_ANNOTATION_SUBNET_KEY:
                jsonutils.dumps('{foo: bar}')
        }

        metadata = fake_namespace_added_event['object']['metadata']
        metadata['annotations'] = annotations
        # Prepare the mock response of the neutron network that this
        # pod belongs to
        self.mox.StubOutWithMock(self.fake_raven.neutron, 'list_networks')

        fake_cluster_network_id = str(uuid.uuid4())
        namespace = metadata['name']
        fake_cluster_network_response = {
            'networks': [{
                'name': namespace,
                'subnets': [],
                'admin_state_up': False,
                'shared': False,
                'status': 'ACTIVE',
                'tenant_id': str(uuid.uuid4()),
                'id': fake_cluster_network_id}
            ],
        }
        self.fake_raven.neutron.list_networks(
            name=namespace).AndReturn(
                fake_cluster_network_response)

        # Prepare the mock response of the neutron subnet that this
        # pod belongs to
        self.mox.StubOutWithMock(self.fake_raven.neutron, 'list_subnets')

        fake_cluster_subnet_id = str(uuid.uuid4())
        fake_cluster_subnet_name = utils.get_subnet_name(namespace)
        fake_cluster_subnet_response = {
            'subnets': [{
                'id': fake_cluster_subnet_id,
                'name': fake_cluster_subnet_name,
                'network_id': fake_cluster_network_id,
                'enable_dhcp': False,
                'cidr': '192.168.2.0/24'}
            ],
        }
        self.fake_raven.neutron.list_subnets(
            name=fake_cluster_subnet_name).AndReturn(
                fake_cluster_subnet_response)

        # Fake router id
        self.fake_raven._router['id'] = str(uuid.uuid4())

        # Fake port attached to the router
        self.mox.StubOutWithMock(self.fake_raven.neutron, 'list_ports')
        port_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        fake_namespace_port = {
            "network_id": fake_cluster_network_id,
            "tenant_id": tenant_id,
            "device_owner": "network:router_interface",
            "mac_address": "fa:16:3e:20:57:c3",
            "fixed_ips": [{
                'subnet_id': fake_cluster_subnet_id,
                'ip_address': '10.0.0.2',
            }],
            "id": port_id,
            "device_id": self.fake_raven._router['id'],
        }
        self.fake_raven.neutron.list_ports(
                device_owner='network:router_interface',
                device_id=self.fake_raven._router['id'],
                network_id=fake_cluster_network_id).AndReturn(
                        {'ports': [fake_namespace_port]})
        self.mox.StubOutWithMock(self.fake_raven, 'delegate')

        # Mock the patch call
        fake_patch_response_future = asyncio.Future(
            loop=self.fake_raven._event_loop)
        fake_patch_response_future.set_result(
            _FakeSuccessResponse())

        self.fake_raven.delegate(
            requests.patch,
            constants.K8S_API_ENDPOINT_BASE + metadata['selfLink'],
            data=mox.IgnoreArg(),
            headers=mox.IgnoreArg()).AndReturn(fake_patch_response_future)

        self.mox.ReplayAll()
        self.fake_raven._event_loop.run_until_complete(
            self.translate(fake_namespace_added_event))

    def test_translate_added_delete_network(self):

        # Set the input fake data event
        fake_ns_del_event = {
            "type": "DELETED",
            "object": self.fake_namespace_object,
        }

        # Create the network and the subnet object and attach
        # then into the event.
        metadata = fake_ns_del_event['object']['metadata']
        fake_cluster_network_id = str(uuid.uuid4())
        namespace = metadata['name']
        namespace_network = {
            'name': namespace,
            'subnets': [],
            'admin_state_up': False,
            'shared': False,
            'status': 'ACTIVE',
            'tenant_id': str(uuid.uuid4()),
            'id': fake_cluster_network_id
        }

        fake_cluster_subnet_id = str(uuid.uuid4())
        fake_cluster_subnet_name = utils.get_subnet_name(namespace)
        namespace_subnet = {
            'id': fake_cluster_subnet_id,
            'name': fake_cluster_subnet_name,
            'network_id': fake_cluster_network_id,
            'ip_version': 4,
            'subnetpool_id': self.fake_raven._subnetpool['id'],
            'cidr': '192.168.2.0/24',
            'enable_dhcp': True
        }
        annotations = {
            constants.K8S_ANNOTATION_NETWORK_KEY:
                jsonutils.dumps(namespace_network),
            constants.K8S_ANNOTATION_SUBNET_KEY:
                jsonutils.dumps(namespace_subnet)
        }
        metadata['annotations'] = annotations

        # Delete network
        self.fake_raven._router['id'] = str(uuid.uuid4())
        self.mox.StubOutWithMock(self.fake_raven.neutron,
                                 'remove_interface_router')
        self.fake_raven.neutron.remove_interface_router(
            self.fake_raven._router['id'],
            {'subnet_id': fake_cluster_subnet_id}).AndReturn(None)
        self.mox.StubOutWithMock(self.fake_raven.neutron,
                                 'delete_network')
        self.fake_raven.neutron.delete_network(
            fake_cluster_network_id)

        self.mox.ReplayAll()
        self.fake_raven._event_loop.run_until_complete(
            self.translate(fake_ns_del_event))


class TestK8sPodsWatcher(TestK8sWatchersBase):
    """The unit test for the translate method of TestK8sPodsWatcher.

    The following tests validate if translate method works appropriately.
    """
    TEST_WATCHER = watchers.K8sPodsWatcher

    def test_translate_added(self):
        """Tests if K8sServicesWatcher.translate works as intended."""

        # Set the input fake data event
        fake_pod_added_event = {
            "type": "ADDED",
            "object": self.fake_pod_object,
        }
        fake_port_id = str(uuid.uuid4())
        fake_port = self._get_fake_port(
            fake_pod_added_event['object']['metadata']['name'],
            self.fake_raven._network['id'],
            fake_port_id)['port']
        fake_port_future = asyncio.Future(loop=self.fake_raven._event_loop)
        fake_port_future.set_result({'port': fake_port})
        metadata = fake_pod_added_event['object']['metadata']

        # Prepare the mock response of the neutron network that this
        # pod belongs to
        self.mox.StubOutWithMock(self.fake_raven.neutron, 'list_networks')
        fake_cluster_network_id = str(uuid.uuid4())
        namespace = metadata['namespace']
        fake_cluster_network_response = {
            'networks': [{
                'name': namespace,
                'subnets': [],
                'admin_state_up': False,
                'shared': False,
                'status': 'ACTIVE',
                'tenant_id': str(uuid.uuid4()),
                'id': fake_cluster_network_id}
            ],
        }
        self.fake_raven.neutron.list_networks(
            name=metadata['namespace']).AndReturn(
                fake_cluster_network_response)

        # Prepare the mock response of the neutron subnet that this
        # pod belongs to
        self.mox.StubOutWithMock(self.fake_raven.neutron, 'list_subnets')

        fake_cluster_subnet_id = str(uuid.uuid4())
        fake_cluster_subnet_name = utils.get_subnet_name(namespace)
        fake_cluster_subnet_response = {
            'subnets': [{
                'id': fake_cluster_subnet_id,
                'name': fake_cluster_subnet_name,
                'network_id': fake_cluster_network_id,
                'enable_dhcp': False,
                'cidr': '192.168.2.0/24'}
            ],
        }
        namespace = metadata['namespace']
        fake_cluster_subnet_name = utils.get_subnet_name(namespace)
        self.fake_raven.neutron.list_subnets(
            name=fake_cluster_subnet_name).AndReturn(
                fake_cluster_subnet_response)

        new_port = {
            'name': metadata.get('name', ''),
            'network_id': fake_cluster_network_id,
            'admin_state_up': True,
            'device_owner': constants.DEVICE_OWNER,
            'fixed_ips': [{'subnet_id': fake_cluster_subnet_id}],
            'security_groups': [self.fake_raven._default_sg],
        }
        self.mox.StubOutWithMock(self.fake_raven, 'delegate')
        self.fake_raven.delegate(
            mox.IsA(self.fake_raven.neutron.create_port),
            {'port': new_port}).AndReturn(fake_port_future)
        path = metadata.get('selfLink', '')
        annotations = copy.deepcopy(metadata['annotations'])
        metadata = {}
        metadata.update({'annotations': annotations})
        annotations.update(
            {constants.K8S_ANNOTATION_PORT_KEY: jsonutils.dumps(fake_port)})
        annotations.update(
            {constants.K8S_ANNOTATION_SUBNET_KEY: jsonutils.dumps(
                fake_cluster_subnet_response['subnets'][0])})
        fake_pod_update_data = {
            "kind": "Pod",
            "apiVersion": "v1",
            "metadata": metadata,
        }
        headers = {
            'Content-Type': 'application/merge-patch+json',
            'Accept': 'application/json',
        }

        fake_patch_response = _FakeSuccessResponse()
        fake_patch_response_future = asyncio.Future(
            loop=self.fake_raven._event_loop)
        fake_patch_response_future.set_result(fake_patch_response)
        self.fake_raven.delegate(
            requests.patch, constants.K8S_API_ENDPOINT_BASE + path,
            data=jsonutils.dumps(fake_pod_update_data),
            headers=headers).AndReturn(fake_patch_response_future)
        self.mox.ReplayAll()
        self.fake_raven._event_loop.run_until_complete(
            self.translate(fake_pod_added_event))

    def test_translate_deleted(self):
        """Tests DELETED events for watcher.

        Tests if K8sServicesWatcher.translate works as intended for DELETED.
        """
        fake_pod_deleted_event = {
            "type": "DELETED",
            "object": self.fake_pod_object,
        }
        fake_network_id = self.fake_raven._network['id']
        fake_port_id = str(uuid.uuid4())
        fake_port = self._get_fake_port(
            fake_pod_deleted_event['object']['metadata']['name'],
            fake_network_id,
            fake_port_id)['port']
        metadata = fake_pod_deleted_event['object']['metadata']
        annotations = metadata['annotations']
        annotations.update(
            {constants.K8S_ANNOTATION_PORT_KEY: jsonutils.dumps(fake_port)})
        self.mox.StubOutWithMock(self.fake_raven, 'delegate')
        none_future = asyncio.Future(loop=self.fake_raven._event_loop)
        none_future.set_result(None)
        self.fake_raven.delegate(
            mox.IsA(self.fake_raven.neutron.delete_port),
            fake_port_id).AndReturn(none_future)
        self.mox.ReplayAll()
        self.fake_raven._event_loop.run_until_complete(
            self.translate(fake_pod_deleted_event))