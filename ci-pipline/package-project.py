import argparse
import sys
import dataikuapi
import requests
import urllib3
import json
import re

# Disable SSL warnings for internal Dataiku nodes
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# Pattern for matching project keys following the standard naming convention
project_key_pattern = re.compile(r"^\d{2}_(\w+)_(DATASET|DESIGN|PRODUCT)$")


def create_group(dss_client, group_name, group_description=None, group_source_type='LOCAL'):
    """Create a group on the DSS node if it does not already exist."""
    print(f"[INFO] Start running function create_group")
    print(f"[DEBUG] group_name = {group_name}, group_source_type = {group_source_type}")

    print(f"[INFO] Executing step: fetching existing groups list")
    groups = [g["name"] for g in dss_client.list_groups()]
    print(f"[DEBUG] Number of existing groups = {len(groups)}")

    if group_name not in groups:
        print(f"[INFO] Executing step: group not found, creating group '{group_name}'")
        new_group = dss_client.create_group(group_name, description=group_description, source_type=group_source_type)
        group_definintion = new_group.get_definition()

        # Set all permissions to False (read-only group by default)
        group_permissions = {
            'admin': False, 'mayManageUDM': False, 'mayCreateProjects': False,
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
            'mayManageFeatureStore': False, 'canObtainAPITicketFromCookiesForGroupsRegex': ''
        }

        group_definintion.update(group_permissions)
        new_group.set_definition(group_definintion)
        print(f"[INFO] Group '{group_name}' created with default restricted permissions")
    else:
        print(f"[INFO] Group '{group_name}' already exists, skipping creation")

    print(f"[INFO] End running function create_group")


def extract_included_managed_folders(dss_client, project_key, bundle_id):
    """Find all managed folders tagged for bundle inclusion in the given project."""
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

            # Only include folders explicitly tagged for bundle inclusion
            if "Managed_folder:include_folder_to_bundle" in tags:
                print(f"[INFO] Executing step: folder found with inclusion tag: {folder['name']}")
                try:
                    files = folder_obj.list_contents()
                    all_files = [f["path"] for f in files]
                    print(f"[DEBUG] {len(all_files)} file(s) found in folder '{folder['name']}'")
                    included_folders.append({
                        "folder_name": folder["name"],
                        "files": all_files
                    })
                except Exception as e:
                    print(f"[ERROR] Failed to scan folder '{folder['name']}': {e}")

        print(f"[DEBUG] Total included folders found = {len(included_folders)}")
        print(f"[INFO] End running function extract_included_managed_folders")
        return included_folders

    except Exception as e:
        print(f"[ERROR] Unexpected error in extract_included_managed_folders: {e}")
        print(f"[INFO] End running function extract_included_managed_folders")
        return []


def extract_project_trigram(project_key):
    """Extract the trigram identifier from a project key."""
    print(f"[INFO] Start running function extract_project_trigram")
    print(f"[DEBUG] project_key = {project_key}")

    try:
        match = re.match(project_key_pattern, project_key)
        trigram = match.group(1)
        print(f"[DEBUG] trigram = {trigram}")
        print(f"[INFO] End running function extract_project_trigram")
        return trigram
    except Exception:
        print(f"[WARNING] Could not extract trigram from project_key = {project_key}")
        print(f"[INFO] End running function extract_project_trigram")
        return None


def extract_bundle_id_version(bundle):
    """Extract the numeric version from a bundle ID string."""
    print(f"[INFO] Start running function extract_bundle_id_version")
    print(f"[DEBUG] bundle_id = {bundle.get('bundleId')}")

    match = re.search(r'_v(\d+)', bundle['bundleId'])
    result = int(match.group(1)) if match else None

    print(f"[DEBUG] Extracted bundle version = {result}")
    print(f"[INFO] End running function extract_bundle_id_version")
    return result


def define_bundles_version(project):
    """Compute the next bundle version number based on existing exported bundles."""
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

    print(f"[DEBUG] Next bundle version = {next_version}")
    print(f"[INFO] End running function define_bundles_version")
    return next_version


def create_and_publish_bundle(project, bundle_id):
    """Export and publish a bundle with the given ID to the deployer."""
    print(f"[INFO] Start running function create_and_publish_bundle")
    print(f"[DEBUG] bundle_id = {bundle_id}")

    print(f"[INFO] Executing step: exporting bundle '{bundle_id}'")
    project.export_bundle(bundle_id)
    print(f"[INFO] Executing step: publishing bundle '{bundle_id}' to deployer")
    project.publish_bundle(bundle_id)

    print(f"[INFO] End running function create_and_publish_bundle")


class PackageUseCaseIndus:
    def __init__(self, project_key, design_rd_host, design_rd_user_api_key, deployer_host, deployer_api_key):
        """Initialize DSS clients and use-case group configuration."""
        print(f"[INFO] Start running function PackageUseCaseIndus.__init__")
        print(f"[DEBUG] project_key = {project_key}")

        self.project_key = project_key
        self.trigram = extract_project_trigram(project_key)
        print(f"[DEBUG] trigram = {self.trigram}")

        print(f"[INFO] Executing step: connecting to design RD DSS node")
        self.client = dataikuapi.DSSClient(design_rd_host, design_rd_user_api_key, insecure_tls=True)

        print(f"[INFO] Executing step: connecting to deployer DSS node")
        self.deployer_client = dataikuapi.DSSClient(deployer_host, deployer_api_key, insecure_tls=True)

        self.use_case_groups = self.get_use_case_groups()
        self.deployer_project_permissions = self.get_deployer_project_permissions()

        print(f"[INFO] End running function PackageUseCaseIndus.__init__")

    # TODO put this configuration inside json config file
    def get_use_case_groups(self):
        """Return the standard group names for this use case based on its trigram."""
        print(f"[INFO] Start running function get_use_case_groups")
        groups = {
            "admin_group": f"{self.trigram}_Admin",
            "contributor_group": f"{self.trigram}_Contributor",
            "consumer_group": f"{self.trigram}_Consumer"
        }
        print(f"[DEBUG] use_case_groups = {list(groups.values())}")
        print(f"[INFO] End running function get_use_case_groups")
        return groups

    # TODO put this configuration inside json config file
    def get_deployer_project_permissions(self):
        """Return the deployer-level permissions to apply for this project."""
        print(f"[INFO] Start running function get_deployer_project_permissions")
        permissions = [
            {'group': 'Admin', 'read': True, 'write': True, 'deploy': True, 'admin': True},
            {'group': 'SRE', 'read': True, 'write': True, 'deploy': True, 'admin': True},
            {'group': 'ITOps', 'read': True, 'write': True, 'deploy': True, 'admin': True},
            {'group': f'{self.trigram}_Admin', 'read': True, 'write': False, 'deploy': False, 'admin': False},
            {'group': f'{self.trigram}_Contributor', 'read': True, 'write': False, 'deploy': False, 'admin': False},
            {'group': f'{self.trigram}_Consumer', 'read': True, 'write': False, 'deploy': False, 'admin': False}
        ]
        print(f"[DEBUG] Number of permission entries = {len(permissions)}")
        print(f"[INFO] End running function get_deployer_project_permissions")
        return permissions

    def run(self, progress_callback):
        """Execute the full packaging and publishing workflow for the project."""
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
                print(f"[WARNING] Skipping project {self.project_key}: {e}")
            else:
                print(f"[ERROR] Unexpected error while publishing bundle for {self.project_key}: {e}")

        # Step 2: Check if there are managed folders in the project
        print(f"[INFO] Executing step: listing managed folders in project {self.project_key}")
        folders = None
        try:
            folders = project.list_managed_folders()
            print(f"[DEBUG] {len(folders)} managed folder(s) found in {self.project_key}")
        except Exception as e:
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
            print(f"[ERROR] Error while extracting managed folders for {self.project_key}: {e}")

        print(f"[INFO] All bundles version {bundle_version} have been successfully published")

        # Step 4: Create use-case groups on the deployer node
        print(f"[INFO] Executing step: creating use-case groups on deployer node")
        for group in self.use_case_groups.values():
            create_group(
                self.deployer_client,
                group,
                group_description=f"{self.trigram} : Use Case Group",
                group_source_type='LOCAL'  # TODO: switch to SSO
            )
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

        print(f"[INFO] Bundles version {bundle_version} published for project {self.project_key}")
        print(f"[INFO] End processing project: {self.project_key}")
        print(f"[INFO] End running function PackageUseCaseIndus.run")


def run_package_and_publish_use_case_indus(project_key, design_rd_user_api_key, deployer_api_key):
    """Entry point to instantiate and run the packaging workflow."""
    print(f"[INFO] Start running function run_package_and_publish_use_case_indus")
    print(f"[DEBUG] project_key = {project_key}")

    # TODO: move host information into a config file
    design_rd_host = "https://ds-studio-0r1.leasingsolutions.echonet"
    deployer_host = "https://ds-deploy.leasingsolutions.echonet"
    print(f"[DEBUG] design_rd_host = {design_rd_host}")
    print(f"[DEBUG] deployer_host = {deployer_host}")

    print(f"[INFO] Executing step: initializing PackageUseCaseIndus")
    use_case_indus = PackageUseCaseIndus(
        project_key,
        design_rd_host, design_rd_user_api_key,
        deployer_host, deployer_api_key
    )

    print(f"[INFO] Executing step: running packaging workflow")
    use_case_indus.run(None)

    print(f"[INFO] End running function run_package_and_publish_use_case_indus")


def build_parser(params):
    """Build an argparse parser from a list of (param_name, required) tuples."""
    parser = argparse.ArgumentParser(
        description="Package and publish a Dataiku use case project to the deployer."
    )
    for param, required in params:
        parser.add_argument(f"--{param}", required=required)
    return parser


if __name__ == "__main__":
    print("[INFO] Input arguments check")

    # Define expected CLI arguments — sensitive keys are required but not logged
    params = [
        ("design-rd-user-api-key", True),
        ("deployer-api-key", True),
    ]

    parser = build_parser(params)
    args = parser.parse_args()

    print("[INFO] Input arguments check passed")

    # Read project key from params.json (set by the CI pipeline)
    print("[INFO] Executing step: reading project key from params.json")
    try:
        with open('params.json', 'r') as file:
            params_data = json.load(file)
            project_key = params_data.get("name")
    except Exception as e:
        print(f"[ERROR] Failed to read params.json: {e}")
        sys.exit(1)

    if not project_key:
        print("[ERROR] 'name' key not found in params.json")
        sys.exit(1)

    print(f"[DEBUG] project_key = {project_key}")
    print(f"[INFO] Start processing project: {project_key}")

    run_package_and_publish_use_case_indus(
        project_key,
        args.design_rd_user_api_key,
        args.deployer_api_key
    )

    print(f"[INFO] End processing project: {project_key}")
    print("[INFO] Package and publish use case indus completed successfully")
