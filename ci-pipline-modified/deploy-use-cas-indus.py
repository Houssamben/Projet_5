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

class UseCaseIndusAPIDeployer():
    def __init__(self, design_rd_host, design_rd_user_api_key, project_key, deployer_host, deployer_api_key,
                 api_service_id, infra_id, api_version):
        print("[INFO] Start running function UseCaseIndusAPIDeployer.__init__")
        print(f"[DEBUG] project_key = {project_key}")
        print(f"[DEBUG] infra_id = {infra_id}")
        print(f"[DEBUG] api_service_id = {api_service_id}")
        print(f"[DEBUG] api_version = {api_version if api_version else '(latest)'}")

        self.client = dataikuapi.DSSClient(design_rd_host, design_rd_user_api_key, insecure_tls=True)
        self.deployer_client = dataikuapi.DSSClient(deployer_host, deployer_api_key, insecure_tls=True)

        self.project_key = project_key
        self.api_service_id = api_service_id
        self.infra_id = infra_id
        self.api_version = api_version

        print("[INFO] End running function UseCaseIndusAPIDeployer.__init__")

    def run(self, process_callback):
        print("[INFO] Start running function UseCaseIndusAPIDeployer.run")
        print(f"[INFO] Start processing project: {self.project_key}")

        print("[INFO] Executing step: fetching project from design node")
        project = self.client.get_project(self.project_key)

        print(f"[INFO] Executing step: fetching API service {self.api_service_id}")
        api_service = project.get_api_service(self.api_service_id)

        print("[INFO] Executing step: fetching infra settings from deployer")
        api_deployer = self.deployer_client.get_apideployer()
        infra_settings = api_deployer.get_infra(self.infra_id).get_settings().get_raw()
        stage = infra_settings["stage"].replace("&", "")
        print(f"[DEBUG] stage = {stage}")

        print("[INFO] Executing step: resolving API version to deploy")
        if self.api_version == "" or self.api_version is None:
            print("[DEBUG] No explicit api_version provided — resolving latest version")
            recent_Api_version = f"v{define_api_version(api_service, stage)}_{stage}"
            print(f"[DEBUG] resolved recent_Api_version = {recent_Api_version}")
        else:
            infra_txt = self.infra_id.split("_")[-1].upper()
            txt_api_version = f"v{self.api_version}_{infra_txt}"
            print(f"[DEBUG] requested api_version = {txt_api_version}")
            published_ids = {pkg["id"] for pkg in api_service.list_packages()}
            print(f"[DEBUG] total published packages = {len(published_ids)}")

            if txt_api_version in published_ids:
                recent_Api_version = txt_api_version
                print(f"[DEBUG] version found in published packages: {recent_Api_version}")
            else:
                print(f"[ERROR] Version {self.api_version} does not exist for service {api_service}")
                return

        service_id = api_service.id
        deployment_id = f"{service_id}-on-{self.infra_id}"
        print(f"[DEBUG] service_id = {service_id}")
        print(f"[DEBUG] deployment_id = {deployment_id}")

        print("[INFO] Executing step: creating or updating deployment")
        create_or_update_deployment(self.deployer_client, deployment_id, self.infra_id, recent_Api_version, service_id)

        print(f"[INFO] End processing project: {self.project_key}")
        print("[INFO] End running function UseCaseIndusAPIDeployer.run")

def run_deploy_use_case_indus_api(design_rd_user_api_key, project_key, deployer_api_key, api_service_id, infra_id,
                                  api_version):
    print("[INFO] Start running function run_deploy_use_case_indus_api")
    print(f"[DEBUG] project_key = {project_key}")
    print(f"[DEBUG] infra_id = {infra_id}")
    print(f"[DEBUG] api_service_id = {api_service_id}")

    design_rd_host = "https://ds-studio-0r1.leasingsolutions.echonet"
    deployer_host = "https://ds-deploy.leasingsolutions.echonet"
    print(f"[DEBUG] design_rd_host = {design_rd_host}")
    print(f"[DEBUG] deployer_host = {deployer_host}")

    use_case_indus_api = UseCaseIndusAPIDeployer(design_rd_host, design_rd_user_api_key, project_key, deployer_host,
                                                 deployer_api_key, api_service_id, infra_id, api_version)
    use_case_indus_api.run(None)

    print("[INFO] End running function run_deploy_use_case_indus_api")


def build_parser(params):
    """Build argparse parser from a list of (param_name, required) tuples."""
    parser = argparse.ArgumentParser(description="Deploy use case indus API to the target infra")
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
        ("infra-id", True),
        ("api-version", False),  # Optional: if not provided, latest version is resolved automatically
    ]

    parser = build_parser(params)
    args = parser.parse_args()

    print("[INFO] Input arguments check passed")
    print(f"[DEBUG] infra_id = {args.infra_id}")
    print(f"[DEBUG] api_service_id = {args.api_service_id}")
    print(f"[DEBUG] api_version = {args.api_version if args.api_version else '(latest)'}")

    # Read project key from params.json
    print("[INFO] Executing step: reading project key from params.json")
    with open('params.json', 'r') as file:
        params_data = json.load(file)
        project_key = params_data.get("name")

    if not project_key:
        print("[ERROR] 'name' key not found in params.json")
        sys.exit(1)

    print(f"[DEBUG] project_key = {project_key}")

    API_VERSION = args.api_version if args.api_version else ""

    print(f"[INFO] Start processing project: {project_key}")
    run_deploy_use_case_indus_api(
        args.design_rd_user_api_key,
        project_key,
        args.deployer_api_key,
        args.api_service_id,
        args.infra_id,
        API_VERSION
    )
    print(f"[INFO] End processing project: {project_key}")
    print("[INFO] Deploy use case indus API completed successfully")
