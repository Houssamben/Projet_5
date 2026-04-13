import sys
import dataikuapi
import requests
import urllib3
import json

from lib.macro_utils import *

# Désactiver les avertissements SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

class UseCaseIndusAPIDeployer():
    def __init__(self, design_rd_host, design_rd_user_api_key, project_key, deployer_host, deployer_api_key,
                 api_service_id, infra_id, api_version):

        self.client = dataikuapi.DSSClient(design_rd_host, design_rd_user_api_key, insecure_tls=True)
        self.deployer_client = dataikuapi.DSSClient(deployer_host, deployer_api_key, insecure_tls=True)

        self.project_key = project_key
        self.api_service_id = api_service_id
        self.infra_id = infra_id
        self.api_version = api_version


    def run(self, process_callback):
        project = self.client.get_project(self.project_key)
        api_service = project.get_api_service(self.api_service_id)
        api_deployer = self.deployer_client.get_apideployer()
        infra_settings = api_deployer.get_infra(self.infra_id).get_settings().get_raw()
        stage = infra_settings["stage"].replace("&", "")

        if self.api_version == "" or self.api_version is None:
            recent_Api_version = f"v{define_api_version(api_service, stage)}_{stage}"
        else:
            infra_txt = self.infra_id.split("_")[-1].upper()
            txt_api_version = f"v{self.api_version}_{infra_txt}"
            published_ids = {pkg["id"] for pkg in api_service.list_packages()}

            if txt_api_version in published_ids:
                recent_Api_version = txt_api_version
            else:
                print(f"Erreur : la version {self.api_version} n'existe pas pour le service {api_service}")
                return

        service_id = api_service.id
        deployment_id = f"{service_id}-on-{self.infra_id}"

        create_or_update_deployment(self.deployer_client, deployment_id, self.infra_id, recent_Api_version, service_id)

def run_deploy_use_case_indus_api(design_rd_user_api_key, project_key, deployer_api_key, api_service_id, infra_id,
                                  api_version):
    design_rd_host = "https://ds-studio-0r1.leasingsolutions.echonet"
    deployer_host = "https://ds-deploy.leasingsolutions.echonet"

    use_case_indus_api = UseCaseIndusAPIDeployer(design_rd_host, design_rd_user_api_key, project_key, deployer_host,
                                                 deployer_api_key, api_service_id, infra_id, api_version)
    use_case_indus_api.run(None)


if __name__ == "__main__":
    # Vérifier si un token a été fourni en paramètre
    if len(sys.argv) not in [5, 6]:
        print(len(sys.argv))
        print("Usage: python deploy_use_case_indus_api.py <DESIGN_RD_USER_API_KEY> <DEPLOYER_API_KEY> <API_SERVICE_ID> "
              "<INFRA_ID> <OPTIONAL:API_VERSION>")
        sys.exit(1)

    # Récupérer le token depuis les arguments de la ligne de commande
    DESIGN_RD_USER_API_KEY = sys.argv[1]
    DEPLOYER_API_KEY = sys.argv[2]
    API_SERVICE_ID = sys.argv[3]
    INFRA_ID=sys.argv[4]
    if len(sys.argv) == 6:
        API_VERSION=sys.argv[5]
    else:
        API_VERSION = ""

    # Lire le fichier JSON et récupérer la valeur de "name"
    with open('params.json', 'r') as file:
        params_data = json.load(file)
        project_key = params_data.get("name")

    if not project_key:
        print("Error: 'name' key not found in params.json")
        sys.exit(1)

    print("Project_key : ")
    print(project_key)
    run_deploy_use_case_indus_api(DESIGN_RD_USER_API_KEY, project_key, DEPLOYER_API_KEY, API_SERVICE_ID, INFRA_ID,
                                  API_VERSION)
    

    print("Package and publish use case indus run !")