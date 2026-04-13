import sys
import dataikuapi
import requests
import urllib3
import json
from datetime import datetime
from lib.macro_utils import *
import logging


# Désactiver les avertissements SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


class PackageUseCaseIndusAPI():
    def __init__(self, design_rd_host, design_rd_user_api_key, project_key, deployer_host, deployer_api_key,
                 api_service_id, automation_node_hosts, automation_api_key_qual, automation_api_key_int,
                 automation_api_key_rd, automation_api_key_pprd, automation_api_key_prd):

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


    def run(self, process_callback):
        project = self.client.get_project(self.project_key)
        trigram = extract_project_trigram(self.project_key)

        api_service = project.get_api_service(self.api_service_id)

        # TODO retirer le +1 d'ici pour que la fonction define api version retourne la version d'api défini
        api_version = f"v{define_api_version(api_service) + 1}"

        for automation in self.dict_automations:
            client_automation = dataikuapi.DSSClient(automation["host"], automation["api_key"], insecure_tls=True)
            automation_connections = client_automation.list_connections_names(connection_type="all")
            connection_name = extract_connection_name(trigram.lower(), automation_connections)
            api_version_with_stage = f"{api_version} {automation['infra']}"

            settings = api_service.get_settings()
            service_raw_settings = settings.get_raw()

            endpoint_list = settings.endpoints

            sql_endpoints_list = [endpoint.get("id") for endpoint in endpoint_list if
                                  endpoint.get("type") == "SQL_QUERY"]

            for sql_endpoint in sql_endpoints_list:
                service_raw_settings = update_connection(service_raw_settings, sql_endpoint, connection_name)
                settings.save()

            # Create a new version
            api_service.create_package(api_version_with_stage)

            # Publish to API Deployer
            api_service.publish_package(api_version_with_stage)

def run_package_and_publish_use_case_indus_api(design_rd_user_api_key, project_key, deployer_api_key,
                                               api_service_id, automation_api_key_qual, automation_api_key_int,
                                               automation_api_key_rd, automation_api_key_pprd, automation_api_key_prd):
    design_rd_host = "https://ds-studio-0r1.leasingsolutions.echonet"
    deployer_host = "https://ds-deploy.leasingsolutions.echonet"
    automation_node_hosts = {
        "qual": "https://ds-automa-0u0.leasingsolutions.staging.echonet/",
        "int": "https://ds-automa-0t1.leasingsolutions.dev.echonet/",
        "rd": "https://ds-automa-0r1.leasingsolutions.echonet/",
        "pprod": "https://ds-automa-0q0.leasingsolutions.echonet/",
        "prod": "https://ds-automa.leasingsolutions.echonet/"
    }

    use_case_indus_api = PackageUseCaseIndusAPI(design_rd_host, design_rd_user_api_key, project_key, deployer_host,
                                                deployer_api_key, api_service_id, automation_node_hosts,
                                                automation_api_key_qual, automation_api_key_int, automation_api_key_rd,
                                                automation_api_key_pprd, automation_api_key_prd)
    use_case_indus_api.run(None)
            


if __name__ == "__main__":
    # Vérifier si un token a été fourni en paramètre
    if len(sys.argv) != 9:
        print(len(sys.argv))
        print(sys.argv)
        print("Usage: python run_package_and_publish_use_case_indus_api.py <DESIGN_RD_USER_API_KEY> <DEPLOYER_API_KEY> "
              "<API_SERVICE_ID> <AUTOMATION_API_KEY_QUAL> <AUTOMATION_API_KEY_INT> <AUTOMATION_API_KEY_RD> "
              "<AUTOMATION_API_KEY_PPRD> <AUTOMATION_API_KEY_PRD>")
        sys.exit(1)

    # Récupérer le token depuis les arguments de la ligne de commande
    DESIGN_RD_USER_API_KEY = sys.argv[1]
    DEPLOYER_API_KEY = sys.argv[2]
    API_SERVICE_ID = sys.argv[3]
    AUTOMATION_API_KEY_QUAL = sys.argv[4]
    AUTOMATION_API_KEY_INT = sys.argv[5]
    AUTOMATION_API_KEY_RD = sys.argv[6]
    AUTOMATION_API_KEY_PPRD = sys.argv[7]
    AUTOMATION_API_KEY_PRD = sys.argv[8]

    # Lire le fichier JSON et récupérer la valeur de "name"
    with open('params.json', 'r') as file:
        params_data = json.load(file)
        project_key = params_data.get("name")

    if not project_key:
        print("Error: 'name' key not found in params.json")
        sys.exit(1)

    print("Project_key : ")
    print(project_key)
    run_package_and_publish_use_case_indus_api(DESIGN_RD_USER_API_KEY, project_key, DEPLOYER_API_KEY, API_SERVICE_ID,
                                               AUTOMATION_API_KEY_QUAL, AUTOMATION_API_KEY_INT, AUTOMATION_API_KEY_RD,
                                               AUTOMATION_API_KEY_PPRD, AUTOMATION_API_KEY_PRD)

    print("Macro Package and publish use case indus run !")