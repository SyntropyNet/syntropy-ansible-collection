# Copyright: (c) 2020, Syntropy Network
# MIT License
from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import traceback

SDK_IMP_ERR = None
try:
    from syntropy_sdk import (
        AgentsApi,
        ApiClient,
        AuthApi,
        Configuration,
        ConnectionsApi,
    )
    from syntropy_sdk.exceptions import ApiException, SyntropyError
    from syntropy_sdk.models import (
        V1AgentFilter,
        V1NetworkAgentsSearchRequest,
        V1NetworkAuthApiKeysCreateRequest,
    )
    from syntropy_sdk.utils import (
        MAX_QUERY_FIELD_SIZE,
        BatchedRequest,
        BatchedRequestFilter,
        WithPagination,
        login_with_access_token,
    )
    from syntropynac.configure import configure_network
    from syntropynac.exceptions import ConfigureNetworkError
    from syntropynac.fields import ConfigFields

    HAS_SDK = True
except ImportError:
    HAS_SDK = False
    SDK_IMP_ERR = traceback.format_exc()


class EnvVars:
    API_URL = "SYNTROPY_API_SERVER"
    TOKEN = "SYNTROPY_API_TOKEN"


def get_api_client(api_url=None, api_key=None):
    config = Configuration()
    config.host = api_url if api_url else os.environ.get(EnvVars.API_URL)
    access_token = api_key if api_key else os.environ.get(EnvVars.TOKEN)
    config.api_key["Authorization"] = "Bearer " + login_with_access_token(
        config.host, access_token
    )
    return ApiClient(config)


def api_getter_builder(T):
    def get(api_url=None, api_key=None, client=None):
        return T(get_api_client(api_url, api_key)) if client is None else T(client)

    return get


if HAS_SDK:
    get_auth_api = api_getter_builder(AuthApi)
    get_agents_api = api_getter_builder(AgentsApi)
    get_connections_api = api_getter_builder(ConnectionsApi)
