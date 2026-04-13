import sys
import argparse
import dataikuapi
import requests
import urllib3
import json
import re

# Disable SSL warnings for internal/self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
project_key_pattern = re.compile("^\d{2}_(\w+)_(DATASET|DESIGN|PRODUCT)$")


def create_folder_hierarchy(client, parent_folder, folder_names, permissions):
    """
    Creates a nested folder hierarchy.

    Args:
        client: The API client
        parent_folder: Starting parent folder
        folder_names: Ordered list of folder names to create
        permissions: Permissions to apply to each folder

    Returns:
        The last folder created in the hierarchy
    """
    print("[INFO] Start running function create_folder_hierarchy")
    print(f"[DEBUG] folder_names = {folder_names}")

    current_folder = parent_folder
    for folder_name in folder_names:
        print(f"[INFO] Executing step: get or create folder '{folder_name}'")
        current_folder = get_or_create_folder(client, current_folder, folder_name, permissions)

    print("[INFO] End running function create_folder_hierarchy")
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
    """Create a group if it does not already exist"""
    print("[INFO] Start running function create_group")
    print(f"[DEBUG] group_name = {group_name}")
    print(f"[DEBUG] group_source_type = {group_source_type}")

    groups = [g["name"] for g in dss_client.list_groups()]
    print(f"[DEBUG] total existing groups = {len(groups)}")

    if group_name not in groups:
        print(f"[INFO] Executing step: group '{group_name}' not found — creating it")
        dss_client.create_group(group_name, description=group_description, source_type=group_source_type)
    else:
        print(f"[INFO] Executing step: group '{group_name}' already exists — skipping creation")

    print("[INFO] End running function create_group")


def get_or_create_folder(dss_client, parent_folder, folder_name, folder_permissions):
    print("[INFO] Start running function get_or_create_folder")
    print(f"[DEBUG] folder_name = {folder_name}")

    child_folders = parent_folder.list_child_folders()

    folder_id = None
    for child_folder in child_folders:
        if child_folder.name == folder_name:
            folder_id = child_folder.id

    if folder_id is None:
        print(f"[INFO] Executing step: folder '{folder_name}' not found — creating it")
        folder = parent_folder.create_sub_folder(folder_name)
    else:
        print(f"[INFO] Executing step: folder '{folder_name}' already exists — reusing it")
        folder = dss_client.get_project_folder(folder_id)

    print("[INFO] Executing step: applying permissions to folder")
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
    print("[INFO] End running function get_or_create_folder")
    return folder


def extract_project_trigram(project_key):
    print("[INFO] Start running function extract_project_trigram")
    print(f"[DEBUG] project_key = {project_key}")

    try:
        match = re.match(project_key_pattern, project_key)
        trigram = match.group(1)
        print(f"[DEBUG] extracted trigram = {trigram}")
        print("[INFO] End running function extract_project_trigram")
        return trigram
    except:
        print(f"[WARNING] Could not extract trigram from project_key = {project_key}")
        print("[INFO] End running function extract_project_trigram")
        return None


def get_last_version_bundle(bundles):
    print("[INFO] Start running function get_last_version_bundle")
    print(f"[DEBUG] total bundles to scan = {len(bundles)}")

    last_bundle = None
    last_version = 0
    for bundle in bundles:
        match = re.search(r'_v(\d+)', bundle['bundleId'])
        if match:
            version = int(match.group(1))
            if version > last_version:
                last_version = version
                last_bundle = bundle

    print(f"[DEBUG] last_version = {last_version}")
    print(f"[DEBUG] last_bundle = {last_bundle['bundleId'] if last_bundle else None}")
    print("[INFO] End running function get_last_version_bundle")
    return last_bundle


def get_specified_version_bundle(version, bundles):
    print("[INFO] Start running function get_specified_version_bundle")
    print(f"[DEBUG] requested version = {version}")
    print(f"[DEBUG] total bundles to scan = {len(bundles)}")

    match_bundle = None
    for bundle in bundles:
        match = re.search(rf'_v{version}', bundle['bundleId'])
        if match:
            match_bundle = bundle

    if not match_bundle:
        available_bundles = [b['bundleId'] for b in bundles]
        print("[WARNING] The specified version does not exist for the project: bundles available are " + ", ".join(
            available_bundles))
        raise ValueError(
            f"The specified version '{version}' does not exist for the project. Available bundles are: " + ', '.join(
                available_bundles))

    print(f"[DEBUG] matched bundle = {match_bundle['bundleId']}")
    print("[INFO] End running function get_specified_version_bundle")
    return match_bundle


def get_connection_type(connection):
    print("[INFO] Start running function get_connection_type")

    if re.search(r's3-cft-[a-zA-Z0-9_-]+-co[a-zA-Z0-9]+', connection):
        print("[DEBUG] connection type = s3-cft")
        print("[INFO] End running function get_connection_type")
        return 's3-cft'
    if re.search(r's3-[a-zA-Z0-9_-]+-co[a-zA-Z0-9]+', connection):
        print("[DEBUG] connection type = s3-cos")
        print("[INFO] End running function get_connection_type")
        return 's3-cos'
    if re.search(r'db-[a-zA-Z0-9_-]+-pg[a-zA-Z0-9]+', connection): # to be checked !!!!
        print("[DEBUG] connection type = db-pg")
        print("[INFO] End running function get_connection_type")
        return 'db-pg'
    print("[WARNING] connection type not recognized")
    print("[INFO] End running function get_connection_type")
    return None


def get_mapped_connections(source_connections, target_connections):
    print("[INFO] Start running function get_mapped_connections")
    print(f"[DEBUG] number of source connections = {len(source_connections)}")
    print(f"[DEBUG] number of target connections = {len(target_connections)}")

    connections = []
    for source in source_connections:
        source_type = get_connection_type(source)
        for target in target_connections:
            target_type = get_connection_type(target)
            if source_type and target_type and source_type == target_type:
                connections.append({"source": source, "target": target})
                print(f"[DEBUG] mapped connection: {source} -> {target}")
                break

    print(f"[DEBUG] total mapped connections = {len(connections)}")
    print("[INFO] End running function get_mapped_connections")
    return connections


def get_activated_scenarios(project, infra_id):
    print("[INFO] Start running function get_activated_scenarios")
    print(f"[DEBUG] infra_id = {infra_id}")

    scenarios_list = project.list_scenarios(as_type="objects")
    print(f"[DEBUG] total scenarios found = {len(scenarios_list)}")

    scenarios_settings_list = [s.get_settings() for s in scenarios_list]
    scenarios_settings_raw_list = [s.get_raw() for s in scenarios_settings_list]
    activated_scenarios = [s["id"] for s in scenarios_settings_raw_list if
                        f"Scenarios:{infra_id}_activated" in s["tags"]]

    print(f"[DEBUG] number of activated scenarios for infra '{infra_id}' = {len(activated_scenarios)}")
    print("[INFO] End running function get_activated_scenarios")
    return {scenario_id: True for scenario_id in activated_scenarios}


def create_or_update_deployment(dss_deployer_client, deployment_id, trg_project_key, infra_id, bundle_id,
                                remapping_global_connections, remapping_project_connections,
                                automation_project_folder_id, trg_project):
    print("[INFO] Start running function create_or_update_deployment")
    print(f"[DEBUG] deployment_id = {deployment_id}")
    print(f"[DEBUG] trg_project_key = {trg_project_key}")
    print(f"[DEBUG] infra_id = {infra_id}")
    print(f"[DEBUG] bundle_id = {bundle_id}")
    print(f"[DEBUG] global connection remappings = {len(remapping_global_connections)}")
    print(f"[DEBUG] project connection remappings = {len(remapping_project_connections)}")

    print("[INFO] Executing step: fetching all deployments from deployer node")
    project_deployer = dss_deployer_client.get_projectdeployer()
    deployment_list = project_deployer.list_deployments(as_objects=True)
    print(f"[DEBUG] total deployments found = {len(deployment_list)}")

    deployment = next((d for d in deployment_list if d.get_settings().get_raw()["id"] == deployment_id and d.get_settings().get_raw()["infraId"] == infra_id), None)

    if not deployment:
        print(f"[INFO] Executing step: no deployment found — creating new deployment '{deployment_id}'")
        deployment = project_deployer.create_deployment(deployment_id, trg_project_key, infra_id, bundle_id, deployed_project_key=trg_project_key)
    else:
        print(f"[INFO] Executing step: deployment '{deployment_id}' found — updating it")

    print("[INFO] Executing step: applying bundle, connections remapping and scenario activation")
    deployment_settings = deployment.get_settings()
    deployment_settings_raw = deployment_settings.get_raw()
    deployment_settings_raw["bundleId"] = bundle_id
    deployment_settings_raw["bundleContainerSettings"]["remapping"][
        "connections"] = remapping_global_connections + remapping_project_connections
    deployment_settings_raw["projectFolderId"] = automation_project_folder_id
    deployment_settings_raw["scenariosToActivate"] = get_activated_scenarios(trg_project, infra_id)

    print("[INFO] Executing step: saving deployment settings")
    deployment_settings.save()
    print("[INFO] Executing step: deployment settings saved")

    print("[INFO] Executing step: starting deployment update and waiting for result")
    update = deployment.start_update()
    update.wait_for_result()
    print("[INFO] Executing step: deployment update completed")

    print("[INFO] End running function create_or_update_deployment")
    return deployment


def update_automation_project(dss_client, project_key, project_permissions):
    print("[INFO] Start running function update_automation_project")
    print(f"[DEBUG] project_key = {project_key}")
    print(f"[DEBUG] number of permissions to apply = {len(project_permissions)}")

    print("[INFO] Executing step: fetching project and git configuration")
    project = dss_client.get_project(project_key)
    project_git = project.get_project_git()

    if project_git.get_remote():
        print("[INFO] Executing step: remote found — removing it")
        project_git.remove_remote()

    if "master" not in project_git.list_branches(remote=False):
        print("[INFO] Executing step: 'master' branch not found — creating it")
        project_git.create_branch("master")

    print("[INFO] Executing step: updating project permissions")
    permissions = project.get_permissions()
    for perm in project_permissions:
        permissions["permissions"].append(perm)
    project.set_permissions(permissions)

    print("[INFO] End running function update_automation_project")


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
            print("[INFO] Start running function UseCaseIndusDeployer.run")
            print(f"[INFO] Start processing project: {self.project_key}")
            print(f"[DEBUG] infra_id = {self.infra_id}")
            print(f"[DEBUG] version = {self.version if self.version else '(latest)'}")

            indus_folder_name = "Use Case Indus"
            data_source_folder_name = "01 Data Source"

            print("[INFO] Executing step: fetching project folder hierarchy from design node")
            project_folders = get_project_folders(self.client, self.project_key)
            print(f"[DEBUG] project folder hierarchy = {[f['name'] for f in project_folders]}")

            if any(project_folder['name'] == data_source_folder_name for project_folder in project_folders):
                print(f"[INFO] Executing step: data source project detected — switching permissions profile")
                self.is_data_source_project = True
                self.project_permissions = self.get_data_source_project_permissions()

            print("[INFO] Executing step: fetching root project folder from automation node")
            automation_root_project_folder = self.automation_client.get_root_project_folder()

            folder_hierarchy = [folder['name'] for folder in project_folders if
                                folder['name'] is not None and folder['id'] != 'ROOT']
            print(f"[DEBUG] folder_hierarchy = {folder_hierarchy}")

            print("[INFO] Executing step: creating folder hierarchy on automation node")
            automation_project_folder = create_folder_hierarchy(
                self.automation_client,
                automation_root_project_folder,
                folder_hierarchy,
                self.folder_permissions
            )

            print("[INFO] Executing step: listing connections on design and automation nodes")
            client_connections = self.client.list_connections_names("all")
            automation_client_connections = self.automation_client.list_connections_names("all")
            print(f"[DEBUG] design node connections count = {len(client_connections)}")
            print(f"[DEBUG] automation node connections count = {len(automation_client_connections)}")

            remapping_project_connections = []
            if not self.is_data_source_project:
                print("[INFO] Executing step: computing project-level connection remappings")
                project_connections = [pc for pc in client_connections if self.trigram.lower() in pc]
                automation_project_connections = [apc for apc in automation_client_connections if
                                                  self.trigram.lower() in apc]
                print(f"[DEBUG] project connections (design) = {project_connections}")
                print(f"[DEBUG] project connections (automation) = {automation_project_connections}")

                remapping_project_connections = get_mapped_connections(project_connections,
                                                                       automation_project_connections)

                print("[INFO] Executing step: creating use case groups on automation node")
                for group in self.use_case_groups.values():
                    create_group(self.automation_client, group, group_description=f"{self.trigram} : Use Case Group",
                                 group_source_type='LOCAL') #TODO mettre le SSO ici
                print("[INFO] Executing step: project groups creation done")

            print("[INFO] Executing step: fetching global connection mapping from design node variables") #TODO remettre ces info dans un fichier de conf
            global_connection_mapping = self.client.get_global_variables()

            remapping_global_connections = []
            for global_connection in global_connection_mapping['global_connection_mapping'].values():
                if global_connection[self.infra_id] and global_connection[self.infra_id].strip() != "":
                    remapping_global_connections.append({
                        "source": global_connection['design_rd'],
                        "target": global_connection[self.infra_id]
                    })
            print(f"[DEBUG] global connection remappings count = {len(remapping_global_connections)}")

            print("[INFO] Executing step: fetching bundles and resolving target bundle")
            trg_project = self.client.get_project(self.project_key)
            trg_bundles = trg_project.list_exported_bundles()
            if self.version:
                print(f"[DEBUG] using specified version = {self.version}")
                trg_bundle = get_specified_version_bundle(self.version, trg_bundles["bundles"])
            else:
                print("[DEBUG] no version specified — using latest bundle")
                trg_bundle = get_last_version_bundle(trg_bundles["bundles"])

            deployment_id = f"{self.project_key}_{self.infra_id}"
            bundle_id = trg_bundle['bundleId']
            print(f"[DEBUG] deployment_id = {deployment_id}")
            print(f"[DEBUG] bundle_id = {bundle_id}")

            print("[INFO] Executing step: creating or updating deployment")
            create_or_update_deployment(self.deployer_client, deployment_id, self.project_key, self.infra_id,
                                        bundle_id, remapping_global_connections,
                                        remapping_project_connections, automation_project_folder.id,
                                        trg_project)

            print(f"[INFO] Created or updated deployment for project: {self.project_key}")

            print("[INFO] Executing step: updating automation project permissions")
            update_automation_project(self.automation_client, self.project_key,
                                      self.project_permissions[self.infra_id])

            print(f"[INFO] Updated automation project: {self.project_key}")
            print(f"[INFO] End processing project: {self.project_key}")
            print("[INFO] End running function UseCaseIndusDeployer.run")


def run_deploy_use_case_indus(design_rd_user_api_key, deployer_api_key, automation_api_key, project_key, infra_id,
                              version):
    print("[INFO] Start running function run_deploy_use_case_indus")
    print(f"[DEBUG] project_key = {project_key}")
    print(f"[DEBUG] infra_id = {infra_id}")
    print(f"[DEBUG] version = {version if version else '(latest)'}")

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
    print(f"[DEBUG] design_rd_host = {design_rd_host}")
    print(f"[DEBUG] deployer_host = {deployer_host}")
    print(f"[DEBUG] automation_host = {automation_host}")

    use_case_indus = UseCaseIndusDeployer(design_rd_host, design_rd_user_api_key, deployer_host, deployer_api_key, automation_host, automation_api_key,
                                          project_key, infra_id, version)
    use_case_indus.run(None)

    print("[INFO] End running function run_deploy_use_case_indus")


def build_parser(params):
    """Build argparse parser from a list of (param_name, required) tuples."""
    parser = argparse.ArgumentParser(description="Deploy use case indus project bundle to the target infra")
    for param, required in params:
        parser.add_argument(f"--{param}", required=required)
    return parser


if __name__ == "__main__":
    print("[INFO] Input arguments check")

    # Define expected arguments: (argument name, required)
    params = [
        ("design-rd-user-api-key", True),
        ("deployer-api-key", True),
        ("infra-id", True),
        ("automation-api-key", True),
        ("version", False),  # Optional: if not provided, latest bundle version is used
    ]

    parser = build_parser(params)
    args = parser.parse_args()

    print("[INFO] Input arguments check passed")
    print(f"[DEBUG] infra_id = {args.infra_id}")
    print(f"[DEBUG] version = {args.version if args.version else '(latest)'}")

    # Read project key from params.json
    print("[INFO] Executing step: reading project key from params.json")
    with open('params.json', 'r') as file:
        params_data = json.load(file)
        project_key = params_data.get("name")

    if not project_key:
        print("[ERROR] 'name' key not found in params.json")
        sys.exit(1)

    print(f"[DEBUG] project_key = {project_key}")

    VERSION = args.version if args.version else ""

    print(f"[INFO] Start processing project: {project_key}")
    run_deploy_use_case_indus(
        args.design_rd_user_api_key,
        args.deployer_api_key,
        args.automation_api_key,
        project_key,
        args.infra_id,
        VERSION
    )
    print(f"[INFO] End processing project: {project_key}")
    print("[INFO] Deploy use case indus completed successfully")
