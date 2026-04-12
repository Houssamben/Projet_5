import sys
import dataikuapi
import requests
import urllib3
import json
import re
import logging

# Désactiver les avertissements SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
project_key_pattern = re.compile("^\d{2}_(\w+)_(DATASET|DESIGN|PRODUCT)$")


def create_folder_hierarchy(client, parent_folder, folder_names, permissions):
    """
    Crée une hiérarchie de dossiers imbriqués.

    Args:
        client: Le client pour interagir avec l'API
        parent_folder: Le dossier parent de départ
        folder_names: Liste des noms de dossiers à créer dans l'ordre hiérarchique
        permissions: Les permissions à appliquer aux dossiers

    Returns:
        Le dernier dossier créé dans la hiérarchie
    """
    current_folder = parent_folder
    for folder_name in folder_names:
        current_folder = get_or_create_folder(client, current_folder, folder_name, permissions)
    return current_folder


def get_project_folders(client, project_key):
    def find_project_path(folder_id, current_path):
        folder = client.get_project_folder(folder_id)
        current_path.append({"id": folder.id, "name": folder.name})

        # Vérifier si le projet est dans ce dossier
        projects = client.get_project_folder(folder_id).list_projects()
        for project in projects:
            if project.project_key == project_key:
                return current_path.copy()

        # Rechercher dans les sous-dossiers
        children = folder.list_child_folders()
        for child in children:
            result = find_project_path(child.id, current_path)
            if result:
                return result

        current_path.pop()
        return None

    return find_project_path("ROOT", [])


def create_group(dss_client, group_name, group_description=None, group_source_type='LOCAL'):
    """Crée un groupe s'il n'existe pas déjà"""
    groups = [g["name"] for g in dss_client.list_groups()]
    if group_name not in groups:
        dss_client.create_group(group_name, description=group_description, source_type=group_source_type)


def get_or_create_folder(dss_client, parent_folder, folder_name, folder_permissions):
    child_folders = parent_folder.list_child_folders()

    folder_id = None
    for child_folder in child_folders:
        if child_folder.name == folder_name:
            folder_id = child_folder.id

    if folder_id is None:
        folder = parent_folder.create_sub_folder(folder_name)
    else:
        folder = dss_client.get_project_folder(folder_id)

    folder_settings = folder.get_settings()
    folder_settings_permissions = folder_settings.get_permissions()
    granted_groups = [p["group"] for p in folder_settings_permissions]
    for perm in folder_permissions:
        if perm["group"] in granted_groups:
            for p in folder_settings_permissions:
                if p["group"] == perm["group"]:
                    p.update(perm)
                    break
        else:
            folder_settings_permissions.append(perm)

    folder_settings.save()
    return folder


def extract_project_trigram(project_key):
    try:
        match = re.match(project_key_pattern, project_key)
        trigram = match.group(1)
        return trigram
    except:
        return None


def get_last_version_bundle(bundles):
    last_bundle = None
    last_version = 0
    for bundle in bundles:
        match = re.search(r'_v(\d+)', bundle['bundleId'])
        if match:
            version = int(match.group(1))
            if version > last_version:
                last_version = version
                last_bundle = bundle
    return last_bundle


def get_specified_version_bundle(version, bundles):
    match_bundle = None
    for bundle in bundles:
        match = re.search(rf'_v{version}', bundle['bundleId'])
        if match:
            match_bundle = bundle
    if not match_bundle:
        available_bundles = [b['bundleId'] for b in bundles]
        logging.warn("The specified version does not exist for the project: bundles available are " + ", ".join(
            available_bundles))
        raise ValueError(
            f"The specified version '{version}' does not exist for the project. Available bundles are: " + ', '.join(
                available_bundles))
    return match_bundle


def get_connection_type(connection):
    if re.search(r's3-cft-[a-zA-Z0-9_-]+-co[a-zA-Z0-9]+', connection):
        return 's3-cft'
    if re.search(r's3-[a-zA-Z0-9_-]+-co[a-zA-Z0-9]+', connection):
        return 's3-cos'
    if re.search(r'db-[a-zA-Z0-9_-]+-pg[a-zA-Z0-9]+', connection): # to be checked !!!!
        return 'db-pg'
    return None


def get_mapped_connections(source_connections, target_connections):
    connections = []
    for source in source_connections:
        source_type = get_connection_type(source)
        for target in target_connections:
            target_type = get_connection_type(target)
            if source_type and target_type and source_type == target_type:
                connections.append({"source": source, "target": target})
                break
    return connections


def get_activated_scenarios(project, infra_id):
    scenarios_list = project.list_scenarios(as_type="objects")
    scenarios_settings_list = [s.get_settings() for s in scenarios_list]
    scenarios_settings_raw_list = [s.get_raw() for s in scenarios_settings_list]
    activated_scenarios = [s["id"] for s in scenarios_settings_raw_list if
                        f"Scenarios:{infra_id}_activated" in s["tags"]]

    return {scenario_id: True for scenario_id in activated_scenarios}


def create_or_update_deployment(dss_deployer_client, deployment_id, trg_project_key, infra_id, bundle_id,
                                remapping_global_connections, remapping_project_connections,
                                automation_project_folder_id, trg_project):
    project_deployer = dss_deployer_client.get_projectdeployer()
    deployment_list = project_deployer.list_deployments(as_objects=True)
    deployment = next((d for d in deployment_list if d.get_settings().get_raw()["id"] == deployment_id and d.get_settings().get_raw()["infraId"] == infra_id), None)

    if not deployment:
        print("no deployment exist")
        deployment = project_deployer.create_deployment(deployment_id, trg_project_key, infra_id, bundle_id, deployed_project_key=trg_project_key)

    deployment_settings = deployment.get_settings()
    deployment_settings_raw = deployment_settings.get_raw()
    deployment_settings_raw["bundleId"] = bundle_id
    deployment_settings_raw["bundleContainerSettings"]["remapping"][
        "connections"] = remapping_global_connections + remapping_project_connections
    deployment_settings_raw["projectFolderId"] = automation_project_folder_id
    deployment_settings_raw["scenariosToActivate"] = get_activated_scenarios(trg_project, infra_id)
    deployment_settings.save()
    print("deploymetn saved")
    update = deployment.start_update()
    update.wait_for_result()
    print("deploymetn updated")

    return deployment


def update_automation_project(dss_client, project_key, project_permissions):
    project = dss_client.get_project(project_key)
    project_git = project.get_project_git()
    if project_git.get_remote():
        project_git.remove_remote()
    if "master" not in project_git.list_branches(remote=False):
        project_git.create_branch("master")

    permissions = project.get_permissions()
    for perm in project_permissions:
        permissions["permissions"].append(perm)
    project.set_permissions(permissions)


class UseCaseIndusDeployer():
        def __init__(self, design_rd_host, design_rd_user_api_key, deployer_host, deployer_api_key, automation_host,
                     automation_api_key, project_key, infra_id, version):

            self.client = dataikuapi.DSSClient(design_rd_host, design_rd_user_api_key, insecure_tls=True)
            self.deployer_client = dataikuapi.DSSClient(deployer_host, deployer_api_key, insecure_tls=True)
            self.automation_client = dataikuapi.DSSClient(automation_host, automation_api_key, insecure_tls=True)

            self.project_key = project_key
            self.trigram = extract_project_trigram(project_key)

            self.use_case_groups = self.get_use_case_groups()
            self.project_permissions = self.get_use_case_project_permissions()
            self.folder_permissions = self.get_folder_permission()

            self.infra_id = infra_id
            self.version = version
            self.is_data_source_project = False

        # TODO put this configuration inside json config file
        def get_use_case_groups(self):
            return {
                "admin_group": f"{self.trigram}_Admin",
                "contributor_group": f"{self.trigram}_Contributor",
                "consumer_group": f"{self.trigram}_Consumer"
            }

        # TODO put this configuration inside json config file
        def get_use_case_project_permissions(self):
            return {
                "automation_rd": [
                    {
                        "group": self.use_case_groups["admin_group"],
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": self.use_case_groups["contributor_group"],
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": self.use_case_groups["consumer_group"],
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": False,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": "ITops",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "SRE",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "administrators",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    }
                ],
                "automation_pprod": [
                    {
                        "group": self.use_case_groups["admin_group"],
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": False,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": self.use_case_groups["contributor_group"],
                        "admin": False,
                        "readProjectContent": False,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": False,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": self.use_case_groups["consumer_group"],
                        "admin": False,
                        "readProjectContent": False,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": False,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": "ITops",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "SRE",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "administrators",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    }
                ],
                "automation_prod": [
                    {
                        "group": self.use_case_groups["admin_group"],
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": False,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": self.use_case_groups["contributor_group"],
                        "admin": False,
                        "readProjectContent": False,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": False,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": self.use_case_groups["consumer_group"],
                        "admin": False,
                        "readProjectContent": False,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": False,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": "ITops",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "SRE",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "administrators",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    }
                ],
                "automation_qual": [
                    {
                        "group": self.use_case_groups["admin_group"],
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": self.use_case_groups["contributor_group"],
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": self.use_case_groups["consumer_group"],
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": False,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": "ITops",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "SRE",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "administrators",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    }
                ],
                "automation_int": [
                    {
                        "group": self.use_case_groups["admin_group"],
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": self.use_case_groups["contributor_group"],
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": self.use_case_groups["consumer_group"],
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": False,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": "ITops",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "SRE",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "administrators",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    }
                ]
            }

        # TODO put this configuration inside json config file
        def get_data_source_project_permissions(self):
            return {
                "automation_rd": [
                    {
                        "group": "Data_Engineer",
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": "MLOps",
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": "ITops",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "SRE",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "administrators",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    }
                ],
                "automation_pprod": [
                    {
                        "group": "Data_Engineer",
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": False,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": "MLOps",
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": False,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": "ITops",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "SRE",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "administrators",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    }
                ],
                "automation_prod": [
                    {
                        "group": "Data_Engineer",
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": False,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": "MLOps",
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": False,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": "ITops",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "SRE",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "administrators",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    }
                ],
                "automation_qual": [
                    {
                        "group": "Data_Engineer",
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": "MLOps",
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": "ITops",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "SRE",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "administrators",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    }
                ],
                "automation_int": [
                    {
                        "group": "Data_Engineer",
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": "MLOps",
                        "admin": False,
                        "readProjectContent": True,
                        "writeProjectContent": False,
                        "publishToDataCollections": False,
                        "shareToWorkspaces": False,
                        "exportDatasetsData": False,
                        "readDashboards": True,
                        "writeDashboards": False,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": False,
                        "manageExposedElements": False
                    },
                    {
                        "group": "ITops",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "SRE",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    },
                    {
                        "group": "administrators",
                        "admin": True,
                        "readProjectContent": True,
                        "writeProjectContent": True,
                        "publishToDataCollections": True,
                        "shareToWorkspaces": True,
                        "exportDatasetsData": True,
                        "readDashboards": True,
                        "writeDashboards": True,
                        "runScenarios": True,
                        "manageAdditionalDashboardUsers": True,
                        "manageExposedElements": True
                    }
                ]
            }

        # TODO put this configuration inside json config file
        def get_folder_permission(self):
            return [
                {
                    "group": "administrators",
                    'admin': True,
                    'read': True,
                    'writeContents': True
                }
            ]

        def run(self, process_callback):
            indus_folder_name = "Use Case Indus"
            data_source_folder_name = "01 Data Source"

            project_folders = get_project_folders(self.client, self.project_key)
            if any(project_folder['name'] == data_source_folder_name for project_folder in project_folders):
                self.is_data_source_project = True
                self.project_permissions = self.get_data_source_project_permissions()

            automation_root_project_folder = self.automation_client.get_root_project_folder()

            folder_hierarchy = [folder['name'] for folder in project_folders if
                                folder['name'] is not None and folder['id'] != 'ROOT']

            automation_project_folder = create_folder_hierarchy(
                self.automation_client,
                automation_root_project_folder,
                folder_hierarchy,
                self.folder_permissions
            )

            client_connections = self.client.list_connections_names("all")
            automation_client_connections = self.automation_client.list_connections_names("all")

            remapping_project_connections = []
            if not self.is_data_source_project:
                project_connections = [pc for pc in client_connections if self.trigram.lower() in pc]
                automation_project_connections = [apc for apc in automation_client_connections if
                                                  self.trigram.lower() in apc]

                remapping_project_connections = get_mapped_connections(project_connections,
                                                                       automation_project_connections)

                for group in self.use_case_groups.values():
                    create_group(self.automation_client, group, group_description=f"{self.trigram} : Use Case Group",
                                 group_source_type='LOCAL') #TODO mettre le SSO ici
                logging.info("Project Groups done.")

            global_connection_mapping = self.client.get_global_variables() #TODO remettre ces info dans un fichier de conf

            remapping_global_connections = []
            for global_connection in global_connection_mapping['global_connection_mapping'].values():
                if global_connection[self.infra_id] and global_connection[self.infra_id].strip() != "":
                    remapping_global_connections.append({
                        "source": global_connection['design_rd'],
                        "target": global_connection[self.infra_id]
                    })

            trg_project = self.client.get_project(self.project_key)
            trg_bundles = trg_project.list_exported_bundles()
            if self.version:
                trg_bundle = get_specified_version_bundle(self.version, trg_bundles["bundles"])
            else:
                trg_bundle = get_last_version_bundle(trg_bundles["bundles"])
            deployment_id = f"{self.project_key}_{self.infra_id}"
            bundle_id = trg_bundle['bundleId']
            create_or_update_deployment(self.deployer_client, deployment_id, self.project_key, self.infra_id,
                                        bundle_id, remapping_global_connections,
                                        remapping_project_connections, automation_project_folder.id,
                                        trg_project)

            logging.info(f"Created or updated deployment for project: {self.project_key}")

            update_automation_project(self.automation_client, self.project_key,
                                      self.project_permissions[self.infra_id])

            logging.info(f"Updated automation project: {self.project_key}")


def run_deploy_use_case_indus(design_rd_user_api_key, deployer_api_key, automation_api_key, project_key, infra_id,
                              version):
    # TODO Put node Host information into config file
    design_rd_host = "https://ds-studio-0r1.leasingsolutions.echonet"
    deployer_host = "https://ds-deploy.leasingsolutions.echonet"
    automation_node_hosts = {
        "automation_qual": "https://ds-automa-0u0.leasingsolutions.staging.echonet/",
        "automation_int": "https://ds-automa-0t1.leasingsolutions.dev.echonet/",
        "automation_rd": "https://ds-automa-0r1.leasingsolutions.echonet/",
        "automation_pprod": "https://ds-automa-0q0.leasingsolutions.echonet/",
        "automation_prod": "https://ds-automa.leasingsolutions.echonet/"
    }
    automation_host = automation_node_hosts[infra_id]

    print("running function")
    use_case_indus = UseCaseIndusDeployer(design_rd_host, design_rd_user_api_key, deployer_host, deployer_api_key, automation_host, automation_api_key,
                                          project_key, infra_id, version)
    use_case_indus.run(None)

if __name__ == "__main__":
    # Vérifier si un token a été fourni en paramètre
    if not (5 <= len(sys.argv) <= 6):
        print(sys.argv)

        print("Usage: python run_deploy_use_case_indus.py <DESIGN_RD_USER_API_KEY> <DEPLOYER_API_KEY> <INFRA_ID> <AUTOMATION_API_KEY> <OPTIONAL:VERSION>")
        sys.exit(1)

    # Récupérer le token depuis les arguments de la ligne de commande
    DESIGN_RD_USER_API_KEY = sys.argv[1]
    DEPLOYER_API_KEY = sys.argv[2]
    INFRA_ID = sys.argv[3]
    AUTOMATION_API_KEY = sys.argv[4]
    if len(sys.argv) == 6:
        VERSION = sys.argv[5]
    else:
        VERSION = ""

    # Lire le fichier JSON et récupérer la valeur de "name"
    with open('params.json', 'r') as file:
        params_data = json.load(file)
        project_key = params_data.get("name")
    if not project_key:
        print("Error: 'name' key not found in params.json")
        sys.exit(1)

    print(f"Project_key : {project_key}")
    run_deploy_use_case_indus(DESIGN_RD_USER_API_KEY, DEPLOYER_API_KEY, AUTOMATION_API_KEY, project_key,
                              INFRA_ID, VERSION)

    print("Package and publish use case indus run !")
