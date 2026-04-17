import argparse
import sys
import dataikuapi
import requests
import urllib3
import json
from lib.macro_utils import extract_project_trigram, extract_connection_name, define_api_version, update_connection

# Disable SSL warnings for internal Dataiku nodes
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


class PackageUseCaseIndusAPI:
    def __init__(self, design_rd_host, design_rd_user_api_key, project_key, deployer_host, deployer_api_key,
                 api_service_id, automation_node_hosts, automation_api_key_qual, automation_api_key_int,
                 automation_api_key_rd, automation_api_key_pprd, automation_api_key_prd):
        """Initialize DSS clients and build the list of automation nodes to package for."""
        print(f"[INFO] Start running function PackageUseCaseIndusAPI.__init__")
        print(f"[DEBUG] project_key = {project_key}, api_service_id = {api_service_id}")

        print(f"[INFO] Executing step: connecting to design RD DSS node")
        self.client = dataikuapi.DSSClient(design_rd_host, design_rd_user_api_key, insecure_tls=True)

        print(f"[INFO] Executing step: connecting to deployer DSS node")
        self.deployer_client = dataikuapi.DSSClient(deployer_host, deployer_api_key, insecure_tls=True)

        self.api_service_id = api_service_id
        self.project_key = project_key

        # Build the list of automation environments to package the API for
        # TODO: move host information into a config file
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
        print(f"[DEBUG] Number of automation environments configured = {len(self.dict_automations)}")
        print(f"[INFO] End running function PackageUseCaseIndusAPI.__init__")

    def run(self, process_callback):
        """Package and publish the API service for every configured automation environment."""
        print(f"[INFO] Start running function PackageUseCaseIndusAPI.run")
        print(f"[INFO] Start processing project: {self.project_key}")

        print(f"[INFO] Executing step: retrieving project from DSS")
        project = self.client.get_project(self.project_key)

        print(f"[INFO] Executing step: extracting project trigram")
        trigram = extract_project_trigram(self.project_key)
        print(f"[DEBUG] trigram = {trigram}")

        print(f"[INFO] Executing step: retrieving API service '{self.api_service_id}'")
        api_service = project.get_api_service(self.api_service_id)

        # Compute the next API version number (current max + 1)
        print(f"[INFO] Executing step: computing next API version number")
        api_version = f"v{define_api_version(api_service) + 1}"
        print(f"[DEBUG] Next api_version = {api_version}")

        # Iterate over each automation environment and create a staged API package
        for automation in self.dict_automations:
            infra = automation['infra']
            print(f"[INFO] Executing step: processing automation environment = {infra}")

            print(f"[INFO] Executing step: connecting to automation node for {infra}")
            client_automation = dataikuapi.DSSClient(automation["host"], automation["api_key"], insecure_tls=True)

            print(f"[INFO] Executing step: listing connections on automation node {infra}")
            automation_connections = client_automation.list_connections_names(connection_type="all")
            print(f"[DEBUG] Number of connections on {infra} = {len(automation_connections)}")

            connection_name = extract_connection_name(trigram.lower(), automation_connections)
            print(f"[DEBUG] Resolved connection_name for {infra} = {connection_name}")

            api_version_with_stage = f"{api_version} {infra}"
            print(f"[DEBUG] api_version_with_stage = {api_version_with_stage}")

            print(f"[INFO] Executing step: retrieving API service settings")
            settings = api_service.get_settings()
            service_raw_settings = settings.get_raw()
            endpoint_list = settings.endpoints

            # Find SQL_QUERY endpoints to remap their connection to the target environment
            sql_endpoints_list = [endpoint.get("id") for endpoint in endpoint_list if
                                  endpoint.get("type") == "SQL_QUERY"]
            print(f"[DEBUG] SQL endpoints found = {sql_endpoints_list}")

            for sql_endpoint in sql_endpoints_list:
                print(f"[INFO] Executing step: remapping connection for SQL endpoint '{sql_endpoint}' on {infra}")
                service_raw_settings = update_connection(service_raw_settings, sql_endpoint, connection_name)
                settings.save()
                print(f"[INFO] Settings saved for endpoint '{sql_endpoint}'")

            # Create a new staged version of the API package
            print(f"[INFO] Executing step: creating API package '{api_version_with_stage}'")
            api_service.create_package(api_version_with_stage)
            print(f"[INFO] API package '{api_version_with_stage}' created")

            # Publish the new package to the API Deployer
            print(f"[INFO] Executing step: publishing API package '{api_version_with_stage}' to deployer")
            api_service.publish_package(api_version_with_stage)
            print(f"[INFO] API package '{api_version_with_stage}' published for environment {infra}")

        print(f"[INFO] End processing project: {self.project_key}")
        print(f"[INFO] End running function PackageUseCaseIndusAPI.run")


def run_package_and_publish_use_case_indus_api(design_rd_user_api_key, project_key, deployer_api_key,
                                               api_service_id, automation_api_key_qual, automation_api_key_int,
                                               automation_api_key_rd, automation_api_key_pprd, automation_api_key_prd):
    """Entry point to instantiate and run the API packaging workflow."""
    print(f"[INFO] Start running function run_package_and_publish_use_case_indus_api")
    print(f"[DEBUG] project_key = {project_key}, api_service_id = {api_service_id}")

    # TODO: move host information into a config file
    design_rd_host = "https://ds-studio-0r1.leasingsolutions.echonet"
    deployer_host = "https://ds-deploy.leasingsolutions.echonet"
    automation_node_hosts = {
        "qual": "https://ds-automa-0u0.leasingsolutions.staging.echonet/",
        "int": "https://ds-automa-0t1.leasingsolutions.dev.echonet/",
        "rd": "https://ds-automa-0r1.leasingsolutions.echonet/",
        "pprod": "https://ds-automa-0q0.leasingsolutions.echonet/",
        "prd": "https://ds-automa.leasingsolutions.echonet/"
    }
    print(f"[DEBUG] design_rd_host = {design_rd_host}")
    print(f"[DEBUG] deployer_host = {deployer_host}")
    print(f"[DEBUG] Automation environments configured: {list(automation_node_hosts.keys())}")

    print(f"[INFO] Executing step: initializing PackageUseCaseIndusAPI")
    use_case_indus_api = PackageUseCaseIndusAPI(
        design_rd_host, design_rd_user_api_key, project_key, deployer_host,
        deployer_api_key, api_service_id, automation_node_hosts,
        automation_api_key_qual, automation_api_key_int, automation_api_key_rd,
        automation_api_key_pprd, automation_api_key_prd
    )

    print(f"[INFO] Executing step: running API packaging workflow")
    use_case_indus_api.run(None)

    print(f"[INFO] End running function run_package_and_publish_use_case_indus_api")


def build_parser(params):
    """Build an argparse parser from a list of (param_name, required) tuples."""
    parser = argparse.ArgumentParser(
        description="Package and publish a Dataiku API service to the deployer for all environments."
    )
    for param, required in params:
        parser.add_argument(f"--{param}", required=required)
    return parser


if __name__ == "__main__":
    print("[INFO] Input arguments check")

    # Define expected CLI arguments — sensitive API keys are required but not logged
    params = [
        ("design-rd-user-api-key", True),
        ("deployer-api-key", True),
        ("api-service-id", True),
        ("automation-api-key-qual", True),
        ("automation-api-key-int", True),
        ("automation-api-key-rd", False),
        ("automation-api-key-pprd", True),
        ("automation-api-key-prd", False),
    ]

    parser = build_parser(params)
    args = parser.parse_args()

    print("[INFO] Input arguments check passed")
    print(f"[DEBUG] api_service_id = {args.api_service_id}")

    # Read project key from params.json (set by the CI pipeline)
    print("[INFO] Executing step: reading project key from params.json")
    try:
        with open('params.json', 'r') as file:
            params_data = json.load(file)
            project_key = params_data.get("name")
    except Exception as e:
        print(f"[ERROR] Failed to read params.json: {e}")
        sys.exit(1)

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
    print("[INFO] Package and publish API use case indus completed successfully")
