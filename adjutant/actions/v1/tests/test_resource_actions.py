# Copyright (C) 2015 Catalyst IT Ltd
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

from django.test import TestCase
from django.test.utils import override_settings

import mock

from adjutant.actions.v1.resources import (
    NewDefaultNetworkAction, NewProjectDefaultNetworkAction,
    SetProjectQuotaAction, UpdateProjectQuotasAction)
from adjutant.api.models import Task
from adjutant.common.tests.utils import modify_dict_settings
from adjutant.common.tests.fake_clients import (
    FakeManager, setup_identity_cache, get_fake_neutron, get_fake_novaclient,
    get_fake_cinderclient, setup_neutron_cache, neutron_cache, cinder_cache,
    nova_cache, setup_mock_caches, get_fake_octaviaclient, octavia_cache)


@mock.patch('adjutant.common.user_store.IdentityManager',
            FakeManager)
@mock.patch(
    'adjutant.actions.v1.resources.openstack_clients.get_neutronclient',
    get_fake_neutron)
@mock.patch(
    'adjutant.common.openstack_clients.get_neutronclient',
    get_fake_neutron)
@mock.patch(
    'adjutant.common.openstack_clients.get_novaclient',
    get_fake_novaclient)
@mock.patch(
    'adjutant.common.openstack_clients.get_cinderclient',
    get_fake_cinderclient)
class ProjectSetupActionTests(TestCase):

    def test_network_setup(self):
        """
        Base case, setup a new network , no issues.
        """
        setup_neutron_cache('RegionOne', 'test_project_id')
        task = Task.objects.create(
            ip_address="0.0.0.0",
            keystone_user={
                'roles': ['admin'],
                'project_id': 'test_project_id'})

        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_identity_cache(projects=[project])

        data = {
            'setup_network': True,
            'region': 'RegionOne',
            'project_id': 'test_project_id',
        }

        action = NewDefaultNetworkAction(
            data, task=task, order=1)

        action.pre_approve()
        self.assertEqual(action.valid, True)

        action.post_approve()
        self.assertEqual(action.valid, True)

        self.assertEqual(
            action.action.cache,
            {'network_id': 'net_id_0',
             'port_id': 'port_id_3',
             'router_id': 'router_id_2',
             'subnet_id': 'subnet_id_1'}
        )

        global neutron_cache
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['networks']), 1)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['routers']), 1)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['subnets']), 1)

    def test_network_setup_no_setup(self):
        """
        Told not to setup, should do nothing.
        """
        setup_neutron_cache('RegionOne', 'test_project_id')
        task = Task.objects.create(
            ip_address="0.0.0.0",
            keystone_user={
                'roles': ['admin'],
                'project_id': 'test_project_id'})

        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_identity_cache(projects=[project])

        data = {
            'setup_network': False,
            'region': 'RegionOne',
            'project_id': 'test_project_id',
        }

        action = NewDefaultNetworkAction(
            data, task=task, order=1)

        action.pre_approve()
        self.assertEqual(action.valid, True)

        action.post_approve()
        self.assertEqual(action.valid, True)

        self.assertEqual(action.action.cache, {})

        global neutron_cache
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['networks']), 0)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['routers']), 0)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['subnets']), 0)

    def test_network_setup_fail(self):
        """
        Should fail, but on re_approve will continue where it left off.
        """
        setup_neutron_cache('RegionOne', 'test_project_id')
        global neutron_cache
        task = Task.objects.create(
            ip_address="0.0.0.0",
            keystone_user={
                'roles': ['admin'],
                'project_id': 'test_project_id'})

        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_identity_cache(projects=[project])

        data = {
            'setup_network': True,
            'region': 'RegionOne',
            'project_id': 'test_project_id',
        }

        action = NewDefaultNetworkAction(
            data, task=task, order=1)

        action.pre_approve()
        self.assertEqual(action.valid, True)

        neutron_cache['RegionOne']['test_project_id']['routers'] = []

        try:
            action.post_approve()
            self.fail("Shouldn't get here.")
        except Exception:
            pass

        self.assertEqual(
            action.action.cache,
            {'network_id': 'net_id_0',
             'subnet_id': 'subnet_id_1'}
        )

        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['networks']), 1)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['subnets']), 1)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['routers']), 0)

        neutron_cache['RegionOne']['test_project_id']['routers'] = {}

        action.post_approve()

        self.assertEqual(
            action.action.cache,
            {'network_id': 'net_id_0',
             'port_id': 'port_id_3',
             'router_id': 'router_id_2',
             'subnet_id': 'subnet_id_1'}
        )

        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['networks']), 1)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['routers']), 1)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['subnets']), 1)

    @modify_dict_settings(DEFAULT_ACTION_SETTINGS={
        'operation': 'override',
        'key_list': ['NewDefaultNetworkAction'],
        'value': {'RegionOne': {
            'DNS_NAMESERVERS': ['193.168.1.2', '193.168.1.3'],
            'SUBNET_CIDR': '192.168.1.0/24',
            'network_name': 'somenetwork',
            'public_network': '3cb50f61-5bce-4c03-96e6-8e262e12bb35',
            'router_name': 'somerouter',
            'subnet_name': 'somesubnet'
        }}})
    def test_new_project_network_setup(self):
        """
        Base case, setup network after a new project, no issues.
        """
        setup_neutron_cache('RegionOne', 'test_project_id')
        task = Task.objects.create(
            ip_address="0.0.0.0", keystone_user={'roles': ['admin']})

        data = {
            'setup_network': True,
            'region': 'RegionOne',
        }

        action = NewProjectDefaultNetworkAction(
            data, task=task, order=1)

        action.pre_approve()
        self.assertEqual(action.valid, True)

        # Now we add the project data as this is where the project
        # would be created:
        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_identity_cache(projects=[project])

        task.cache = {'project_id': "test_project_id"}

        action.post_approve()
        self.assertEqual(action.valid, True)

        self.assertEqual(
            action.action.cache,
            {'network_id': 'net_id_0',
             'port_id': 'port_id_3',
             'router_id': 'router_id_2',
             'subnet_id': 'subnet_id_1'}
        )

        global neutron_cache
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['networks']), 1)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['routers']), 1)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['subnets']), 1)

    def test_new_project_network_setup_no_id(self):
        """
        No project id given, should do nothing.
        """
        setup_neutron_cache('RegionOne', 'test_project_id')
        task = Task.objects.create(
            ip_address="0.0.0.0", keystone_user={'roles': ['admin']})

        data = {
            'setup_network': True,
            'region': 'RegionOne',
        }

        action = NewProjectDefaultNetworkAction(
            data, task=task, order=1)

        action.pre_approve()
        self.assertEqual(action.valid, True)

        action.post_approve()
        self.assertEqual(action.valid, False)

        self.assertEqual(action.action.cache, {})

        global neutron_cache
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['networks']), 0)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['routers']), 0)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['subnets']), 0)

    def test_new_project_network_setup_no_setup(self):
        """
        Told not to setup, should do nothing.
        """
        setup_neutron_cache('RegionOne', 'test_project_id')
        task = Task.objects.create(
            ip_address="0.0.0.0", keystone_user={'roles': ['admin']})

        data = {
            'setup_network': False,
            'region': 'RegionOne',
        }

        action = NewProjectDefaultNetworkAction(
            data, task=task, order=1)

        action.pre_approve()
        self.assertEqual(action.valid, True)

        # Now we add the project data as this is where the project
        # would be created:
        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_identity_cache(projects=[project])

        task.cache = {'project_id': "test_project_id"}

        action.post_approve()
        self.assertEqual(action.valid, True)

        self.assertEqual(action.action.cache, {})

        global neutron_cache
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['networks']), 0)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['routers']), 0)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['subnets']), 0)

    def test_new_project_network_setup_fail(self):
        """
        Should fail, but on re_approve will continue where it left off.
        """
        setup_neutron_cache('RegionOne', 'test_project_id')
        global neutron_cache
        task = Task.objects.create(
            ip_address="0.0.0.0", keystone_user={'roles': ['admin']})

        data = {
            'setup_network': True,
            'region': 'RegionOne',
        }

        action = NewProjectDefaultNetworkAction(
            data, task=task, order=1)

        action.pre_approve()
        self.assertEqual(action.valid, True)

        neutron_cache['RegionOne']['test_project_id']['routers'] = []

        # Now we add the project data as this is where the project
        # would be created:
        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_identity_cache(projects=[project])

        task.cache = {'project_id': "test_project_id"}

        try:
            action.post_approve()
            self.fail("Shouldn't get here.")
        except Exception:
            pass

        self.assertEqual(
            action.action.cache,
            {'network_id': 'net_id_0',
             'subnet_id': 'subnet_id_1'}
        )

        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['networks']), 1)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['subnets']), 1)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['routers']), 0)

        neutron_cache['RegionOne']['test_project_id']['routers'] = {}

        action.post_approve()

        self.assertEqual(
            action.action.cache,
            {'network_id': 'net_id_0',
             'port_id': 'port_id_3',
             'router_id': 'router_id_2',
             'subnet_id': 'subnet_id_1'}
        )

        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['networks']), 1)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['routers']), 1)
        self.assertEqual(len(
            neutron_cache['RegionOne']['test_project_id']['subnets']), 1)

    def test_set_quota(self):
        """
        Base case, sets quota on all services of the cached project id.
        """
        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_identity_cache(projects=[project])
        setup_mock_caches('RegionOne', 'test_project_id')

        task = Task.objects.create(
            ip_address="0.0.0.0", keystone_user={'roles': ['admin']})

        task.cache = {'project_id': "test_project_id"}

        action = SetProjectQuotaAction({}, task=task, order=1)

        action.pre_approve()
        self.assertEqual(action.valid, True)

        action.post_approve()
        self.assertEqual(action.valid, True)

        # check the quotas were updated
        # This relies on test_settings heavily.
        cinderquota = cinder_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(cinderquota['gigabytes'], 5000)
        novaquota = nova_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(novaquota['ram'], 65536)
        neutronquota = neutron_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(neutronquota['network'], 3)

        # RegionThree, cinder only
        self.assertFalse('RegionThree' in nova_cache)
        r2_cinderquota = cinder_cache['RegionThree'][
            'test_project_id']['quota']
        self.assertEqual(r2_cinderquota['gigabytes'], 50001)
        self.assertEqual(r2_cinderquota['snapshots'], 600)
        self.assertEqual(r2_cinderquota['volumes'], 200)


@mock.patch(
    'adjutant.common.user_store.IdentityManager',
    FakeManager)
@mock.patch(
    'adjutant.common.openstack_clients.get_neutronclient',
    get_fake_neutron)
@mock.patch(
    'adjutant.common.openstack_clients.get_novaclient',
    get_fake_novaclient)
@mock.patch(
    'adjutant.common.openstack_clients.get_cinderclient',
    get_fake_cinderclient)
@mock.patch(
    'adjutant.common.openstack_clients.get_octaviaclient',
    get_fake_octaviaclient)
class QuotaActionTests(TestCase):

    def test_update_quota(self):
        """
        Sets a new quota on all services of a project in a single region
        """
        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        user = mock.Mock()
        user.id = 'user_id'
        user.name = "test@example.com"
        user.email = "test@example.com"
        user.domain = 'default'
        user.password = "test_password"

        setup_identity_cache(projects=[project], users=[user])
        setup_neutron_cache('RegionOne', 'test_project_id')

        # Test sending to only a single region
        task = Task.objects.create(
            ip_address="0.0.0.0", keystone_user={'roles': ['admin']})

        data = {
            'project_id': 'test_project_id',
            'size': 'medium',
            'regions': ['RegionOne'],
            'user_id': user.id
        }

        action = UpdateProjectQuotasAction(data, task=task, order=1)

        action.pre_approve()
        self.assertEqual(action.valid, True)

        action.post_approve()
        self.assertEqual(action.valid, True)

        # check the quotas were updated
        # This relies on test_settings heavily.
        cinderquota = cinder_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(cinderquota['gigabytes'], 10000)
        novaquota = nova_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(novaquota['ram'], 327680)
        neutronquota = neutron_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(neutronquota['network'], 5)

    def test_update_quota_multi_region(self):
        """
        Sets a new quota on all services of a project in multiple regions
        """
        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        user = mock.Mock()
        user.id = 'user_id'
        user.name = "test@example.com"
        user.email = "test@example.com"
        user.domain = 'default'
        user.password = "test_password"

        setup_identity_cache(projects=[project], users=[user])
        setup_mock_caches('RegionOne', project.id)
        setup_mock_caches('RegionTwo', project.id)

        task = Task.objects.create(
            ip_address="0.0.0.0", keystone_user={'roles': ['admin']})

        data = {
            'project_id': 'test_project_id',
            'size': 'large',
            'domain_id': 'default',
            'regions': ['RegionOne', 'RegionTwo'],
            'user_id': 'user_id'
        }

        action = UpdateProjectQuotasAction(data, task=task, order=1)

        action.pre_approve()
        self.assertEqual(action.valid, True)

        action.post_approve()
        self.assertEqual(action.valid, True)

        # check the quotas were updated
        # This relies on test_settings heavily.
        cinderquota = cinder_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(cinderquota['gigabytes'], 50000)
        novaquota = nova_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(novaquota['ram'], 655360)
        neutronquota = neutron_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(neutronquota['network'], 10)

        cinderquota = cinder_cache['RegionTwo']['test_project_id']['quota']
        self.assertEqual(cinderquota['gigabytes'], 50000)
        novaquota = nova_cache['RegionTwo']['test_project_id']['quota']
        self.assertEqual(novaquota['ram'], 655360)
        neutronquota = neutron_cache['RegionTwo']['test_project_id']['quota']
        self.assertEqual(neutronquota['network'], 10)

    @override_settings(QUOTA_SIZES_ASC=[])
    def test_update_quota_not_in_sizes_asc(self):
        """
        Tests that the quota will still update to a size even if it is not
        placed in QUOTA_SIZES_ASC
        """

        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        user = mock.Mock()
        user.id = 'user_id'
        user.name = "test@example.com"
        user.email = "test@example.com"
        user.domain = 'default'
        user.password = "test_password"

        setup_identity_cache(projects=[project], users=[user])
        setup_mock_caches('RegionOne', project.id)
        setup_mock_caches('RegionTwo', project.id)

        task = Task.objects.create(
            ip_address="0.0.0.0", keystone_user={'roles': ['admin']})

        data = {
            'project_id': 'test_project_id',
            'size': 'large',
            'domain_id': 'default',
            'regions': ['RegionOne', 'RegionTwo'],
        }

        action = UpdateProjectQuotasAction(data, task=task, order=1)

        action.pre_approve()
        self.assertEqual(action.valid, True)

        action.post_approve()
        self.assertEqual(action.valid, True)

        # check the quotas were updated
        # This relies on test_settings heavily.
        cinderquota = cinder_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(cinderquota['gigabytes'], 50000)
        novaquota = nova_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(novaquota['ram'], 655360)
        neutronquota = neutron_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(neutronquota['network'], 10)

        cinderquota = cinder_cache['RegionTwo']['test_project_id']['quota']
        self.assertEqual(cinderquota['gigabytes'], 50000)
        novaquota = nova_cache['RegionTwo']['test_project_id']['quota']
        self.assertEqual(novaquota['ram'], 655360)
        neutronquota = neutron_cache['RegionTwo']['test_project_id']['quota']
        self.assertEqual(neutronquota['network'], 10)

    @modify_dict_settings(QUOTA_SERVICES={
        'operation': 'append',
        'key_list': ['*'],
        'value': 'octavia'
    })
    def test_update_quota_octavia(self):
        """Tests the quota update of the octavia service"""
        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        user = mock.Mock()
        user.id = 'user_id'
        user.name = "test@example.com"
        user.email = "test@example.com"
        user.domain = 'default'
        user.password = "test_password"

        setup_identity_cache(projects=[project], users=[user])
        setup_mock_caches('RegionOne', project.id)

        task = Task.objects.create(
            ip_address="0.0.0.0", keystone_user={'roles': ['admin']})

        data = {
            'project_id': 'test_project_id',
            'size': 'large',
            'domain_id': 'default',
            'regions': ['RegionOne'],
        }

        action = UpdateProjectQuotasAction(data, task=task, order=1)

        action.pre_approve()
        self.assertEqual(action.valid, True)

        action.post_approve()
        self.assertEqual(action.valid, True)

        # check the quotas were updated
        # This relies on test_settings heavily.
        cinderquota = cinder_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(cinderquota['gigabytes'], 50000)
        novaquota = nova_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(novaquota['ram'], 655360)
        neutronquota = neutron_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(neutronquota['network'], 10)
        octaviaquota = octavia_cache['RegionOne']['test_project_id']['quota']
        self.assertEqual(octaviaquota['load_balancer'], 10)

    @modify_dict_settings(QUOTA_SERVICES={
        'operation': 'append',
        'key_list': ['*'],
        'value': 'octavia'
    })
    def test_update_quota_octavia_over_usage(self):
        """When octavia usage is higher than new quota it won't be changed"""
        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        user = mock.Mock()
        user.id = 'user_id'
        user.name = "test@example.com"
        user.email = "test@example.com"
        user.domain = 'default'
        user.password = "test_password"

        setup_identity_cache(projects=[project], users=[user])
        setup_mock_caches('RegionOne', project.id)

        task = Task.objects.create(
            ip_address="0.0.0.0", keystone_user={'roles': ['admin']})

        data = {
            'project_id': 'test_project_id',
            'size': 'small',
            'domain_id': 'default',
            'regions': ['RegionOne'],
        }

        # setup 2 load balancers
        octavia_cache['RegionOne'][project.id]['load_balancer'] = [
            {'id': 'fake_id'},
            {'id': 'fake_id2'}]

        action = UpdateProjectQuotasAction(data, task=task, order=1)

        action.pre_approve()
        self.assertEqual(action.valid, False)

        action.post_approve()
        self.assertEqual(action.valid, False)

        # check the quotas were updated
        # This relies on test_settings heavily.
        octaviaquota = octavia_cache['RegionOne']['test_project_id']['quota']
        # Still set to default
        self.assertEqual(octaviaquota['load_balancer'], 1)
