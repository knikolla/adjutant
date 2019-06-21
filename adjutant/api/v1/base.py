# Copyright (C) 2019 Catalyst IT Ltd
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

from adjutant.api.v1.views import APIViewWithLogger


# TODO(adriant): Decide what this class does now other than just being a
# namespace for plugin views.
class BaseDelegateAPI(APIViewWithLogger):
    """Base Class for Adjutant's deployer configurable APIs."""
    pass