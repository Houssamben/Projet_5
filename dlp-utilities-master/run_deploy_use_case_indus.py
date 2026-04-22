import sys
import dataikuapi
import requests
import urllib3
import json

# Désactiver les avertissements SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

def run_deploy_use_case_indus(token, deployer_host, deployer_api_key, automation_host, automation_api_key, project_key, infra_id, version):
    # Créer un client Dataiku
    client = dataikuapi.DSSClient("https://ds-studio-0r1.leasingsolutions.echonet", token, insecure_tls=True)

    macro_name = "pyrunnable_deploy-use-case-indus_use-case-indus-deployer"

    project = client.get_project(project_key)
    macro = project.get_macro(macro_name)

    params = {
        "deployer_host": deployer_host,
        "deployer_api_key": deployer_api_key,
        "automation_host": automation_host,
        "automation_api_key": automation_api_key,
        "project_key": project_key,
        "infra_id": infra_id,
        "deploy_all": False
    }

    if(version != ""):
        params["deploy_version"] = version

    run_id = macro.run(params=params, wait=True)
    print("run_id : ")
    print(run_id)
    status = macro.get_status(run_id)
    print("Status : ")
    print(status)
    result = macro.get_result(run_id)
    print("Result : ")
    print(result)

if __name__ == "__main__":
    # Vérifier si un token a été fourni en paramètre
    if not (7 <= len(sys.argv) <= 8):
        print("Usage: python run_deploy_use_case_indus.py <DESIGN_RD_USER_API_KEY> <DEPLOYER_HOST> <DEPLOYER_API_KEY> <INFRA_ID> <AUTOMATION_HOST> <AUTOMATION_API_KEY> <OPTIONAL:VERSION>")
        sys.exit(1)

    # Récupérer le token depuis les arguments de la ligne de commande
    token = sys.argv[1]
    deployer_host = sys.argv[2]
    deployer_api_key = sys.argv[3]
    infra_id = sys.argv[4]
    automation_host = sys.argv[5]
    automation_api_key = sys.argv[6]
    if(len(sys.argv) == 8):
        version = sys.argv[7]
    else:
        version = ""

    # Lire le fichier JSON et récupérer la valeur de "name"
    with open('params.json', 'r') as file:
        params_data = json.load(file)
        project_key = params_data.get("name")

    if not project_key:
        print("Error: 'name' key not found in params.json")
        sys.exit(1)

    print("Project_key : ")
    print(project_key)
    run_deploy_use_case_indus(token, deployer_host, deployer_api_key, automation_host, automation_api_key, project_key, infra_id, version)

    print("Macro Package and publish use case indus run !")