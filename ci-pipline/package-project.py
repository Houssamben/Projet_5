import sys
import dataikuapi
import requests
import urllib3
import json

import re

# Désactiver les avertissements SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# pattern for matching project keys
project_key_pattern = re.compile(r"^\d{2}_(\w+)_(DATASET|DESIGN|PRODUCT)$")

def create_group(dss_client, group_name, group_description=None, group_source_type='LOCAL'): #Todo changer par create or update cette fonction
    """Crée un groupe s'il n'existe pas déjà"""
    groups = [g["name"] for g in dss_client.list_groups()]
    if group_name not in groups:
        new_group = dss_client.create_group(group_name, description=group_description, source_type=group_source_type)
        group_definintion = new_group.get_definition()
        group_permissions = {'admin': False, 'mayManageUDM': False, 'mayCreateProjects': False,
                             'mayCreateProjectsFromMacros': False, 'mayCreateProjectsFromTemplates': False,
                             'mayCreateProjectsFromDataikuApps': False, 'mayWriteUnsafeCode': False,
                             'mayWriteSafeCode': False,
                             'mayCreateAuthenticatedConnections': False, 'mayCreateCodeEnvs': False,
                             'mayCreateClusters': False,
                             'mayCreateCodeStudioTemplates': False, 'mayDevelopPlugins': False,
                             'mayEditLibFolders': False,
                             'mayManageCodeEnvs': False, 'mayManageClusters': False,
                             'mayManageCodeStudioTemplates': False,
                             'mayViewIndexedHiveConnections': False, 'mayCreatePublishedAPIServices': False,
                             'mayCreatePublishedProjects': False, 'mayWriteInRootProjectFolder': False,
                             'mayCreateActiveWebContent': False, 'mayCreateWorkspaces': False,
                             'mayShareToWorkspaces': False,
                             'mayCreateDataCollections': False, 'mayPublishToDataCollections': False,
                             'mayManageFeatureStore': False, 'canObtainAPITicketFromCookiesForGroupsRegex': ''}

        group_definintion.update(group_permissions)
        new_group.set_definition(group_definintion)


def extract_included_managed_folders(dss_client, project_key, bundle_id):
    project = dss_client.get_project(project_key)
    managed_folders = project.list_managed_folders()
    try:
        print(f"Search for managed folders in a bundle '{bundle_id}'")
        # Extract the bundle
        #bundles = dss_client.list_bundles()
        #bundle = next((b for b in bundles if b["bundleId"] == bundle_id), None)
        #if not bundle:
        #    print(f"not found ID '{bundle_id}'")
        #    return []
        # Extract everything in the bundle 
        #folders = dss_client.list_managed_folders()
        included_folders = []
        for folder in managed_folders:
            folder_obj = dss_client.get_managed_folder(folder["name"])
            tags = folder_obj.get_definition()["tags"]
            # filter on a specefic tag
            if "Managed_folder:include_folder_to_bundle" in tags:
                print(f" Folder found : {folder['name']}")
                try:
                    files = folder_obj.list_contents()
                    all_files = [f["path"] for f in files]
                    print(f"  → {len(all_files)} folder(s) found in {folder['name']}")
                    included_folders.append({
                        "folder_name": folder["name"],
                        "files": all_files
                    })
                except Exception as e:
                    print(f"Error in the scan of the folder '{folder['name']}': {e}")
        print(f" {len(included_folders)} folder(s) inclus found.")
        return included_folders
    except Exception as e:
        print(f" Error in extract_included_managed_folders: {e}")
        return []

def extract_project_trigram(project_key):
    try:
        match = re.match(project_key_pattern, project_key)
        trigram = match.group(1)
        return trigram
    except:
        return None


def extract_bundle_id_version(bundle):
    # Extract version number from bundleId using regex
    match = re.search(r'_v(\d+)', bundle['bundleId'])
    return int(match.group(1)) if match else None


def define_bundles_version(project):
    proj_bundles = project.list_exported_bundles()
    bundle_versions = [extract_bundle_id_version(bundle) for bundle in proj_bundles.get("bundles", []) if
                       extract_bundle_id_version(bundle) is not None]
    max_bundle_version = max(bundle_versions, default=0)
    return max_bundle_version + 1


def create_and_publish_bundle(project, bundle_id):
    # Export and publish a bundle with the given ID
    project.export_bundle(bundle_id)
    project.publish_bundle(bundle_id)


class PackageUseCaseIndus:
    def __init__(self, project_key, design_rd_host, design_rd_user_api_key, deployer_host, deployer_api_key):
        # Initialization method, sets up configuration and client
        self.project_key = project_key
        self.trigram = extract_project_trigram(project_key)
        self.client = dataikuapi.DSSClient(design_rd_host, design_rd_user_api_key, insecure_tls=True)
        self.deployer_client = dataikuapi.DSSClient(deployer_host, deployer_api_key, insecure_tls=True)
        self.use_case_groups = self.get_use_case_groups()
        self.deployer_project_permissions = self.get_deployer_project_permissions()

    # TODO put this configuration inside json config file
    def get_use_case_groups(self):
        return {
            "admin_group": f"{self.trigram}_Admin",
            "contributor_group": f"{self.trigram}_Contributor",
            "consumer_group": f"{self.trigram}_Consumer"
        }


    # TODO put this configuration inside json config file
    def get_deployer_project_permissions(self):
        return [
            {'group': 'Admin', 'read': True, 'write': True, 'deploy': True, 'admin': True},
            {'group': 'SRE', 'read': True, 'write': True, 'deploy': True, 'admin': True},
            {'group': 'ITOps', 'read': True, 'write': True, 'deploy': True, 'admin': True},
            {'group': f'{self.trigram}_Admin', 'read': True, 'write': False, 'deploy': False, 'admin': False},
            {'group': f'{self.trigram}_Contributor', 'read': True, 'write': False, 'deploy': False, 'admin': False},
            {'group': f'{self.trigram}_Consumer', 'read': True, 'write': False, 'deploy': False, 'admin': False}
        ]

    def run(self, progress_callback):
        project = self.client.get_project(self.project_key)
        bundle_version = define_bundles_version(project)
        new_bundle_name = f"{project_key}_v{bundle_version}"

        # Iterate over each new bundle and publish
        print(f"starting processing for project {self.project_key}")

        # Step 1: Attemp to create and publish the bundle
        try:
            create_and_publish_bundle(project, new_bundle_name)
            print(f" Bundle {new_bundle_name} successfully punlished for {self.project_key}")
        except Exception as e:
            if "cannot export managed folder" in str(e):
                print(f" skipping project {self.project_key} : {e}")
            else:
                print(f"Unexpected error while publishing bundle for {self.project_key} : {e} ")

        # Step 2: Check if there are managed folders in the project
        folders = None
        try:
            folders = project.list_managed_folders()
            print(f"{len(folders)} managed folder(s) found in {self.project_key}")

        except Exception as e:
            print(f" Failed to list managed folders for {self.project_key} : {e}")

        if not folders:
            print(f"No managed folder found in {self.project_key}")


        # Step 3: Extract managed folders included in the bundle
        try:
            included_folders = extract_included_managed_folders(
                dss_client=self.client,
                project_key=self.project_key,
                bundle_id=new_bundle_name
            )
            print(f"folders included extracted from {new_bundle_name} : {included_folders}")
        except Exception as e:
            print(f"Error while extracting managed folders for {self.project_key} : {e} ")

        print(f" All bundles version {bundle_version}  have been successfully published")

        for group in self.use_case_groups.values():
            create_group(self.deployer_client, group, group_description=f"{self.trigram} : Use Case Group",
                         group_source_type='LOCAL')  # TODO mettre le SSO ici

        project_deployer = self.deployer_client.get_projectdeployer()
        deployer_project = project_deployer.get_project(self.project_key)
        deployer_project_settings = deployer_project.get_settings()
        deployer_project_settings_raw = deployer_project_settings.get_raw()

        deployer_project_settings_raw['permissions'] = self.deployer_project_permissions
        deployer_project_settings_raw['owner'] = 'admin'
        deployer_project_settings.save()

        print(f"Bundles version {bundle_version} published.")


def run_package_and_publish_use_case_indus(project_key, design_rd_user_api_key, deployer_api_key):
    # TODO Put node Host information into config file
    design_rd_host = "https://ds-studio-0r1.leasingsolutions.echonet"
    deployer_host = "https://ds-deploy.leasingsolutions.echonet"

    use_case_indus = PackageUseCaseIndus(
        project_key,
        design_rd_host, design_rd_user_api_key,
        deployer_host, deployer_api_key
    )

    use_case_indus.run(None)
  

if __name__ == "__main__":
    # Vérifier si un token a été fourni en paramètre
    if len(sys.argv) != 3:
        print("Usage: python run_package_and_publish_use_case_indus.py <DESIGN_RD_USER_API_KEY> <DEPLOYER_API_KEY>")
        sys.exit(1)

    # Récupérer le token depuis les arguments de la ligne de commande
    DESIGN_RD_USER_API_KEY = sys.argv[1]
    DEPLOYER_API_KEY = sys.argv[2]

    # Lire le fichier JSON et récupérer la valeur de "name"
    with open('params.json', 'r') as file:
        params_data = json.load(file)
        project_key = params_data.get("name")
    if not project_key:
        print("Error: 'name' key not found in params.json")
        sys.exit(1)

    print("Project_key : ")
    print(project_key)
    run_package_and_publish_use_case_indus(project_key, DESIGN_RD_USER_API_KEY, DEPLOYER_API_KEY)

    print("Package and publish use case indus run !")