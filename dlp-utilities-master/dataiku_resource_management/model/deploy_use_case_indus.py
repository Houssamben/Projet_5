import re
import dataikuapi
import requests
import urllib3

from core.logger import log, LogLevel, Step
from utils.helpers import format_nested_structure

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

project_key_pattern = re.compile(r"^\d{2}_(\w+)_(DATASET|DESIGN|PRODUCT)$")


def create_folder_hierarchy(client, parent_folder, folder_names, permissions):
    """Create a nested folder hierarchy on the given DSS node."""
    log(LogLevel.INFO, Step.DEPLOY, f"Start create_folder_hierarchy — folders={folder_names}")
    print(f"[INFO] Start running function create_folder_hierarchy")
    print(f"[DEBUG] Folder hierarchy to create = {folder_names}")

    current_folder = parent_folder
    for folder_name in folder_names:
        print(f"[INFO] Executing step: getting or creating folder '{folder_name}'")
        current_folder = get_or_create_folder(client, current_folder, folder_name, permissions)

    print(f"[INFO] End running function create_folder_hierarchy")
    log(LogLevel.INFO, Step.DEPLOY, "End create_folder_hierarchy")
    return current_folder


def get_project_folders(client, project_key):
    """Return the folder path (list of id/name dicts) that contains the given project."""
    log(LogLevel.INFO, Step.DEPLOY, f"Start get_project_folders — project_key={project_key}")
    print(f"[INFO] Start running function get_project_folders")
    print(f"[DEBUG] project_key = {project_key}")

    def find_project_path(folder_id, current_path):
        folder = client.get_project_folder(folder_id)
        current_path.append({"id": folder.id, "name": folder.name})
        projects = client.get_project_folder(folder_id).list_projects()
        for project in projects:
            if project.project_key == project_key:
                return current_path.copy()
        children = folder.list_child_folders()
        for child in children:
            result = find_project_path(child.id, current_path)
            if result:
                return result
        current_path.pop()
        return None

    result = find_project_path("ROOT", [])
    print(f"[DEBUG] Folder path found = {[f['name'] for f in result] if result else 'None'}")
    print(f"[INFO] End running function get_project_folders")
    log(LogLevel.DEBUG, Step.DEPLOY, f"Folder path found = {[f['name'] for f in result] if result else 'None'}")
    return result


def get_or_create_folder(dss_client, parent_folder, folder_name, folder_permissions):
    """Get an existing sub-folder or create it, then apply the given permissions."""
    log(LogLevel.INFO, Step.FOLDER, f"Start get_or_create_folder — folder_name={folder_name}")
    print(f"[INFO] Start running function get_or_create_folder")
    print(f"[DEBUG] folder_name = {folder_name}")

    print(f"[INFO] Executing step: listing child folders")
    child_folders = parent_folder.list_child_folders()
    folder_id = None
    for child_folder in child_folders:
        if child_folder.name == folder_name:
            folder_id = child_folder.id

    if folder_id is None:
        print(f"[INFO] Executing step: folder '{folder_name}' not found, creating it")
        folder = parent_folder.create_sub_folder(folder_name)
        print(f"[INFO] Folder '{folder_name}' created")
    else:
        print(f"[INFO] Executing step: folder '{folder_name}' already exists (id={folder_id}), retrieving it")
        folder = dss_client.get_project_folder(folder_id)

    print(f"[INFO] Executing step: applying permissions to folder '{folder_name}'")
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
    print(f"[INFO] Permissions saved for folder '{folder_name}'")
    print(f"[INFO] End running function get_or_create_folder")
    log(LogLevel.INFO, Step.FOLDER, f"End get_or_create_folder — folder_name={folder_name}")
    return folder


def create_group(dss_client, group_name, group_description=None, group_source_type='LOCAL'):
    """Create a group on the DSS node if it does not already exist."""
    log(LogLevel.INFO, Step.GROUP, f"Start create_group — group_name={group_name}")
    print(f"[INFO] Start running function create_group")
    print(f"[DEBUG] group_name = {group_name}, group_source_type = {group_source_type}")

    print(f"[INFO] Executing step: fetching existing groups list")
    groups = [g["name"] for g in dss_client.list_groups()]
    print(f"[DEBUG] Number of existing groups = {len(groups)}")

    if group_name not in groups:
        print(f"[INFO] Executing step: group not found, creating group '{group_name}'")
        dss_client.create_group(group_name, description=group_description, source_type=group_source_type)
        log(LogLevel.INFO, Step.GROUP, f"Group '{group_name}' created")
        print(f"[INFO] Group '{group_name}' created")
    else:
        print(f"[INFO] Group '{group_name}' already exists, skipping creation")

    print(f"[INFO] End running function create_group")


def extract_project_trigram(project_key):
    """Extract the trigram identifier from a standard project key."""
    log(LogLevel.INFO, Step.DEPLOY, f"Start extract_project_trigram — project_key={project_key}")
    print(f"[INFO] Start running function extract_project_trigram")
    print(f"[DEBUG] project_key = {project_key}")

    try:
        match = re.match(project_key_pattern, project_key)
        trigram = match.group(1)
        print(f"[DEBUG] trigram = {trigram}")
        print(f"[INFO] End running function extract_project_trigram")
        log(LogLevel.DEBUG, Step.DEPLOY, f"trigram = {trigram}")
        return trigram
    except Exception:
        log(LogLevel.WARNING, Step.DEPLOY, f"Could not extract trigram from project_key = {project_key}")
        print(f"[WARNING] Could not extract trigram from project_key = {project_key}")
        print(f"[INFO] End running function extract_project_trigram")
        return None


def get_last_version_bundle(bundles):
    """Return the bundle dict with the highest version number."""
    log(LogLevel.INFO, Step.BUNDLE, f"Start get_last_version_bundle — bundles count={len(bundles)}")
    print(f"[INFO] Start running function get_last_version_bundle")
    print(f"[DEBUG] Number of bundles to evaluate = {len(bundles)}")

    last_bundle = None
    last_version = 0
    for bundle in bundles:
        match = re.search(r'_v(\d+)', bundle['bundleId'])
        if match:
            version = int(match.group(1))
            if version > last_version:
                last_version = version
                last_bundle = bundle

    print(f"[DEBUG] Latest bundle = {last_bundle['bundleId'] if last_bundle else 'None'}, version = {last_version}")
    print(f"[INFO] End running function get_last_version_bundle")
    log(LogLevel.DEBUG, Step.BUNDLE, f"Latest bundle = {last_bundle['bundleId'] if last_bundle else 'None'}")
    return last_bundle


def get_specified_version_bundle(version, bundles):
    """Return the bundle matching the specified version number, or raise ValueError."""
    log(LogLevel.INFO, Step.BUNDLE, f"Start get_specified_version_bundle — version={version}")
    print(f"[INFO] Start running function get_specified_version_bundle")
    print(f"[DEBUG] Requested version = {version}, number of bundles = {len(bundles)}")

    match_bundle = None
    for bundle in bundles:
        match = re.search(rf'_v{version}', bundle['bundleId'])
        if match:
            match_bundle = bundle

    if not match_bundle:
        available_bundles = [b['bundleId'] for b in bundles]
        log(LogLevel.WARNING, Step.BUNDLE, f"Version '{version}' not found. Available: {available_bundles}")
        print(f"[WARNING] Specified version '{version}' not found. Available bundles: {', '.join(available_bundles)}")
        raise ValueError(
            f"The specified version '{version}' does not exist for the project. Available bundles are: "
            + ', '.join(available_bundles)
        )

    print(f"[DEBUG] Matching bundle found = {match_bundle['bundleId']}")
    print(f"[INFO] End running function get_specified_version_bundle")
    log(LogLevel.DEBUG, Step.BUNDLE, f"Matching bundle = {match_bundle['bundleId']}")
    return match_bundle


def get_connection_type(connection):
    """Determine the connection type from its naming pattern."""
    print(f"[INFO] Start running function get_connection_type")
    if re.search(r's3-cft-[a-zA-Z0-9_-]+-co[a-zA-Z0-9]+', connection):
        return 's3-cft'
    if re.search(r's3-[a-zA-Z0-9_-]+-co[a-zA-Z0-9]+', connection):
        return 's3-cos'
    if re.search(r'db-[a-zA-Z0-9_-]+-pg[a-zA-Z0-9]+', connection):
        return 'db-pg'
    log(LogLevel.WARNING, Step.DEPLOY, f"No connection type matched for: {connection}")
    print(f"[WARNING] No connection type matched for connection name provided: {connection}")
    print(f"[INFO] End running function get_connection_type")
    return None


def get_mapped_connections(source_connections, target_connections):
    """Build a list of source-to-target connection remapping dicts by matching connection types."""
    log(LogLevel.INFO, Step.DEPLOY, f"Start get_mapped_connections — source={len(source_connections)}, target={len(target_connections)}")
    print(f"[INFO] Start running function get_mapped_connections")
    print(f"[DEBUG] Number of source connections = {len(source_connections)}, target connections = {len(target_connections)}")

    connections = []
    for source in source_connections:
        source_type = get_connection_type(source)
        for target in target_connections:
            target_type = get_connection_type(target)
            if source_type and target_type and source_type == target_type:
                connections.append({"source": source, "target": target})
                print(f"[DEBUG] Connection mapped: {source} -> {target} (type={source_type})")
                break

    print(f"[DEBUG] Total connection mappings resolved = {len(connections)}")
    print(f"[INFO] End running function get_mapped_connections")
    log(LogLevel.DEBUG, Step.DEPLOY, f"Total connection mappings resolved = {len(connections)}")
    return connections


def get_activated_scenarios(project, infra_id):
    """Return a dict of scenario IDs that are tagged for activation on the given infra."""
    log(LogLevel.INFO, Step.DEPLOY, f"Start get_activated_scenarios — infra_id={infra_id}")
    print(f"[INFO] Start running function get_activated_scenarios")
    print(f"[DEBUG] infra_id = {infra_id}")

    print(f"[INFO] Executing step: listing scenarios in project")
    scenarios_list = project.list_scenarios(as_type="objects")
    scenarios_settings_list = [s.get_settings() for s in scenarios_list]
    scenarios_settings_raw_list = [s.get_raw() for s in scenarios_settings_list]

    activated_scenarios = [
        s["id"] for s in scenarios_settings_raw_list
        if f"Scenarios:{infra_id}_activated" in s["tags"]
    ]
    print(f"[DEBUG] Activated scenarios for infra '{infra_id}' = {activated_scenarios}")
    print(f"[INFO] End running function get_activated_scenarios")
    log(LogLevel.DEBUG, Step.DEPLOY, f"Activated scenarios for '{infra_id}' = {activated_scenarios}")
    return {scenario_id: True for scenario_id in activated_scenarios}


def create_or_update_deployment(dss_deployer_client, deployment_id, trg_project_key, infra_id, bundle_id,
                                remapping_global_connections, remapping_project_connections,
                                automation_project_folder_id, trg_project):
    """Create or update a project deployment on the deployer, then trigger an update."""
    log(LogLevel.INFO, Step.DEPLOY, f"Start create_or_update_deployment — deployment_id={deployment_id}, infra_id={infra_id}, bundle_id={bundle_id}")
    print(f"[INFO] Start running function create_or_update_deployment")
    print(f"[DEBUG] deployment_id = {deployment_id}, trg_project_key = {trg_project_key}")
    print(f"[DEBUG] infra_id = {infra_id}, bundle_id = {bundle_id}")
    print(f"[DEBUG] automation_project_folder_id = {automation_project_folder_id}")

    print(f"[INFO] Executing step: listing all deployments from project deployer")
    project_deployer = dss_deployer_client.get_projectdeployer()
    deployment_list = project_deployer.list_deployments(as_objects=True)
    print(f"[DEBUG] Total deployments found = {len(deployment_list)}")

    print(f"[INFO] Executing step: searching for existing deployment matching id and infra")
    deployment = next(
        (d for d in deployment_list
         if d.get_settings().get_raw()["id"] == deployment_id
         and d.get_settings().get_raw()["infraId"] == infra_id),
        None
    )

    if not deployment:
        print(f"[INFO] No existing deployment found, creating new deployment '{deployment_id}'")
        deployment = project_deployer.create_deployment(deployment_id, trg_project_key, infra_id, bundle_id,
                                                        deployed_project_key=trg_project_key)
        log(LogLevel.INFO, Step.DEPLOY, f"New deployment created: {deployment_id}")
        print(f"[INFO] New deployment created: {deployment_id}")
    else:
        print(f"[INFO] Existing deployment found: {deployment_id}")

    print(f"[INFO] Executing step: updating deployment settings")
    deployment_settings = deployment.get_settings()
    deployment_settings_raw = deployment_settings.get_raw()
    deployment_settings_raw["bundleId"] = bundle_id
    deployment_settings_raw["bundleContainerSettings"]["remapping"]["connections"] = (
        remapping_global_connections + remapping_project_connections
    )
    deployment_settings_raw["projectFolderId"] = automation_project_folder_id

    print(f"[INFO] Executing step: resolving activated scenarios for infra '{infra_id}'")
    deployment_settings_raw["scenariosToActivate"] = get_activated_scenarios(trg_project, infra_id)

    deployment_settings.save()
    print(f"[INFO] Deployment settings saved for '{deployment_id}'")

    print(f"[INFO] Executing step: triggering deployment update and waiting for result")
    update = deployment.start_update()
    update.wait_for_result()

    log(LogLevel.INFO, Step.DEPLOY, f"Deployment update completed: {deployment_id}")
    print(f"[INFO] Deployment update completed for '{deployment_id}'")
    print(f"[INFO] End running function create_or_update_deployment")
    return deployment


def update_automation_project(dss_client, project_key, project_permissions):
    """Remove git remote, ensure master branch exists, and apply project permissions."""
    log(LogLevel.INFO, Step.DEPLOY, f"Start update_automation_project — project_key={project_key}")
    print(f"[INFO] Start running function update_automation_project")
    print(f"[DEBUG] project_key = {project_key}")

    print(f"[INFO] Executing step: retrieving automation project")
    project = dss_client.get_project(project_key)
    project_git = project.get_project_git()

    print(f"[INFO] Executing step: cleaning up git remote if present")
    if project_git.get_remote():
        project_git.remove_remote()
        print(f"[INFO] Git remote removed for project {project_key}")

    print(f"[INFO] Executing step: ensuring master branch exists")
    if "master" not in project_git.list_branches(remote=False):
        project_git.create_branch("master")
        print(f"[INFO] Branch 'master' created for project {project_key}")
    else:
        print(f"[INFO] Branch 'master' already exists for project {project_key}")

    print(f"[INFO] Executing step: applying project permissions")
    permissions = project.get_permissions()
    for perm in project_permissions:
        permissions["permissions"].append(perm)
    project.set_permissions(permissions)
    print(f"[DEBUG] Number of permission entries applied = {len(project_permissions)}")

    log(LogLevel.INFO, Step.DEPLOY, f"End update_automation_project — project_key={project_key}")
    print(f"[INFO] End running function update_automation_project")


class UseCaseIndusDeployer:
    def __init__(self, design_rd_host, design_rd_user_api_key, deployer_host, deployer_api_key,
                 automation_host, automation_api_key, project_key, infra_id, version, deploy_config):
        """Initialize DSS clients and load project configuration from config dict."""
        log(LogLevel.INFO, Step.INIT, f"Start UseCaseIndusDeployer.__init__ — project_key={project_key}, infra_id={infra_id}")
        print(f"[INFO] Start running function UseCaseIndusDeployer.__init__")
        print(f"[DEBUG] project_key = {project_key}, infra_id = {infra_id}")

        print(f"[INFO] Executing step: connecting to design RD DSS node")
        self.client = dataikuapi.DSSClient(design_rd_host, design_rd_user_api_key, insecure_tls=True)

        print(f"[INFO] Executing step: connecting to deployer DSS node")
        self.deployer_client = dataikuapi.DSSClient(deployer_host, deployer_api_key, insecure_tls=True)

        print(f"[INFO] Executing step: connecting to automation DSS node")
        self.automation_client = dataikuapi.DSSClient(automation_host, automation_api_key, insecure_tls=True)

        self.project_key = project_key
        self.trigram = extract_project_trigram(project_key)
        print(f"[DEBUG] trigram = {self.trigram}")

        self.infra_id = infra_id
        self.version = version
        self.is_data_source_project = False

        # Load permissions and group names from config, resolving {use_case_trigram} placeholders
        self.use_case_groups = format_nested_structure(
            deploy_config["use_case_groups"],
            use_case_trigram=self.trigram
        )
        self.folder_permissions = deploy_config["folder_permissions"]
        self.use_case_project_permissions = format_nested_structure(
            deploy_config["use_case_project_permissions"],
            use_case_trigram=self.trigram
        )
        self.data_source_project_permissions = deploy_config["data_source_project_permissions"]

        print(f"[DEBUG] version = '{self.version}' (empty means use latest)")
        log(LogLevel.INFO, Step.INIT, f"End UseCaseIndusDeployer.__init__ — trigram={self.trigram}")
        print(f"[INFO] End running function UseCaseIndusDeployer.__init__")

    def run(self):
        """Execute the full deployment workflow: folder setup, connection remapping, bundle deploy, permissions."""
        log(LogLevel.INFO, Step.DEPLOY, f"Start UseCaseIndusDeployer.run — project_key={self.project_key}")
        print(f"[INFO] Start running function Run")
        print(f"[INFO] Start processing project: {self.project_key}")

        data_source_folder_name = "01 Data Source"

        # Step 1: Detect if project is a data source project and adjust permissions accordingly
        print(f"[INFO] Executing step: resolving project folder path on design RD node")
        project_folders = get_project_folders(self.client, self.project_key)
        if any(pf['name'] == data_source_folder_name for pf in project_folders):
            self.is_data_source_project = True
            project_permissions = self.data_source_project_permissions
            log(LogLevel.INFO, Step.DEPLOY, f"Project '{self.project_key}' identified as data source project")
        else:
            project_permissions = self.use_case_project_permissions
            print(f"[INFO] Project is a standard use case indus project (not data source)")

        # Step 2: Recreate the same folder hierarchy on the automation node
        print(f"[INFO] Executing step: retrieving automation root project folder")
        automation_root_project_folder = self.automation_client.get_root_project_folder()

        folder_hierarchy = [
            folder['name'] for folder in project_folders
            if folder['name'] is not None and folder['id'] != 'ROOT'
        ]
        print(f"[DEBUG] Folder hierarchy to replicate on automation = {folder_hierarchy}")

        automation_project_folder = create_folder_hierarchy(
            self.automation_client,
            automation_root_project_folder,
            folder_hierarchy,
            self.folder_permissions
        )
        print(f"[DEBUG] automation_project_folder.id = {automation_project_folder.id}")

        # Step 3: Build connection remapping between design and automation nodes
        client_connections = self.client.list_connections_names("all")
        automation_client_connections = self.automation_client.list_connections_names("all")

        remapping_project_connections = []
        if not self.is_data_source_project:
            project_connections = [pc for pc in client_connections if self.trigram.lower() in pc]
            automation_project_connections = [apc for apc in automation_client_connections
                                              if self.trigram.lower() in apc]
            remapping_project_connections = get_mapped_connections(project_connections,
                                                                   automation_project_connections)

            print(f"[INFO] Executing step: creating use-case groups on automation node")
            for group in self.use_case_groups.values():
                create_group(self.automation_client, group,
                             group_description=f"{self.trigram} : Use Case Group",
                             group_source_type='LOCAL')

        print(f"[INFO] Project groups done on automation node")

        # Step 4: Resolve global connection mapping from design node variables
        global_connection_mapping = self.client.get_global_variables()
        remapping_global_connections = []
        for global_connection in global_connection_mapping['global_connection_mapping'].values():
            if global_connection[self.infra_id] and global_connection[self.infra_id].strip() != "":
                remapping_global_connections.append({
                    "source": global_connection['design_rd'],
                    "target": global_connection[self.infra_id]
                })

        # Step 5: Resolve bundle to deploy
        print(f"[INFO] Executing step: retrieving exported bundles for project {self.project_key}")
        trg_project = self.client.get_project(self.project_key)
        trg_bundles = trg_project.list_exported_bundles()
        print(f"[DEBUG] Number of exported bundles = {len(trg_bundles.get('bundles', []))}")

        if self.version:
            print(f"[INFO] Executing step: looking for specified bundle version '{self.version}'")
            trg_bundle = get_specified_version_bundle(self.version, trg_bundles["bundles"])
        else:
            print(f"[INFO] Executing step: no version specified, using latest bundle")
            trg_bundle = get_last_version_bundle(trg_bundles["bundles"])

        deployment_id = f"{self.project_key}_{self.infra_id}"
        bundle_id = trg_bundle['bundleId']
        print(f"[DEBUG] deployment_id = {deployment_id}")
        print(f"[DEBUG] bundle_id = {bundle_id}")

        # Step 6: Create or update the deployment
        print(f"[INFO] Executing step: creating or updating deployment '{deployment_id}' on infra '{self.infra_id}'")
        create_or_update_deployment(
            self.deployer_client, deployment_id, self.project_key, self.infra_id,
            bundle_id, remapping_global_connections, remapping_project_connections,
            automation_project_folder.id, trg_project
        )
        print(f"[INFO] Deployment created or updated for project: {self.project_key}")

        # Step 7: Update automation project permissions
        print(f"[INFO] Executing step: updating automation project permissions for infra '{self.infra_id}'")
        update_automation_project(self.automation_client, self.project_key,
                                  project_permissions[self.infra_id])
        print(f"[INFO] Automation project updated for: {self.project_key}")

        log(LogLevel.INFO, Step.DEPLOY, f"End UseCaseIndusDeployer.run — project_key={self.project_key}")
        print(f"[INFO] End processing project: {self.project_key}")
        print(f"[INFO] End running function Run")
