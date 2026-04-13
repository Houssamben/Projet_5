import re
import logging
import dataikuapi

#logging.basicConfig(level=logging.INFO,write_to_console=True)
def extract_ApiId_version(api_version, stage=None):
    
    if stage is None:
        pattern = rf'v(\d+)_(\w+)'
    else:
        pattern = rf'v(\d+)_{stage}'
    
    match = re.search(pattern, api_version['id'])
    
    return int(match.group(1)) if match else None

def get_connection_type(connection):
    print(connection)
    if re.search(r's3-cft-[a-zA-Z0-9_-]+-co[a-zA-Z0-9]+', connection):
        return 's3-cft'
    if re.search(r's3-[a-zA-Z0-9_-]+-co[a-zA-Z0-9]+', connection):
        return 's3-cos'
    if re.search(r'db-[a-zA-Z0-9_-]+-pg[a-zA-Z0-9]+', connection): # to be checked !!!!
        return 'db-pg'
    return None


def update_connection(data, endpoint_id, connection_name):
   
    for endpoint in data.get('endpoints', []):
        if endpoint['id'] == endpoint_id:
            endpoint['connection'] = connection_name
            break
    
    return data

 
def extract_project_trigram(project_key):
    project_key_pattern = re.compile("^\d{2}_(\w+)_(DATASET|DESIGN|PRODUCT)$")

    try:
        match = re.match(project_key_pattern, project_key)
        trigram = match.group(1)
        return trigram
    except:
        return None

# def extract_connection_name(trigram, connection):
    
#     trigram_pattern = re.compile(rf"-{trigram}-")
    
#     if get_connection_type(connection) == "db-pg":
#         if trigram_pattern.search(connection):
#                 matching_connection=connection
     
#     return matching_connection 

def extract_connection_name(trigram, connections_list):
    
    trigram_pattern = re.compile(rf"-{trigram}-")
    
    for connection in connections_list:
        if get_connection_type(connection) == "db-pg":
            if trigram_pattern.search(connection):
                matching_connection=connection
     
    return matching_connection 



def define_api_version(api_service,stage=None):
    last_api_version = 0
    full_name_versions_list = api_service.list_packages()
    api_versions = [extract_ApiId_version(api_version,stage) for api_version in full_name_versions_list if extract_ApiId_version(api_version,stage) is not None]
    service_max_api_version = max(api_versions, default=0)
    last_api_version = max(service_max_api_version, last_api_version)
    
    return last_api_version


#----------------- list to be completed --------------
def init_api_groups_permissions():
    authorizations_to_query_through_deployer = [
    {"group": "administrators", "queryThroughDeployer": True},
    {"group": "Data_Engineer", "queryThroughDeployer": True},
    {"group": "ITops", "queryThroughDeployer": True},
    {"group": "SRE", "queryThroughDeployer": True}
                                               ]
    return authorizations_to_query_through_deployer



def create_or_update_deployment(dss_deployer_client, deployment_id, infra_id, api_version, service_id):
    
    # get all the the deployment from the deployer node                           
    api_deployer = dss_deployer_client.get_apideployer()
    deployment_list = api_deployer.list_deployments(as_objects=True)
    deployment = next((d for d in deployment_list if d.get_settings().get_raw()["id"] == deployment_id and d.get_settings().get_raw()["infraId"] == infra_id), None)

    if not deployment:
        #create deployment if not already exist
        deployment = api_deployer.create_deployment(deployment_id, service_id, infra_id, api_version)
        
    authorizations_to_query_through_deployer = init_api_groups_permissions()
    deployment_settings = deployment.get_settings()
    deployment_settings.set_single_version(api_version)
    deployment_settings_raw = deployment_settings.get_raw()
    deployment_settings_raw["authorizations_to_query_through_deployer "] = init_api_groups_permissions()
              
    deployment_settings.save()
 
    update = deployment.start_update()
    
    update.wait_for_result()

    return deployment



