import dataikuapi
import requests
import urllib3

from core.logger import log, LogLevel, Step
from utils.macro_utils import define_api_version, create_or_update_deployment

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


class UseCaseIndusAPIDeployer:
    def __init__(self, design_rd_host, design_rd_user_api_key, project_key,
                 deployer_host, deployer_api_key, api_service_id, infra_id, api_version,
                 api_groups_permissions):
        """Initialize DSS clients and store deployment parameters."""
        log(LogLevel.INFO, Step.INIT, f"Start UseCaseIndusAPIDeployer.__init__ — project_key={project_key}, api_service_id={api_service_id}, infra_id={infra_id}")
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
        self.api_groups_permissions = api_groups_permissions

        print(f"[DEBUG] api_version (input) = '{self.api_version}' (empty means use latest)")
        log(LogLevel.INFO, Step.INIT, f"End UseCaseIndusAPIDeployer.__init__")
        print(f"[INFO] End UseCaseIndusAPIDeployer initialization")

    def run(self):
        """Resolve the API version to deploy and create or update the deployment."""
        log(LogLevel.INFO, Step.API_DEPLOY, f"Start UseCaseIndusAPIDeployer.run — project_key={self.project_key}")
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
            print(f"[INFO] Executing step: no version specified, resolving latest published version")
            recent_api_version = f"v{define_api_version(api_service, stage)}_{stage}"
            print(f"[DEBUG] Resolved latest api_version = {recent_api_version}")
            log(LogLevel.DEBUG, Step.API_DEPLOY, f"Resolved latest api_version = {recent_api_version}")
        else:
            print(f"[INFO] Executing step: verifying specified version '{self.api_version}' exists in published packages")
            infra_txt = self.infra_id.split("_")[-1].upper()
            txt_api_version = f"v{self.api_version}_{infra_txt}"
            print(f"[DEBUG] Looking for package id = {txt_api_version}")

            published_ids = {pkg["id"] for pkg in api_service.list_packages()}
            print(f"[DEBUG] Published package ids = {published_ids}")

            if txt_api_version in published_ids:
                recent_api_version = txt_api_version
                print(f"[INFO] Specified version found: {recent_api_version}")
                log(LogLevel.INFO, Step.API_DEPLOY, f"Specified version found: {recent_api_version}")
            else:
                log(LogLevel.ERROR, Step.API_DEPLOY, f"Version '{self.api_version}' does not exist for service '{self.api_service_id}'")
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
            self.deployer_client, deployment_id, self.infra_id,
            recent_api_version, service_id, self.api_groups_permissions
        )
        print(f"[INFO] Deployment '{deployment_id}' created or updated on infra '{self.infra_id}'")

        log(LogLevel.INFO, Step.API_DEPLOY, f"End UseCaseIndusAPIDeployer.run — project_key={self.project_key}")
        print(f"[INFO] End processing project: {self.project_key}")
        print(f"[INFO] End running function UseCaseIndusAPIDeployer RUN")
