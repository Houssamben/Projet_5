import sys
import argparse
import dataikuapi
import requests
import urllib3
import json

from lib.macro_utils import *

# Disable SSL warnings for internal/self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


class PackageUseCaseIndusAPI():
    def __init__(self, design_rd_host, design_rd_user_api_key, project_key, deployer_host, deployer_api_key,
                 api_service_id, automation_node_hosts, automation_api_key_qual, automation_api_key_int,
                 automation_api_key_rd, automation_api_key_pprd, automation_api_key_prd):
        print("[INFO] Start running function PackageUseCaseIndusAPI.__init__")
        print(f"[DEBUG] project_key = {project_key}")
        print(f"[DEBUG] api_service_id = {api_service_id}")

        self.client = dataikuapi.DSSClient(design_rd_host, design_rd_user_api_key, insecure_tls=True)
        self.deployer_client = dataikuapi.DSSClient(deployer_host, deployer_api_key, insecure_tls=True)

        self.api_service_id = api_service_id
        self.project_key = project_key

        # TODO get url from config file
        self.dict_automations = [
            {
                "host": automation_node_hosts['int'],
                "api_key": automation_api_key_int,
                "infra": "INT"
            },
            {
                "host": automation_node_hosts['qual'],
                "api_key": automation_api_key_qual,
                "infra": "QUAL"
            },
            {
                "host": automation_node_hosts['pprod'],
                "api_key": automation_api_key_pprd,
                "infra": "PPRD"
            },
            {
                "host": automation_node_hosts['prd'],
                "api_key": automation_api_key_prd,
                "infra": "PRD"
            },
            {
                "host": automation_node_hosts['rd'],
                "api_key": automation_api_key_rd,
                "infra": "RD"
            }
        ]

        print(f"[DEBUG] number of automation targets = {len(self.dict_automations)}")
        print("[INFO] End running function PackageUseCaseIndusAPI.__init__")

    def run(self, process_callback):
        print("[INFO] Start running function PackageUseCaseIndusAPI.run")
        print(f"[INFO] Start processing project: {self.project_key}")

        print("[INFO] Executing step: fetching project from design node")
        project = self.client.get_project(self.project_key)

        print("[INFO] Executing step: extracting project trigram")
        trigram = extract_project_trigram(self.project_key)
        print(f"[DEBUG] trigram = {trigram}")

        print(f"[INFO] Executing step: fetching API service {self.api_service_id}")
        api_service = project.get_api_service(self.api_service_id)

        # TODO retirer le +1 d'ici pour que la fonction define api version retourne la version d'api défini
        api_version = f"v{define_api_version(api_service) + 1}"
        print(f"[DEBUG] api_version = {api_version}")

        print(f"[INFO] Executing step: iterating over {len(self.dict_automations)} automation targets")
        for automation in self.dict_automations:
            print(f"[INFO] Executing step: processing automation infra = {automation['infra']}")
            print(f"[DEBUG] automation host = {automation['host']}")

            client_automation = dataikuapi.DSSClient(automation["host"], automation["api_key"], insecure_tls=True)

            print("[INFO] Executing step: listing connections on automation node")
            automation_connections = client_automation.list_connections_names(connection_type="all")
            print(f"[DEBUG] total connections on automation node = {len(automation_connections)}")

            connection_name = extract_connection_name(trigram.lower(), automation_connections)
            print(f"[DEBUG] connection_name = {connection_name}")

            api_version_with_stage = f"{api_version} {automation['infra']}"
            print(f"[DEBUG] api_version_with_stage = {api_version_with_stage}")

            settings = api_service.get_settings()
            service_raw_settings = settings.get_raw()

            endpoint_list = settings.endpoints
            sql_endpoints_list = [endpoint.get("id") for endpoint in endpoint_list if
                                  endpoint.get("type") == "SQL_QUERY"]
            print(f"[DEBUG] number of SQL endpoints = {len(sql_endpoints_list)}")

            print("[INFO] Executing step: updating connection for each SQL endpoint")
            for sql_endpoint in sql_endpoints_list:
                print(f"[DEBUG] updating endpoint {sql_endpoint} with connection {connection_name}")
                service_raw_settings = update_connection(service_raw_settings, sql_endpoint, connection_name)
                settings.save()

            # Create a new version
            print(f"[INFO] Executing step: creating API package {api_version_with_stage}")
            api_service.create_package(api_version_with_stage)

            # Publish to API Deployer
            print(f"[INFO] Executing step: publishing API package {api_version_with_stage} to deployer")
            api_service.publish_package(api_version_with_stage)

            print(f"[INFO] Executing step: completed for infra = {automation['infra']}")

        print(f"[INFO] End processing project: {self.project_key}")
        print("[INFO] End running function PackageUseCaseIndusAPI.run")


def run_package_and_publish_use_case_indus_api(design_rd_user_api_key, project_key, deployer_api_key,
                                               api_service_id, automation_api_key_qual, automation_api_key_int,
                                               automation_api_key_rd, automation_api_key_pprd, automation_api_key_prd):
    print("[INFO] Start running function run_package_and_publish_use_case_indus_api")
    print(f"[DEBUG] project_key = {project_key}")
    print(f"[DEBUG] api_service_id = {api_service_id}")

    design_rd_host = "https://ds-studio-0r1.leasingsolutions.echonet"
    deployer_host = "https://ds-deploy.leasingsolutions.echonet"
    automation_node_hosts = {
        "qual": "https://ds-automa-0u0.leasingsolutions.staging.echonet/",
        "int": "https://ds-automa-0t1.leasingsolutions.dev.echonet/",
        "rd": "https://ds-automa-0r1.leasingsolutions.echonet/",
        "pprod": "https://ds-automa-0q0.leasingsolutions.echonet/",
        "prod": "https://ds-automa.leasingsolutions.echonet/"
    }
    print(f"[DEBUG] design_rd_host = {design_rd_host}")
    print(f"[DEBUG] deployer_host = {deployer_host}")
    print(f"[DEBUG] automation_node_hosts = {list(automation_node_hosts.keys())}")

    use_case_indus_api = PackageUseCaseIndusAPI(design_rd_host, design_rd_user_api_key, project_key, deployer_host,
                                                deployer_api_key, api_service_id, automation_node_hosts,
                                                automation_api_key_qual, automation_api_key_int, automation_api_key_rd,
                                                automation_api_key_pprd, automation_api_key_prd)
    use_case_indus_api.run(None)

    print("[INFO] End running function run_package_and_publish_use_case_indus_api")


def build_parser(params):
    """Build argparse parser from a list of (param_name, required) tuples."""
    parser = argparse.ArgumentParser(description="Package and publish use case indus API across all automation nodes")
    for param, required in params:
        parser.add_argument(f"--{param}", required=required)
    return parser


if __name__ == "__main__":
    print("[INFO] Input arguments check")

    # Define expected arguments: (argument name, required)
    params = [
        ("design-rd-user-api-key", True),
        ("deployer-api-key", True),
        ("api-service-id", True),
        ("automation-api-key-qual", True),
        ("automation-api-key-int", True),
        ("automation-api-key-rd", False),   # Optional: RD environment
        ("automation-api-key-pprd", True),
        ("automation-api-key-prd", False),  # Optional: PRD environment
    ]

    parser = build_parser(params)
    args = parser.parse_args()

    print("[INFO] Input arguments check passed")
    print(f"[DEBUG] api_service_id = {args.api_service_id}")

    # Read project key from params.json
    print("[INFO] Executing step: reading project key from params.json")
    with open('params.json', 'r') as file:
        params_data = json.load(file)
        project_key = params_data.get("name")

    if not project_key:
        print("[ERROR] 'name' key not found in params.json")
        sys.exit(1)

    print(f"[DEBUG] project_key = {project_key}")

    print(f"[INFO] Start processing project: {project_key}")
    run_package_and_publish_use_case_indus_api(
        args.design_rd_user_api_key,
        project_key,
        args.deployer_api_key,
        args.api_service_id,
        args.automation_api_key_qual,
        args.automation_api_key_int,
        args.automation_api_key_rd,
        args.automation_api_key_pprd,
        args.automation_api_key_prd
    )
    print(f"[INFO] End processing project: {project_key}")
    print("[INFO] Package and publish use case indus API completed successfully")
