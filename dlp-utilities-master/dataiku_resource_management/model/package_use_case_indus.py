import re
import dataikuapi
import requests
import urllib3

from core.logger import log, LogLevel, Step
from utils.helpers import format_nested_structure

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

project_key_pattern = re.compile(r"^\d{2}_(\w+)_(DATASET|DESIGN|PRODUCT)$")


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
        new_group = dss_client.create_group(group_name, description=group_description, source_type=group_source_type)
        group_definition = new_group.get_definition()

        group_permissions = {
            'admin': False, 'mayManageUDM': False, 'mayCreateProjects': False,
            'mayCreateProjectsFromMacros': False, 'mayCreateProjectsFromTemplates': False,
            'mayCreateProjectsFromDataikuApps': False, 'mayWriteUnsafeCode': False,
            'mayWriteSafeCode': False, 'mayCreateAuthenticatedConnections': False,
            'mayCreateCodeEnvs': False, 'mayCreateClusters': False,
            'mayCreateCodeStudioTemplates': False, 'mayDevelopPlugins': False,
            'mayEditLibFolders': False, 'mayManageCodeEnvs': False,
            'mayManageClusters': False, 'mayManageCodeStudioTemplates': False,
            'mayViewIndexedHiveConnections': False, 'mayCreatePublishedAPIServices': False,
            'mayCreatePublishedProjects': False, 'mayWriteInRootProjectFolder': False,
            'mayCreateActiveWebContent': False, 'mayCreateWorkspaces': False,
            'mayShareToWorkspaces': False, 'mayCreateDataCollections': False,
            'mayPublishToDataCollections': False, 'mayManageFeatureStore': False,
            'canObtainAPITicketFromCookiesForGroupsRegex': ''
        }
        group_definition.update(group_permissions)
        new_group.set_definition(group_definition)
        log(LogLevel.INFO, Step.GROUP, f"Group '{group_name}' created")
        print(f"[INFO] Group '{group_name}' created")
    else:
        print(f"[INFO] Group '{group_name}' already exists, skipping creation")

    print(f"[INFO] End running function create_group")


def extract_project_trigram(project_key):
    """Extract the trigram identifier from a project key."""
    log(LogLevel.INFO, Step.PACKAGE, f"Start extract_project_trigram — project_key={project_key}")
    print(f"[INFO] Start running function extract_project_trigram")
    print(f"[DEBUG] project_key = {project_key}")

    try:
        match = re.match(project_key_pattern, project_key)
        trigram = match.group(1)
        print(f"[DEBUG] trigram = {trigram}")
        print(f"[INFO] End running function extract_project_trigram")
        log(LogLevel.DEBUG, Step.PACKAGE, f"trigram = {trigram}")
        return trigram
    except Exception:
        log(LogLevel.WARNING, Step.PACKAGE, f"Could not extract trigram from project_key = {project_key}")
        print(f"[WARNING] Could not extract trigram from project_key = {project_key}")
        print(f"[INFO] End running function extract_project_trigram")
        return None


def extract_bundle_id_version(bundle):
    """Extract the numeric version from a bundle ID string."""
    log(LogLevel.INFO, Step.BUNDLE, f"Start extract_bundle_id_version — bundle_id={bundle.get('bundleId')}")
    print(f"[INFO] Start running function extract_bundle_id_version")
    print(f"[DEBUG] bundle_id = {bundle.get('bundleId')}")

    match = re.search(r'_v(\d+)', bundle['bundleId'])
    result = int(match.group(1)) if match else None

    print(f"[DEBUG] Extracted bundle version = {result}")
    print(f"[INFO] End running function extract_bundle_id_version")
    log(LogLevel.DEBUG, Step.BUNDLE, f"Extracted bundle version = {result}")
    return result


def define_bundles_version(project):
    """Compute the next bundle version number based on existing exported bundles."""
    log(LogLevel.INFO, Step.BUNDLE, "Start define_bundles_version")
    print(f"[INFO] Start running function define_bundles_version")

    print(f"[INFO] Executing step: listing exported bundles")
    proj_bundles = project.list_exported_bundles()
    bundle_versions = [
        extract_bundle_id_version(bundle)
        for bundle in proj_bundles.get("bundles", [])
        if extract_bundle_id_version(bundle) is not None
    ]
    print(f"[DEBUG] Existing bundle versions = {bundle_versions}")

    max_bundle_version = max(bundle_versions, default=0)
    next_version = max_bundle_version + 1

    log(LogLevel.DEBUG, Step.BUNDLE, f"Next bundle version = {next_version}")
    print(f"[DEBUG] Next bundle version = {next_version}")
    print(f"[INFO] End running function define_bundles_version")
    return next_version


def create_and_publish_bundle(project, bundle_id):
    """Export and publish a bundle with the given ID to the deployer."""
    log(LogLevel.INFO, Step.BUNDLE, f"Start create_and_publish_bundle — bundle_id={bundle_id}")
    print(f"[INFO] Start running function create_and_publish_bundle")
    print(f"[DEBUG] bundle_id = {bundle_id}")

    print(f"[INFO] Executing step: exporting bundle '{bundle_id}'")
    project.export_bundle(bundle_id)
    print(f"[INFO] Executing step: publishing bundle '{bundle_id}' to deployer")
    project.publish_bundle(bundle_id)

    log(LogLevel.INFO, Step.BUNDLE, f"Bundle '{bundle_id}' exported and published")
    print(f"[INFO] End running function create_and_publish_bundle")


def extract_included_managed_folders(dss_client, project_key, bundle_id):
    """Find all managed folders tagged for bundle inclusion in the given project."""
    log(LogLevel.INFO, Step.PACKAGE, f"Start extract_included_managed_folders — project_key={project_key}, bundle_id={bundle_id}")
    print(f"[INFO] Start running function extract_included_managed_folders")
    print(f"[DEBUG] project_key = {project_key}, bundle_id = {bundle_id}")

    project = dss_client.get_project(project_key)
    managed_folders = project.list_managed_folders()
    print(f"[DEBUG] Total managed folders in project = {len(managed_folders)}")

    try:
        print(f"[INFO] Executing step: searching for managed folders tagged for bundle '{bundle_id}'")
        included_folders = []

        for folder in managed_folders:
            folder_obj = dss_client.get_managed_folder(folder["name"])
            tags = folder_obj.get_definition()["tags"]

            if "Managed_folder:include_folder_to_bundle" in tags:
                print(f"[INFO] Executing step: folder found with inclusion tag: {folder['name']}")
                try:
                    files = folder_obj.list_contents()
                    all_files = [f["path"] for f in files]
                    print(f"[DEBUG] {len(all_files)} file(s) found in folder '{folder['name']}'")
                    included_folders.append({"folder_name": folder["name"], "files": all_files})
                except Exception as e:
                    log(LogLevel.ERROR, Step.PACKAGE, f"Failed to scan folder '{folder['name']}': {e}")
                    print(f"[ERROR] Failed to scan folder '{folder['name']}': {e}")

        print(f"[DEBUG] Total included folders found = {len(included_folders)}")
        print(f"[INFO] End running function extract_included_managed_folders")
        log(LogLevel.DEBUG, Step.PACKAGE, f"Total included folders = {len(included_folders)}")
        return included_folders

    except Exception as e:
        log(LogLevel.ERROR, Step.PACKAGE, f"Unexpected error in extract_included_managed_folders: {e}")
        print(f"[ERROR] Unexpected error in extract_included_managed_folders: {e}")
        print(f"[INFO] End running function extract_included_managed_folders")
        return []


class PackageUseCaseIndus:
    def __init__(self, project_key, design_rd_host, design_rd_user_api_key,
                 deployer_host, deployer_api_key, package_config):
        """Initialize DSS clients and use-case group configuration from config dict."""
        log(LogLevel.INFO, Step.INIT, f"Start PackageUseCaseIndus.__init__ — project_key={project_key}")
        print(f"[INFO] Start running function PackageUseCaseIndus init")
        print(f"[DEBUG] project_key = {project_key}")

        self.project_key = project_key
        self.trigram = extract_project_trigram(project_key)
        print(f"[DEBUG] trigram = {self.trigram}")

        print(f"[INFO] Executing step: connecting to design RD DSS node")
        self.client = dataikuapi.DSSClient(design_rd_host, design_rd_user_api_key, insecure_tls=True)

        print(f"[INFO] Executing step: connecting to deployer DSS node")
        self.deployer_client = dataikuapi.DSSClient(deployer_host, deployer_api_key, insecure_tls=True)

        # Load group names and permissions from config, resolving {use_case_trigram} placeholders
        self.use_case_groups = format_nested_structure(
            package_config["use_case_groups"],
            use_case_trigram=self.trigram
        )
        self.deployer_project_permissions = format_nested_structure(
            package_config["deployer_project_permissions"],
            use_case_trigram=self.trigram
        )

        log(LogLevel.INFO, Step.INIT, f"End PackageUseCaseIndus.__init__ — trigram={self.trigram}")
        print(f"[INFO] End running function PackageUseCaseIndus init")

    def run(self):
        """Execute the full packaging and publishing workflow for the project."""
        log(LogLevel.INFO, Step.PACKAGE, f"Start PackageUseCaseIndus.run — project_key={self.project_key}")
        print(f"[INFO] Start running function PackageUseCaseIndus.run")
        print(f"[INFO] Start processing project: {self.project_key}")

        print(f"[INFO] Executing step: retrieving project from DSS")
        project = self.client.get_project(self.project_key)

        print(f"[INFO] Executing step: computing next bundle version")
        bundle_version = define_bundles_version(project)
        new_bundle_name = f"{self.project_key}_v{bundle_version}"
        print(f"[DEBUG] new_bundle_name = {new_bundle_name}")

        # Step 1: Attempt to create and publish the bundle
        print(f"[INFO] Executing step: creating and publishing bundle '{new_bundle_name}'")
        try:
            create_and_publish_bundle(project, new_bundle_name)
            print(f"[INFO] Bundle '{new_bundle_name}' successfully published for project {self.project_key}")
        except Exception as e:
            if "cannot export managed folder" in str(e):
                log(LogLevel.WARNING, Step.PACKAGE, f"Skipping {self.project_key}: managed folder cannot be exported")
                print(f"[WARNING] Skipping project {self.project_key} because managed folder cannot be exported: {e}")
            else:
                log(LogLevel.ERROR, Step.PACKAGE, f"Unexpected error while publishing bundle for {self.project_key}: {e}")
                print(f"[ERROR] Unexpected error while publishing bundle for {self.project_key}: {e}")

        # Step 2: Check if there are managed folders in the project
        print(f"[INFO] Executing step: listing managed folders in project {self.project_key}")
        folders = None
        try:
            folders = project.list_managed_folders()
            print(f"[DEBUG] {len(folders)} managed folder(s) found in {self.project_key}")
        except Exception as e:
            log(LogLevel.ERROR, Step.PACKAGE, f"Failed to list managed folders for {self.project_key}: {e}")
            print(f"[ERROR] Failed to list managed folders for {self.project_key}: {e}")

        if not folders:
            print(f"[INFO] No managed folder found in {self.project_key}")

        # Step 3: Extract managed folders included in the bundle
        print(f"[INFO] Executing step: extracting managed folders included in bundle '{new_bundle_name}'")
        try:
            included_folders = extract_included_managed_folders(
                dss_client=self.client,
                project_key=self.project_key,
                bundle_id=new_bundle_name
            )
            print(f"[DEBUG] Included folders from '{new_bundle_name}': {included_folders}")
        except Exception as e:
            log(LogLevel.ERROR, Step.PACKAGE, f"Error extracting managed folders for {self.project_key}: {e}")
            print(f"[ERROR] Error while extracting managed folders for {self.project_key}: {e}")

        print(f"[INFO] All bundles version {bundle_version} have been successfully published")

        # Step 4: Create use-case groups on the deployer node
        print(f"[INFO] Executing step: creating use-case groups on deployer node")
        for group in self.use_case_groups.values():
            create_group(self.deployer_client, group,
                         group_description=f"{self.trigram} : Use Case Group",
                         group_source_type='LOCAL')
        print(f"[INFO] Use-case groups processed on deployer")

        # Step 5: Update deployer project permissions
        print(f"[INFO] Executing step: updating deployer project settings for {self.project_key}")
        project_deployer = self.deployer_client.get_projectdeployer()
        deployer_project = project_deployer.get_project(self.project_key)
        deployer_project_settings = deployer_project.get_settings()
        deployer_project_settings_raw = deployer_project_settings.get_raw()
        deployer_project_settings_raw['permissions'] = self.deployer_project_permissions
        deployer_project_settings_raw['owner'] = 'admin'
        deployer_project_settings.save()
        print(f"[INFO] Deployer project settings saved for {self.project_key}")

        log(LogLevel.INFO, Step.PACKAGE, f"End PackageUseCaseIndus.run — project_key={self.project_key}")
        print(f"[INFO] Bundles version {bundle_version} published for project {self.project_key}")
        print(f"[INFO] End processing project: {self.project_key}")
        print(f"[INFO] End running function PackageUseCaseIndus.run")
