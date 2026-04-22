import argparse
import sys
import dataikuapi
import requests
import urllib3
import json
from lib.macro_utils import define_api_version, create_or_update_deployment

# Disable SSL warnings for internal Dataiku nodes
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


class UseCaseIndusAPIDeployer():
    def __init__(self, design_rd_host, design_rd_user_api_key, project_key, deployer_host, deployer_api_key,
                 api_service_id, infra_id, api_version):
        """Initialize DSS clients and store deployment parameters."""
        print(f"[INFO] Starting UseCaseIndusAPIDeployer initialization")
        print(f"[DEBUG] project_key = {project_key}, api_service_id = {api_service_id}, infra_id = {infra_id}")

        print(f"[INFO] Executing step: connecting to design RD DSS node")
        self.client = dataikuapi.DSSClient(design_rd_host, design_rd_user_api_key, insecure_tls=True)

        print(f"[INFO] Executing step: connecting to deployer DSS node")
        self.deployer_client = dataikuapi.DSSClient(deployer_host, deployer_api_key, insecure_tls=True)

        self.project_key = project_key
        self.api_service_id = api_service_id
        self.infra_id = infra_id
        self.api_version = api_version
 
        print(f"[DEBUG] api_version (input) = '{self.api_version}' (empty means use latest)")
        print(f"[INFO] End UseCaseIndusAPIDeployer initialization")

    def run(self, process_callback):
        """Resolve the API version to deploy and create or update the deployment."""
        print(f"[INFO] Start running function UseCaseIndusAPIDeployer RUN")
        print(f"[INFO] Start processing project: {self.project_key}")

        print(f"[INFO] Executing step: retrieving project from design RD DSS")
        project = self.client.get_project(self.project_key)

        print(f"[INFO] Executing step: retrieving API service '{self.api_service_id}'")
        api_service = project.get_api_service(self.api_service_id)

        print(f"[INFO] Executing step: retrieving infra settings for '{self.infra_id}'")
        api_deployer = self.deployer_client.get_apideployer()
        infra_settings = api_deployer.get_infra(self.infra_id).get_settings().get_raw()
        stage = infra_settings["stage"].replace("&", "")
        print(f"[DEBUG] stage resolved from infra settings = {stage}")

        # Determine which API version to deploy
        if self.api_version == "" or self.api_version is None:
            print(f"[INFO] Executing step: no version specified, resolving latest published version ")
            recent_Api_version = f"v{define_api_version(api_service, stage)}_{stage}"
            print(f"[DEBUG] Resolved latest api_version = {recent_Api_version}")
        else:
            print(f"[INFO] Executing step: verifying specified version '{self.api_version}' exists in published packages")
            infra_txt = self.infra_id.split("_")[-1].upper()
            txt_api_version = f"v{self.api_version}_{infra_txt}"
            print(f"[DEBUG] Looking for package id = {txt_api_version}")

            published_ids = {pkg["id"] for pkg in api_service.list_packages()}
            print(f"[DEBUG] Published package ids = {published_ids}")

            if txt_api_version in published_ids:
                recent_Api_version = txt_api_version
                print(f"[INFO] Specified version found: {recent_Api_version}")
            else:
                print(f"[ERROR] Version '{self.api_version}' does not exist for service '{self.api_service_id}'")
                print(f"[ERROR] Available published ids = {published_ids}")
                return

        # Build deployment identifiers
        service_id = api_service.id
        deployment_id = f"{service_id}-on-{self.infra_id}"
        print(f"[DEBUG] service_id = {service_id}")
        print(f"[DEBUG] deployment_id = {deployment_id}")

        print(f"[INFO] Executing step: creating or updating deployment '{deployment_id}'")
        create_or_update_deployment(
            self.deployer_client, deployment_id, self.infra_id, recent_Api_version, service_id
        )
        print(f"[INFO] Deployment '{deployment_id}' created or updated on infra '{self.infra_id}'")

        print(f"[INFO] End processing project: {self.project_key}")
        print(f"[INFO] End running function UseCaseIndusAPIDeployer RUN")


def run_deploy_use_case_indus_api(design_rd_user_api_key, project_key, deployer_api_key, api_service_id, infra_id,
                                  api_version):
    """Entry point to instantiate and run the API deployment workflow."""
    print(f"[INFO] Start running function run_deploy_use_case_indus_api")
    print(f"[DEBUG] project_key = {project_key}, api_service_id = {api_service_id}, infra_id = {infra_id}")

    # TODO: move host information into a config file
    design_rd_host = "https://ds-studio-0r1.leasingsolutions.echonet"
    deployer_host = "https://ds-deploy.leasingsolutions.echonet"
    print(f"[DEBUG] design_rd_host = {design_rd_host}")
    print(f"[DEBUG] deployer_host = {deployer_host}")

    print(f"[INFO] Executing step: initializing UseCaseIndusAPIDeployer")
    use_case_indus_api = UseCaseIndusAPIDeployer(design_rd_host, design_rd_user_api_key, project_key, deployer_host,
                                                 deployer_api_key, api_service_id, infra_id, api_version)

    print(f"[INFO] Executing step: running deployment workflow")
    use_case_indus_api.run(None)

    print(f"[INFO] End running function run_deploy_use_case_indus_api")


def build_parser(params):
    """Build an argparse parser from a list of (param_name, required) tuples."""
    parser = argparse.ArgumentParser()
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
        ("infra-id", True),
        ("api-version", False),   # Optional: if not provided, latest published version is used
    ]

    parser = build_parser(params)
    args = parser.parse_args()

    print("[INFO] Input arguments check passed")
    print(f"[DEBUG] api_service_id = {args.api_service_id}")
    print(f"[DEBUG] infra_id = {args.infra_id}")
    print(f"[DEBUG] api_version = {args.api_version if args.api_version else '(not specified, will use latest)'}")

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

    run_deploy_use_case_indus_api(
        args.design_rd_user_api_key,
        project_key,
        args.deployer_api_key,
        args.api_service_id,
        args.infra_id,
        args.api_version if args.api_version else ""
    )

    print(f"[INFO] End processing project: {project_key}")
    print("[INFO] Deploy use case indus API completed successfully")
