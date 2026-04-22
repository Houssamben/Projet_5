from core.logger import log, LogLevel, Step
from utils.helpers import format_nested_structure
from .dataiku import (
    create_or_update_group,
    get_or_create_folder,
    set_connection_permissions,
    set_data_collection_permissions,
    clean_connection,
    clean_data_collection,
    create_or_update_code_env,
    get_or_create_project,
    set_project_permissions,
    set_project_code_env,
    create_or_update_data_collection,
    add_dataset_to_data_collection
)

import dataikuapi
import requests
import urllib3

# Désactiver les avertissements SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


class UseCaseIndus:
    def __init__(self, use_case_trigram, use_case_config, use_case_gouvernance, design_rd_host, design_rd_user_api_key):
        log(LogLevel.INFO, Step.INIT, f"Début de l'initialisation du use case indus: {use_case_trigram}")
        try:
            # Initialisation des propriétés de base
            self.use_case_trigram = use_case_trigram
            self.use_case_ap_code = use_case_config['ap_code']
            self.use_case_name = use_case_config['name']
            self.use_case_lots = use_case_config["lots"]
            self.data_sources = use_case_config["data_sources"]

            # Initialisation du client Dataiku
            self.client = dataikuapi.DSSClient(design_rd_host, design_rd_user_api_key, insecure_tls=True)

            # Configuration des groupes
            self.use_case_groups = format_nested_structure(
                use_case_gouvernance["use_case_groups"],
                use_case_trigram=self.use_case_trigram
            )
            self.use_case_groups_config = use_case_config["use_case_group"]

            # Configuration des permissions
            self.use_case_groups_permissions = use_case_gouvernance["use_case_groups_permissions"]
            self.project_settings = {}

            # Configuration des projets
            self.use_case_projects = []
            self.projects_permissions = []
            for lot in self.use_case_lots:
                permissions = format_nested_structure(
                    use_case_gouvernance["projects_permissions"],
                    use_case_trigram=self.use_case_trigram
                )
                if lot["activate_lot_group"]:
                    permissions += format_nested_structure(
                        use_case_gouvernance["lot_projects_permissions"],
                        use_case_trigram=self.use_case_trigram,
                        lot_trigram=lot["trigram"]
                    )
                self.projects_permissions.append({lot["lot"]: permissions})
                self.use_case_projects.append({
                    lot["lot"]: format_nested_structure(
                        use_case_gouvernance["use_case_projects"],
                        lot_trigram=lot["trigram"],
                        lot_name=lot["name"],
                        ap_code=self.use_case_ap_code
                    )
                })

            # Configuration des collections de données
            self.data_collections = []
            self.data_collection_permissions = []
            for lot in self.use_case_lots:
                permissions = format_nested_structure(
                    use_case_gouvernance["data_collection_permissions"],
                    use_case_trigram=self.use_case_trigram
                )
                if lot["activate_lot_group"]:
                    permissions += format_nested_structure(
                        use_case_gouvernance["lot_data_collection_permissions"],
                        use_case_trigram=self.use_case_trigram,
                        lot_trigram=lot["trigram"]
                    )
                self.data_collection_permissions.append((lot["lot"], permissions))
                self.data_collections.append((
                    lot["lot"], format_nested_structure(
                        use_case_gouvernance["data_collection_names"],
                        lot_trigram=lot["trigram"]
                    )
                ))

            # Configuration des connexions
            self.cos_connection = use_case_config["cos_connection"]
            self.db_connection = use_case_config["db_connection"]
            self.shared_cos_connection = use_case_config["shared_cos_connection"]
            self.shared_db_connection = use_case_config["shared_db_connection"]

            self.cos_connections_permissions = format_nested_structure(
                use_case_gouvernance["cos_connections_permissions"],
                use_case_trigram=self.use_case_trigram
            )
            self.db_connections_permissions = format_nested_structure(
                use_case_gouvernance["db_connections_permissions"],
                use_case_trigram=self.use_case_trigram
            )
            self.shared_cos_connections_permissions = format_nested_structure(
                use_case_gouvernance["shared_cos_connections_permissions"],
                use_case_trigram=self.use_case_trigram
            )
            self.shared_db_connections_permissions = format_nested_structure(
                use_case_gouvernance["shared_db_connections_permissions"],
                use_case_trigram=self.use_case_trigram
            )

            # Configuration des collections partagées
            self.shared_data_collection = use_case_config["shared_data_collection"]
            self.shared_data_collection_permissions = format_nested_structure(
                use_case_gouvernance["shared_data_collection_permissions"],
                use_case_trigram=self.use_case_trigram
            )

            # Configuration de l'environnement de code
            self.code_env_permissions = format_nested_structure(
                use_case_gouvernance["code_env_permissions"],
                use_case_trigram=self.use_case_trigram
            )

            # Configuration du dossier
            self.use_case_folder_name = f"{self.use_case_trigram}_{self.use_case_ap_code}_{self.use_case_name}"
            self.use_case_folder_permissions = format_nested_structure(
                use_case_gouvernance["use_case_folder_permissions"],
                use_case_trigram=self.use_case_trigram
            )

            log(LogLevel.INFO, Step.INIT, f"Fin de l'initialisation du use case indus: {use_case_trigram}")
        except Exception as e:
            log(LogLevel.ERROR, Step.INIT,
                f"Erreur lors de l'initialisation du use case indus {use_case_trigram}: {str(e)}")
            raise

    def run(self):
        log(LogLevel.INFO, Step.RUN, f"Début de l'exécution pour le use case indus: {self.use_case_trigram}")
        try:
            # Création/mise à jour des groupes
            for group_key in self.use_case_groups:
                log(LogLevel.INFO, Step.RUN, f"Traitement du groupe: {self.use_case_groups[group_key]}")
                create_or_update_group(
                    self.client,
                    group_name=self.use_case_groups[group_key],
                    group_description=f"{self.use_case_trigram} : Use Case Group",
                    group_source_type=self.use_case_groups_config[group_key]["sourceType"],
                    ssoGroupNames=self.use_case_groups_config[group_key]["ssoGroupNames"],
                    group_permissions=self.use_case_groups_permissions
                )

            # Configuration de l'environnement de code
            create_or_update_code_env(
                self.client,
                self.use_case_trigram,
                self.code_env_permissions
            )

            # Création du dossier
            root_folder = self.client.get_project_folder("ROOT")
            root_child_folders = root_folder.list_child_folders()
            use_case_indus_folder_id = None
            for folder in root_child_folders:
                if folder.name == "Use Case Indus":
                    use_case_indus_folder_id = folder.id

            if use_case_indus_folder_id is None:
                log(LogLevel.ERROR, Step.RUN, "Dossier 'Use Case Indus' non trouvé")
                return

            use_case_indus_folder = self.client.get_project_folder(use_case_indus_folder_id)
            use_case_folder = get_or_create_folder(
                self.client,
                use_case_indus_folder,
                self.use_case_folder_name,
                self.use_case_folder_permissions
            )

            # Configuration des projets
            for lots in self.use_case_projects:

                for lot_number in lots:
                    lot_info = next(lot for lot in self.use_case_lots if lot['lot'] == lot_number)
                    lot_folder = get_or_create_folder(
                        self.client,
                        use_case_folder,
                        f"Lot{lot_info['lot']}_{lot_info['trigram']}",
                        self.use_case_folder_permissions
                    )
                    for proj in lots[lot_number]:
                        project = get_or_create_project(
                            self.client,
                            proj["project_key"],
                            proj["project_name"],
                            proj["project_description"],
                            "admin",
                            self.project_settings,
                            lot_folder.id
                        )
                        project_permissions = next((item for item in self.projects_permissions if lot_number in item),
                                                   None)
                        set_project_permissions(project, project_permissions[lot_number])
                        set_project_code_env(project, self.use_case_trigram)

            # Configuration des collections de données
            use_case_collection_names = []
            for lot_key, data_collection_names in self.data_collections:
                for data_collection_name in data_collection_names:
                    use_case_collection_names.append(data_collection_name)
                    create_or_update_data_collection(
                        self.client,
                        data_collection_name,
                        next((item[1] for item in self.data_collection_permissions if item[0] == lot_key), None),
                        overwrite=False
                    )

            for data_source in self.data_sources:
                data_collection_name = f"{data_source['name']}_{self.use_case_trigram}"
                use_case_collection_names.append(data_collection_name)
                create_or_update_data_collection(
                    self.client,
                    data_collection_name,
                    self.shared_data_collection_permissions,
                    overwrite=False
                )
                add_dataset_to_data_collection(
                    self.client,
                    data_collection_name,
                    data_source["name"],
                    data_source["datasets"],
                    overwrite=True
                )

            # Configuration des collections partagées
            for data_collection in self.shared_data_collection:
                set_data_collection_permissions(
                    self.client,
                    data_collection,
                    self.shared_data_collection_permissions
                )

            # Configuration des connexions
            for connection in self.cos_connection:
                set_connection_permissions(
                    self.client,
                    connection,
                    self.cos_connections_permissions,
                    overwrite=True
                )

            for connection in self.db_connection:
                set_connection_permissions(
                    self.client,
                    connection,
                    self.db_connections_permissions,
                    overwrite=True
                )

            for connection in self.shared_cos_connection:
                set_connection_permissions(
                    self.client,
                    connection,
                    self.shared_cos_connections_permissions,
                    overwrite=False
                )

            for connection in self.shared_db_connection:
                set_connection_permissions(
                    self.client,
                    connection,
                    self.shared_db_connections_permissions,
                    overwrite=False
                )

            # Nettoyage des permissions
            to_keep_connections = (
                    self.cos_connection +
                    self.db_connection +
                    self.shared_cos_connection +
                    self.shared_db_connection
            )
            clean_connection(self.client, to_keep_connections, f"{self.use_case_trigram}_Admin")
            clean_connection(self.client, to_keep_connections, f"{self.use_case_trigram}_Contributor")
            clean_connection(self.client, to_keep_connections, f"{self.use_case_trigram}_Consumer")

            for lot in self.use_case_lots:
                clean_connection(
                    self.client,
                    to_keep_connections,
                    f"{self.use_case_trigram}_{lot['trigram']}_Consumer"
                )

            to_keep_collections = self.shared_data_collection + use_case_collection_names
            clean_data_collection(self.client, to_keep_collections, f"{self.use_case_trigram}_Admin")
            clean_data_collection(self.client, to_keep_collections, f"{self.use_case_trigram}_Contributor")
            clean_data_collection(self.client, to_keep_collections, f"{self.use_case_trigram}_Consumer")

            for lot in self.use_case_lots:
                clean_data_collection(
                    self.client,
                    to_keep_collections,
                    f"{self.use_case_trigram}_{lot['trigram']}_Consumer"
                )

            log(LogLevel.INFO, Step.RUN, f"Fin de l'exécution pour le use case indus: {self.use_case_trigram}")
        except Exception as e:
            log(LogLevel.ERROR, Step.RUN,
                f"Erreur lors de l'exécution pour le use case indus {self.use_case_trigram}: {str(e)}")
            raise
