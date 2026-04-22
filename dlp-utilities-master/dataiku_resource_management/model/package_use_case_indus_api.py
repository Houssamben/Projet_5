import dataikuapi
import requests
import urllib3

from core.logger import log, LogLevel, Step
from utils.macro_utils import (
    define_api_version,
    extract_project_trigram,
    extract_connection_name,
    update_connection
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


class PackageUseCaseIndusAPI:
    def __init__(self, design_rd_host, design_rd_user_api_key, project_key,
                 deployer_host, deployer_api_key, api_service_id,
                 automation_nodes, api_groups_permissions):
        """Initialize DSS clients and build the list of automation nodes from global_config.

        Args:
            automation_nodes: list of dicts with keys 'host', 'api_key', 'infra'
                              built by the runnable from global_config entries.
            api_groups_permissions: list loaded from package_use_case_indus_api.json
        """
        log(LogLevel.INFO, Step.INIT, f"Start PackageUseCaseIndusAPI.__init__ — project_key={project_key}, api_service_id={api_service_id}")
        print(f"[INFO] Start running function PackageUseCaseIndusAPI init")
        print(f"[DEBUG] project_key = {project_key}, api_service_id = {api_service_id}")

        print(f"[INFO] Executing step: connecting to design RD DSS node")
        self.client = dataikuapi.DSSClient(design_rd_host, design_rd_user_api_key, insecure_tls=True)

        print(f"[INFO] Executing step: connecting to deployer DSS node")
        self.deployer_client = dataikuapi.DSSClient(deployer_host, deployer_api_key, insecure_tls=True)

        self.api_service_id = api_service_id
        self.project_key = project_key
        self.dict_automations = automation_nodes
        self.api_groups_permissions = api_groups_permissions

        print(f"[DEBUG] Number of automation environments configured = {len(self.dict_automations)}")
        log(LogLevel.INFO, Step.INIT, f"End PackageUseCaseIndusAPI.__init__")
        print(f"[INFO] End running function PackageUseCaseIndusAPI init")

    def run(self):
        """Package and publish the API service for every configured automation environment."""
        log(LogLevel.INFO, Step.API_PACKAGE, f"Start PackageUseCaseIndusAPI.run — project_key={self.project_key}")
        print(f"[INFO] Start running function PackageUseCaseIndusAPI run")
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
        log(LogLevel.DEBUG, Step.API_PACKAGE, f"Next api_version = {api_version}")

        # Iterate over each automation environment and create a staged API package
        for automation in self.dict_automations:
            infra = automation['infra']
            log(LogLevel.INFO, Step.API_PACKAGE, f"Processing automation environment = {infra}")
            print(f"[INFO] Executing step: processing automation environment = {infra}")

            print(f"[INFO] Executing step: connecting to automation node for {infra}")
            client_automation = dataikuapi.DSSClient(automation["host"], automation["api_key"], insecure_tls=True)

            print(f"[INFO] Executing step: listing connections on automation node {infra}")
            automation_connections = client_automation.list_connections_names(connection_type="all")
            print(f"[DEBUG] Number of connections on {infra} = {len(automation_connections)}")

            connection_name = extract_connection_name(trigram.lower(), automation_connections)
            print(f"[DEBUG] Resolved connection_name for {infra} = {connection_name}")

            api_version_with_stage = f"{api_version}_{infra}"
            print(f"[DEBUG] api_version_with_stage = {api_version_with_stage}")

            print(f"[INFO] Executing step: retrieving API service settings")
            settings = api_service.get_settings()
            service_raw_settings = settings.get_raw()
            endpoint_list = settings.endpoints

            # Find SQL_QUERY endpoints to remap their connection to the target environment
            sql_endpoints_list = [
                endpoint.get("id") for endpoint in endpoint_list
                if endpoint.get("type") == "SQL_QUERY"
            ]
            print(f"[DEBUG] SQL endpoints found = {sql_endpoints_list}")

            for sql_endpoint in sql_endpoints_list:
                print(f"[INFO] Executing step: remapping connection for SQL endpoint '{sql_endpoint}' on {infra}")
                service_raw_settings = update_connection(service_raw_settings, sql_endpoint, connection_name)
                settings.save()
                print(f"[INFO] Settings saved for endpoint '{sql_endpoint}'")

            # Create a new staged version of the API package
            print(f"[INFO] Executing step: creating API package '{api_version_with_stage}'")
            api_service.create_package(api_version_with_stage)
            log(LogLevel.INFO, Step.API_PACKAGE, f"API package '{api_version_with_stage}' created")
            print(f"[INFO] API package '{api_version_with_stage}' created")

            # Publish the new package to the API Deployer
            print(f"[INFO] Executing step: publishing API package '{api_version_with_stage}' to deployer")
            api_service.publish_package(api_version_with_stage)
            log(LogLevel.INFO, Step.API_PACKAGE, f"API package '{api_version_with_stage}' published for {infra}")
            print(f"[INFO] API package '{api_version_with_stage}' published for environment {infra}")

        log(LogLevel.INFO, Step.API_PACKAGE, f"End PackageUseCaseIndusAPI.run — project_key={self.project_key}")
        print(f"[INFO] End processing project: {self.project_key}")
        print(f"[INFO] End running function PackageUseCaseIndusAPI run")
