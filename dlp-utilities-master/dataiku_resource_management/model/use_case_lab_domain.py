from core.logger import log, LogLevel, Step
from utils.helpers import format_nested_structure
from .dataiku import (
    create_or_update_group,
    get_or_create_folder,
    set_connection_permissions,
    set_data_collection_permissions,
    clean_connection,
    clean_data_collection,
    create_or_update_code_env
)

import dataikuapi
import requests
import urllib3

# Désactiver les avertissements SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


class UseCaseLabDomain():
    def __init__(self, domain_code, domain_config, lab_domain_gouvernance, design_rd_host, design_rd_user_api_key):
        log(LogLevel.INFO, Step.INIT, f"Début de l'initialisation du domaine: {domain_code}")
        try:
            self.domain_code = domain_code
            self.domain_name = domain_config["name"]
            self.cos_connection = domain_config["cos_connection"]
            self.db_connection = domain_config["db_connection"]
            self.shared_data_collection = domain_config["shared_data_collection"]
            self.shared_cos_connection = domain_config["shared_cos_connection"]
            self.shared_db_connection = domain_config["shared_db_connection"]
            self.use_case_group = domain_config["use_case_group"]

            self.client = dataikuapi.DSSClient(design_rd_host, design_rd_user_api_key, insecure_tls=True)
            self.domain_groups = format_nested_structure(
                lab_domain_gouvernance["domain_groups"],
                domain_code=self.domain_code
            )
            self.domain_folder_permissions = format_nested_structure(
                lab_domain_gouvernance["domain_folder_permissions"],
                contributor_group=f"{self.domain_code}_Contributor"
            )
            self.cos_connections_permissions = format_nested_structure(
                lab_domain_gouvernance["cos_connections_permissions"],
                contributor_group=f"{self.domain_code}_Contributor"
            )
            self.db_connections_permissions = format_nested_structure(
                lab_domain_gouvernance["db_connections_permissions"],
                contributor_group=f"{self.domain_code}_Contributor"
            )
            self.shared_cos_connections_permissions = format_nested_structure(
                lab_domain_gouvernance["shared_cos_connections_permissions"],
                contributor_group=f"{self.domain_code}_Contributor"
            )
            self.shared_db_connections_permissions = format_nested_structure(
                lab_domain_gouvernance["shared_db_connections_permissions"],
                contributor_group=f"{self.domain_code}_Contributor"
            )
            self.shared_data_collection_permissions = format_nested_structure(
                lab_domain_gouvernance["shared_data_collection_permissions"],
                contributor_group=f"{self.domain_code}_Contributor"
            )
            self.code_env_permissions = format_nested_structure(
                lab_domain_gouvernance["code_env_permissions"],
                contributor_group=f"{self.domain_code}_Contributor"
            )
            self.domain_groups_permissions = lab_domain_gouvernance["domain_groups_permissions"]

            self.domain_folder_name = f"{self.domain_code}_{self.domain_name}"

            log(LogLevel.INFO, Step.INIT, f"Fin de l'initialisation du domaine: {domain_code}")
        except Exception as e:
            log(LogLevel.ERROR, Step.INIT, f"Erreur lors de l'initialisation du domaine {domain_code}: {str(e)}")
            raise

    def run(self):
        log(LogLevel.INFO, Step.RUN, f"Début de l'exécution pour le domaine: {self.domain_code}")
        try:
            for group_name in self.domain_groups.values():
                log(LogLevel.INFO, Step.RUN, f"Traitement du groupe: {group_name}")
                create_or_update_group(
                    self.client,
                    group_name=group_name,
                    group_description=f"{self.domain_code} : Use Case Group",
                    group_source_type=self.use_case_group["sourceType"],
                    ssoGroupNames=self.use_case_group["ssoGroupNames"],
                    group_permissions=self.domain_groups_permissions
                )

            root_folder = self.client.get_project_folder("ROOT")
            root_child_folders = root_folder.list_child_folders()
            use_case_lab_folder_id = None
            for folder in root_child_folders:
                if folder.name == "Use Case Lab":
                    use_case_lab_folder_id = folder.id

            if use_case_lab_folder_id is None:
                log(LogLevel.ERROR, Step.RUN, "Dossier 'Use Case Lab' non trouvé")
                return

            use_case_lab_folder = self.client.get_project_folder(use_case_lab_folder_id)
            domain_folder = get_or_create_folder(self.client, use_case_lab_folder, self.domain_folder_name,
                                                 self.domain_folder_permissions)
            domain_folder_settings = domain_folder.get_settings()
            domain_folder_settings.set_owner("admin")
            domain_folder_settings.save()

            for connection in self.cos_connection:
                set_connection_permissions(self.client, connection, self.cos_connections_permissions, overwrite=True)

            for connection in self.db_connection:
                set_connection_permissions(self.client, connection, self.db_connections_permissions, overwrite=True)

            for connection in self.shared_cos_connection:
                set_connection_permissions(self.client, connection, self.shared_cos_connections_permissions,
                                           overwrite=False)

            for connection in self.shared_db_connection:
                set_connection_permissions(self.client, connection, self.shared_db_connections_permissions,
                                           overwrite=False)

            for data_collection in self.shared_data_collection:
                set_data_collection_permissions(self.client, data_collection, self.shared_data_collection_permissions)

            create_or_update_code_env(self.client, self.domain_code, self.code_env_permissions)

            to_keep_connections = self.cos_connection + self.db_connection + self.shared_cos_connection + self.shared_db_connection
            clean_connection(self.client, to_keep_connections, f"{self.domain_code}_Contributor")

            to_keep_collections = self.shared_data_collection
            clean_data_collection(self.client, to_keep_collections, f"{self.domain_code}_Contributor")

            log(LogLevel.INFO, Step.RUN, f"Fin de l'exécution pour le domaine: {self.domain_code}")
        except Exception as e:
            log(LogLevel.ERROR, Step.RUN, f"Erreur lors de l'exécution pour le domaine {self.domain_code}: {str(e)}")
