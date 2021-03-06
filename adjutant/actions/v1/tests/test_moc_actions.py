# Copyright (c) 2019 Kristi Nikolla
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
import yaml
import uuid

from adjutant.api.models import Task
from adjutant.common.tests import fake_clients
from adjutant.common.tests.utils import modify_dict_settings, AdjutantTestCase

from adjutant.actions.v1 import moc_actions


@mock.patch('adjutant.common.user_store.IdentityManager', fake_clients.FakeManager)
class UserActionTests(AdjutantTestCase):
    def test_new_user_existing(self):
        """
        Existing user, valid tenant, no role.
        """
        project = fake_clients.FakeProject(name="test_project")

        user = fake_clients.FakeUser(
            name="test@example.com", password="123", email="test@example.com")
        user_token = uuid.uuid4().hex

        fake_clients.setup_identity_cache(projects=[project], users=[user])

        task = Task.objects.create(
            ip_address="0.0.0.0",
            keystone_user={
                'roles': ['admin', 'project_mod'],
                'project_id': project.id,
                'project_domain_id': 'default',
            })

        data = {
            'email': 'test@example.com',
            'project_id': project.id,
            'roles': ['_member_'],
            'inherited_roles': [],
            'domain_id': 'default',
        }

        action = moc_actions.MocNewUserAction(data, task=task, order=1)

        action.pre_approve()
        self.assertEqual(action.valid, True)

        action.post_approve()
        self.assertEqual(action.valid, True)

        token_data = {'token': user_token}
        with mock.patch(
                'adjutant.common.tests.fake_clients.FakeManager.validate_token',
                return_value={'user': user}
        ):
            action.submit(token_data)
        self.assertEqual(action.valid, True)

        fake_client = fake_clients.FakeManager()
        roles = fake_client._get_roles_as_names(user, project)
        self.assertEqual(roles, ['_member_'])


MAILMAN_SETTINGS = """
MailingListSubscribeAction:
    host: server.example.com
    port: 22
    user: onboarding
    list: kaizen-users
    private_key: /root/.ssh/id_rsa
"""
MAILMAN_SETTINGS = yaml.load(MAILMAN_SETTINGS, Loader=yaml.FullLoader)


@modify_dict_settings(DEFAULT_ACTION_SETTINGS={
        'key_list': ['MailingListSubscribeAction'],
        'operation': 'override',
        'value': MAILMAN_SETTINGS['MailingListSubscribeAction']
    })
class MocTests(AdjutantTestCase):

    def test_mailing_list_subscribe(self):
        task = Task.objects.create(
            ip_address="0.0.0.0",
            keystone_user={'username': 'test@example.com'})
        action = moc_actions.MailingListSubscribeAction({}, task=task,
                                                        order=1)

        action.pre_approve()
        self.assertEqual('pending', action.action.state)

        with mock.patch.object(
                moc_actions.MailingListSubscribeAction,
                '_mailman',
                return_value=['blabla@example.com']) as mailman:
            action.post_approve()
            mailman.assert_has_calls([
                mock.call('/usr/lib/mailman/bin/list_members kaizen-users'),
                mock.call('echo test@example.com | /usr/lib/mailman/bin/add_members -r - kaizen-users')
            ])

        self.assertEqual('complete', action.action.state)

    def test_mailing_list_subscribe_existing(self):
        task = Task.objects.create(
            ip_address="0.0.0.0",
            keystone_user={'username': 'test@example.com'})
        action = moc_actions.MailingListSubscribeAction({}, task=task,
                                                        order=1)

        action.pre_approve()
        self.assertEqual(action.action.state, 'pending')

        with mock.patch.object(
                moc_actions.MailingListSubscribeAction,
                '_mailman',
                return_value=['test@example.com']
        ) as mailman:
            action.post_approve()
            mailman.assert_called_once_with(
                '/usr/lib/mailman/bin/list_members kaizen-users'
            )
            self.assertEqual('complete', action.action.state)

        self.assertEqual('complete', action.action.state)
