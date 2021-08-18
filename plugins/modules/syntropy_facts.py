#!/usr/bin/python
# -*- coding: utf-8 -*-

# (C) Copyright 2020 Syntropy Network
# MIT License


from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
---
module: syntropy_facts
version_added: "0.1.0"
short_description: Gathers Syntropy Stack Facts
description:
    - This module gathers facts about providers, api-keys, connections, endpoints.
author:
    - Andrius Mikonis (@foxis)
requirements: ["syntropy-sdk"]
options:
    api_url:
        description:
            - URL Of the Platform API.
            - This parameter is required if SYNTROPY_API_SERVER environment variable is not set.
        required: false
        default: null
        type: str
    api_token:
        description:
            - API Authorization token string.
            - This parameter is required if SYNTROPY_API_TOKEN environment variable is not set.
        required: false
        default: null
        type: str
    endpoint_name: 
        description: specifies endpoint name to filter facts by.
        required: false
        type: str
    endpoint_tags:
        description: specifies endpoint tag to filter facts by.
        required: false
        elements: str
        type: list
    gather_subset:
        description: A subset of facts to gather.
        choices: ['providers', 'api_keys', 'endpoints', 'connections']
        required: false
        default: ['providers', 'connections']
        elements: str
        type: list
    skip: 
        description: Skip N items in the fact list.
        type: int
        default: 0
    take:
        description: Take N items in from the fact list.
        type: int
        default: 42
"""  # NOQA

EXAMPLES = """
-   name: Retrieve all networks and all connections
    syntropy_facts:
    register: facts_output
-   name: Retrieve api-keys
    syntropy_facts:
        gather_subset: ['api_keys']
-   name: Retrieve topology
    syntropy_facts:
        endpoint_tags: ['dns', 'iot']
        gather_subset: ['endpoints']
    register: facts_subset_output
"""  # NOQA

RETURN = """
error:
    description: Error message upon unsuccessful login.
    type: str
    returned: always
    sample: 'Authorization failure'
facts:
    description:
        - Retrieved facts for various objects specified in gather_subset.
        - Please refer to the API documentation for more information on the returned facts.
    type: complex
    returned: always
    contains:
        providers:
            description: A list of endpoint providers.
            type: list
            elements: dict
            returned: When providers is present in gather_subset.
        api_keys:
            description: A list of API Keys.
            type: list
            elements: dict
            returned: When api_keys is present in gather_subset.
        endpoints:
            description: A list of available endpoints.
            type: list
            elements: dict
            returned: When endpoints is present in gather_subset.
        connections:
            description: A list of configured connections.
            type: list
            elements: dict
            returned: When connections is present in gather_subset.
"""

import traceback
from collections import defaultdict

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

try:
    from ansible_collections.syntropynet.syntropy.plugins.module_utils.syntropy import (
        HAS_SDK,
        MAX_QUERY_FIELD_SIZE,
        SDK_IMP_ERR,
        ApiException,
        BatchedRequest,
        get_api_keys_api,
        get_platform_api,
    )
except ImportError:
    pass


def main():
    """
    Main entry point for module execution
    :returns: ansible_facts
    """
    argument_spec = {
        "api_url": dict(type="str", default=None),
        "api_token": dict(type="str", default=None, no_log=True),
        "endpoint_name": dict(type="str", default=None),
        "endpoint_tags": dict(type="list", elements="str", default=None),
        "gather_subset": dict(
            default=["providers", "connections"],
            type="list",
            elements="str",
            choices=[
                "providers",
                "api_keys",
                "endpoints",
                "connections",
            ],
        ),
        "skip": dict(type="int", default=0),
        "take": dict(type="int", default=42),
    }

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    result = {
        "error": "",
        "facts": {},
    }

    if not HAS_SDK:
        result["error"] = SDK_IMP_ERR
        module.fail_json(
            msg=missing_required_lib("syntropy-sdk"), exception=SDK_IMP_ERR
        )

    filters = []
    if module.params["endpoint_name"]:
        filters.append(f"id|name:'{module.params['endpoint_name']}'")
    if module.params["endpoint_tags"]:
        escaped_tag_names = (f"'{i}'" for i in module.params["endpoint_tags"])
        filters.append(f"tags_names[]:{';'.join(i for i in escaped_tag_names)}")
    agents_filter = ",".join(filters) if filters else None

    try:
        api = get_platform_api(
            api_url=module.params["api_url"], api_key=module.params["api_token"]
        )
        keys_api = get_api_keys_api(client=api.api_client)

        subset = (
            module.params["gather_subset"]
            if isinstance(module.params["gather_subset"], list)
            else [module.params["gather_subset"]]
        )
        for fact in subset:
            if fact == "providers":
                result["facts"][fact] = api.platform_agent_provider_index(
                    skip=module.params["skip"], take=module.params["take"]
                )
            elif fact == "api_keys":
                result["facts"][fact] = [
                    key.to_dict()
                    for key in keys_api.get_api_key(
                        skip=module.params["skip"], take=module.params["take"]
                    ).data
                ]
            elif fact == "connections":
                connections = api.platform_connection_index(
                    skip=module.params["skip"],
                    take=module.params["take"],
                )["data"]
                ids = [connection["agent_connection_id"] for connection in connections]
                connections_services = BatchedRequest(
                    api.platform_connection_service_show,
                    max_payload_size=MAX_QUERY_FIELD_SIZE,
                )(ids)["data"]
                connection_services = {
                    connection["agent_connection_id"]: connection
                    for connection in connections_services
                }
                result["facts"][fact] = [
                    {
                        **connection,
                        "agent_connection_services": connection_services[
                            connection["agent_connection_id"]
                        ],
                    }
                    for connection in connections
                ]
            elif fact == "endpoints":
                agents = api.platform_agent_index(
                    filter=agents_filter,
                    skip=module.params["skip"],
                    take=module.params["take"],
                )["data"]
                ids = [agent["agent_id"] for agent in agents]
                if not ids:
                    continue
                agents_services = BatchedRequest(
                    api.platform_agent_service_index,
                    max_payload_size=MAX_QUERY_FIELD_SIZE,
                )(ids)["data"]
                agent_services = defaultdict(list)
                for agent in agents_services:
                    agent_services[agent["agent_id"]].append(agent)
                result["facts"][fact] = [
                    {
                        **agent,
                        "agent_services": agent_services.get(agent["agent_id"], []),
                    }
                    for agent in agents
                ]
    except ApiException:
        result["error"] = "Failure"
        module.fail_json(
            msg="Syntropy API call resulted in an error",
            exception=traceback.format_exc(),
        )
    finally:
        del api.api_client

    module.exit_json(**result)


if __name__ == "__main__":
    main()
