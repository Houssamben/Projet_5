import re
import dataikuapi


def extract_ApiId_version(api_version, stage=None):
    print("[INFO] Start running function extract_ApiId_version")
    print(f"[DEBUG] stage = {stage}")

    if stage is None:
        pattern = rf'v(\d+)_(\w+)'
    else:
        pattern = rf'v(\d+)_{stage}'

    match = re.search(pattern, api_version['id'])
    result = int(match.group(1)) if match else None

    print(f"[DEBUG] extracted version = {result}")
    print("[INFO] End running function extract_ApiId_version")
    return result


def get_connection_type(connection):
    print("[INFO] Start running function get_connection_type")
    print(connection)
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


def update_connection(data, endpoint_id, connection_name):
    print("[INFO] Start running function update_connection")
    print(f"[DEBUG] endpoint_id = {endpoint_id}")
    print(f"[DEBUG] connection_name = {connection_name}")

    for endpoint in data.get('endpoints', []):
        if endpoint['id'] == endpoint_id:
            print(f"[INFO] Executing step: updating connection for endpoint {endpoint_id}")
            endpoint['connection'] = connection_name
            break

    print("[INFO] End running function update_connection")
    return data


def extract_project_trigram(project_key):
    print("[INFO] Start running function extract_project_trigram")
    print(f"[DEBUG] project_key = {project_key}")

    project_key_pattern = re.compile("^\d{2}_(\w+)_(DATASET|DESIGN|PRODUCT)$")

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


def extract_connection_name(trigram, connections_list):
    print("[INFO] Start running function extract_connection_name")
    print(f"[DEBUG] trigram = {trigram}")
    print(f"[DEBUG] number of connections to scan = {len(connections_list)}")

    trigram_pattern = re.compile(rf"-{trigram}-")

    for connection in connections_list:
        if get_connection_type(connection) == "db-pg":
            if trigram_pattern.search(connection):
                matching_connection=connection
                print(f"[DEBUG] matching connection found = {matching_connection}")

    print(f"[DEBUG] returning matching_connection = {matching_connection}")
    print("[INFO] End running function extract_connection_name")
    return matching_connection


def define_api_version(api_service,stage=None):
    print("[INFO] Start running function define_api_version")
    print(f"[DEBUG] stage = {stage}")

    last_api_version = 0
    full_name_versions_list = api_service.list_packages()
    print(f"[DEBUG] total packages found = {len(full_name_versions_list)}")

    api_versions = [extract_ApiId_version(api_version,stage) for api_version in full_name_versions_list if extract_ApiId_version(api_version,stage) is not None]
    service_max_api_version = max(api_versions, default=0)
    last_api_version = max(service_max_api_version, last_api_version)

    print(f"[DEBUG] last_api_version = {last_api_version}")
    print("[INFO] End running function define_api_version")
    return last_api_version


#----------------- list to be completed --------------
def init_api_groups_permissions():
    print("[INFO] Start running function init_api_groups_permissions")

    authorizations_to_query_through_deployer = [
    {"group": "administrators", "queryThroughDeployer": True},
    {"group": "Data_Engineer", "queryThroughDeployer": True},
    {"group": "ITops", "queryThroughDeployer": True},
    {"group": "SRE", "queryThroughDeployer": True}
                                               ]
    print(f"[DEBUG] number of authorized groups = {len(authorizations_to_query_through_deployer)}")
    print("[INFO] End running function init_api_groups_permissions")
    return authorizations_to_query_through_deployer


def create_or_update_deployment(dss_deployer_client, deployment_id, infra_id, api_version, service_id):
    print("[INFO] Start running function create_or_update_deployment")
    print(f"[DEBUG] deployment_id = {deployment_id}")
    print(f"[DEBUG] infra_id = {infra_id}")
    print(f"[DEBUG] api_version = {api_version}")
    print(f"[DEBUG] service_id = {service_id}")

    # Get all deployments from the deployer node
    print("[INFO] Executing step: fetching all deployments from deployer node")
    api_deployer = dss_deployer_client.get_apideployer()
    deployment_list = api_deployer.list_deployments(as_objects=True)
    print(f"[DEBUG] total deployments found = {len(deployment_list)}")

    deployment = next((d for d in deployment_list if d.get_settings().get_raw()["id"] == deployment_id and d.get_settings().get_raw()["infraId"] == infra_id), None)

    if not deployment:
        # Create deployment if it does not already exist
        print(f"[INFO] Executing step: deployment '{deployment_id}' not found — creating new deployment")
        deployment = api_deployer.create_deployment(deployment_id, service_id, infra_id, api_version)
    else:
        print(f"[INFO] Executing step: deployment '{deployment_id}' already exists — updating it")

    print("[INFO] Executing step: setting API version and group permissions")
    authorizations_to_query_through_deployer = init_api_groups_permissions()
    deployment_settings = deployment.get_settings()
    deployment_settings.set_single_version(api_version)
    deployment_settings_raw = deployment_settings.get_raw()
    deployment_settings_raw["authorizations_to_query_through_deployer "] = init_api_groups_permissions()

    print("[INFO] Executing step: saving deployment settings")
    deployment_settings.save()

    print("[INFO] Executing step: starting deployment update and waiting for result")
    update = deployment.start_update()
    update.wait_for_result()
    print("[INFO] Executing step: deployment update completed")

    print("[INFO] End running function create_or_update_deployment")
    return deployment
