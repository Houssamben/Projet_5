import re
import dataikuapi


def extract_ApiId_version(api_version, stage=None):
    """Extract the numeric version from an API version ID string."""
    print(f"[INFO] Start running function extract_ApiId_version")
    print(f"[DEBUG] api_version id = {api_version.get('id')}, stage = {stage}")

    if stage is None:
        pattern = rf'v(\d+)_(\w+)'
    else:
        pattern = rf'v(\d+)_{stage}'

    match = re.search(pattern, api_version['id'])
    result = int(match.group(1)) if match else None

    print(f"[DEBUG] Extracted version number = {result}")
    print(f"[INFO] End running function extract_ApiId_version")
    return result


def get_connection_type(connection):
    """Determine the type of a connection based on naming conventions."""
    print(f"[INFO] Start running function get_connection_type")

    if re.search(r's3-cft-[a-zA-Z0-9_-]+-co[a-zA-Z0-9]+', connection):
        print(f"[DEBUG] Connection type identified = s3-cft")
        print(f"[INFO] End running function get_connection_type")
        return 's3-cft'
    if re.search(r's3-[a-zA-Z0-9_-]+-co[a-zA-Z0-9]+', connection):
        print(f"[DEBUG] Connection type identified = s3-cos")
        print(f"[INFO] End running function get_connection_type")
        return 's3-cos'
    if re.search(r'db-[a-zA-Z0-9_-]+-pg[a-zA-Z0-9]+', connection):  # to be checked !!!!
        print(f"[DEBUG] Connection type identified = db-pg")
        print(f"[INFO] End running function get_connection_type")
        return 'db-pg'

    print(f"[WARNING] No connection type matched for connection name provided")
    print(f"[INFO] End running function get_connection_type")
    return None


def update_connection(data, endpoint_id, connection_name):
    """Update the connection name for a specific endpoint in the API service settings."""
    print(f"[INFO] Start running function update_connection")
    print(f"[DEBUG] endpoint_id = {endpoint_id}, connection_name = {connection_name}")

    for endpoint in data.get('endpoints', []):
        if endpoint['id'] == endpoint_id:
            print(f"[INFO] Executing step: endpoint found, updating connection")
            endpoint['connection'] = connection_name
            break

    print(f"[INFO] End running function update_connection")
    return data


def extract_project_trigram(project_key):
    project_key_pattern = re.compile("^\d{2}_(\w+)_(DATASET|DESIGN|PRODUCT)$")

    """Extract the 3-letter trigram from a project key matching the standard naming convention."""
    print(f"[INFO] Start running function extract_project_trigram")
    print(f"[DEBUG] project_key = {project_key}")

    try:
        match = re.match(project_key_pattern, project_key)
        trigram = match.group(1)
        print(f"[DEBUG] Extracted trigram = {trigram}")
        print(f"[INFO] End running function extract_project_trigram")
        return trigram
    except Exception:
        print(f"[WARNING] Could not extract trigram from project_key = {project_key}")
        print(f"[INFO] End running function extract_project_trigram")
        return None


def extract_connection_name(trigram, connections_list):
    """Find the db-pg connection whose name contains the given trigram."""
    print(f"[INFO] Start running function extract_connection_name")
    print(f"[DEBUG] trigram = {trigram}, number of connections to scan = {len(connections_list)}")

    trigram_pattern = re.compile(rf"-{trigram}-")
    matching_connection = None

    for connection in connections_list:
        if get_connection_type(connection) == "db-pg":
            if trigram_pattern.search(connection):
                matching_connection = connection
                print(f"[DEBUG] Matching connection found = {connection}")

    if matching_connection is None:
        print(f"[WARNING] No matching db-pg connection found for trigram = {trigram}")

    print(f"[INFO] End running function extract_connection_name")
    return matching_connection


def define_api_version(api_service,stage=None):
    """Return the current maximum API version number published for the given service."""
    print(f"[INFO] Start running function define_api_version")
    print(f"[DEBUG] stage = {stage}")

    print(f"[INFO] Executing step: listing all packages for the API service")
    last_api_version = 0
    full_name_versions_list = api_service.list_packages()
    print(f"[DEBUG] Total packages found = {len(full_name_versions_list)}")

    api_versions = [extract_ApiId_version(api_version,stage) for api_version in full_name_versions_list if extract_ApiId_version(api_version,stage) is not None]
    print(f"[DEBUG] Parsed version numbers = {api_versions}")

    service_max_api_version = max(api_versions, default=0)
    last_api_version = max(service_max_api_version, last_api_version)

    print(f"[DEBUG] Current max api_version = {last_api_version}")
    print(f"[INFO] End running function define_api_version")
    return last_api_version


def init_api_groups_permissions():
    """Return the list of groups authorized to query through the API deployer."""
    print(f"[INFO] Start running function init_api_groups_permissions")

    # List of groups with deployer query authorization
    authorizations_to_query_through_deployer = [
    {"group": "administrators", "queryThroughDeployer": True},
    {"group": "Data_Engineer", "queryThroughDeployer": True},
    {"group": "ITops", "queryThroughDeployer": True},
    {"group": "SRE", "queryThroughDeployer": True}
                                               ]

    print(f"[DEBUG] Number of authorized groups = {len(authorizations_to_query_through_deployer)}")
    print(f"[INFO] End running function init_api_groups_permissions")
    return authorizations_to_query_through_deployer


def create_or_update_deployment(dss_deployer_client, deployment_id, infra_id, api_version, service_id):
    """Create a new API deployment or update an existing one, then trigger an update."""
    print(f"[INFO] Start running function create_or_update_deployment")
    print(f"[DEBUG] deployment_id = {deployment_id}, infra_id = {infra_id}, api_version = {api_version}, service_id = {service_id}")

    print(f"[INFO] Executing step: retrieving all deployments from API deployer")
    api_deployer = dss_deployer_client.get_apideployer()
    deployment_list = api_deployer.list_deployments(as_objects=True)
    print(f"[DEBUG] Total deployments found = {len(deployment_list)}")

    print(f"[INFO] Executing step: searching for existing deployment matching id and infra")
    deployment = next((d for d in deployment_list if d.get_settings().get_raw()["id"] == deployment_id and d.get_settings().get_raw()["infraId"] == infra_id), None)

    if not deployment:
        print(f"[INFO] Executing step: no existing deployment found, creating new deployment")
        deployment = api_deployer.create_deployment(deployment_id, service_id, infra_id, api_version)
        print(f"[INFO] New deployment created: {deployment_id} on infra {infra_id}")
    else:
        print(f"[INFO] Existing deployment found: {deployment_id} on infra {infra_id}")

    print(f"[INFO] Executing step: updating deployment settings")
    authorizations_to_query_through_deployer = init_api_groups_permissions()
    deployment_settings = deployment.get_settings()
    deployment_settings.set_single_version(api_version)
    deployment_settings_raw = deployment_settings.get_raw()
    deployment_settings_raw["authorizations_to_query_through_deployer "] = init_api_groups_permissions()
    deployment_settings.save()
    print(f"[INFO] Deployment settings saved")

    print(f"[INFO] Executing step: triggering deployment update and waiting for result")
    update = deployment.start_update()
    update.wait_for_result()
    print(f"[INFO] Deployment update completed for {deployment_id}")

    print(f"[INFO] End running function create_or_update_deployment")
    return deployment
