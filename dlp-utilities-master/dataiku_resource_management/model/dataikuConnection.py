from core.logger import log, LogLevel, Step
from .dataiku import create_or_update_connection
from utils.helpers import format_nested_structure

import dataikuapi
import requests
import urllib3

# Désactiver les avertissements SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


class DataikuConnection():
    def __init__(self, connection_config, vault_informations, use_case_connection_governance, global_connection_governance, host, api_key):
        log(LogLevel.INFO, Step.INIT, f"Début de l'initialisation de la connexion: {connection_config['name']}")
        try:
            self.connection_name = connection_config["name"]
            self.raw_connection_type = connection_config["type"]
            self.connection_scope = connection_config["scope"]
            self.connection_config = connection_config["config"]

            endpoint = f"https://{self.connection_config.get('host', '')}"
            if self.connection_config.get("port", None):
                endpoint = f"https://{self.connection_config.get('host', '')}:{self.connection_config.get('port', '')}"

            if self.raw_connection_type == "cos_connection":
                self.connection_type = "EC2"
                if self.connection_scope != "global":
                    params = use_case_connection_governance[self.raw_connection_type]["params"]
                else:
                    params = global_connection_governance[self.raw_connection_type]["params"]
            elif self.raw_connection_type == "db_connection":
                if "resource" in self.connection_config:
                    self.connection_type = "PostgreSQL"
                elif "connection_url" in self.connection_config:
                    self.connection_type = "Oracle"
                else:
                    raise ValueError(
                        f"Connexion DB '{self.connection_name}' : aucune clé "
                        "'resource'/'ressource' ou 'connection_url' n’est présente – "
                        "type de connexion indéterminé."
                    )
                if self.connection_scope != "global":
                    params = use_case_connection_governance[self.raw_connection_type]["params"][self.connection_type]
                else:
                    params = global_connection_governance[self.raw_connection_type]["params"][self.connection_type]
            else:
                raise ValueError(
                    f"Connexion '{self.connection_name}' : type brut "
                    f"'{self.raw_connection_type}' inconnu – attendu 'cos_connection' ou 'db_connection'."
                )

            self.connection_params = format_nested_structure(
                params,
                managed_data_subpath=self.connection_config.get("managed_data_subpath", ""),
                endpoint=endpoint,
                bucket=self.connection_config.get("bucket", ""),
                path_in_bucket=self.connection_config.get("path_in_bucket", ""),
                ecosystem=self.connection_config.get("ecosystem", ""),
                cos=self.connection_config.get("cos", ""),
                ap_code=self.connection_config.get("ap_code", "AP59641").lower(),
                accessKey="",
                secretKey="",
                port=self.connection_config.get("port", ""),
                host=self.connection_config.get("host", ""),
                user="",
                password="",
                db=self.connection_config.get("db", ""),
                schema=self.connection_config.get("schema", ""),
                AP_Code=self.connection_config.get("ap_code", "AP59641").upper(),
                resource=self.connection_config.get("resource", ""),
                trigram=self.connection_config.get("use_case", "").lower(),
                connection_url=self.connection_config.get("connection_url", ""),
                displayed_url=self.connection_config.get("displayed_url", "")
            )

            if self.connection_scope != 'global':
                self.connection_governance = use_case_connection_governance[self.raw_connection_type].copy()
                self.connection_governance.pop('params', None)
            else:
                self.connection_governance = global_connection_governance[self.raw_connection_type].copy()
                self.connection_governance.pop('params', None)

            self.description = ""

            # TODO revoir ce qui est utile a terme + potentiellement séparer en variable spécifique en fonction du scope
            self.full_config = connection_config

            self.client = dataikuapi.DSSClient(host, api_key, insecure_tls=True)

            if vault_informations:
                if "access_key" in vault_informations:
                    self.connection_params["accessKey"] = vault_informations["access_key"]
                if "secret_key" in vault_informations:
                    self.connection_params["secretKey"] = vault_informations["secret_key"]
                if "user" in vault_informations:
                    self.connection_params["user"] = vault_informations["user"]
                if "password" in vault_informations:
                    self.connection_params["password"] = vault_informations["password"]

            log(LogLevel.INFO, Step.INIT, f"Fin de l'initialisation de la connexion: {connection_config['name']}")
        except Exception as e:
            log(LogLevel.ERROR, Step.INIT,
                f"Erreur lors de l'initialisation de la connexion: {connection_config['name']}: {str(e)}")
            raise

    def run(self):
        log(LogLevel.INFO, Step.RUN, f"Début de l'exécution pour la connexion: {self.connection_name}")
        try:

            create_or_update_connection(self.client, self.connection_name, self.connection_type, self.connection_params,
                                        self.connection_governance, self.description)


            log(LogLevel.INFO, Step.RUN, f"Fin de l'exécution pour la connexion: {self.connection_name}")
        except Exception as e:
            log(LogLevel.ERROR, Step.RUN,
                f"Erreur lors de l'exécution pour la connexion: {self.connection_name}: {str(e)}")
