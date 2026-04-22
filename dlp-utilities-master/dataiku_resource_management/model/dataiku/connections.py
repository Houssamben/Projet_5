from core.logger import log, LogLevel, Step


def set_connection_permissions(dss_client, connection_name, connections_permissions, overwrite=False):
    log(LogLevel.INFO, Step.CONNECTION,
        f"Début de la configuration des permissions pour la connexion: {connection_name}")
    try:
        connection_obj = dss_client.get_connection(connection_name)
        conn_settings = connection_obj.get_settings()
        usable_groups = conn_settings.usable_by_allowed_groups
        details_readability_groups = conn_settings.details_readability.allowed_groups
        if overwrite:
            usable_groups = []
            details_readability_groups = []

        conn_settings.set_usability(False, *(usable_groups + connections_permissions["allowedGroups"]))
        conn_settings.details_readability.set_readability(False, *(
                    details_readability_groups + connections_permissions["detailsReadableByGroups"]))
        conn_settings.save()
        log(LogLevel.INFO, Step.CONNECTION,
            f"Fin de la configuration des permissions pour la connexion: {connection_name}")
    except Exception as e:
        log(LogLevel.ERROR, Step.CONNECTION,
            f"Erreur lors de la configuration des permissions pour {connection_name}: {str(e)}")
        raise


def clean_connection(dss_client, to_keep_connections, group_name):
    """Nettoie les permissions d'une connexion en retirant un groupe spécifique"""
    log(LogLevel.INFO, Step.PROCESS, f"Début du nettoyage des permissions pour le groupe: {group_name}")

    try:
        # Récupération de toutes les connexions
        log(LogLevel.DEBUG, Step.PROCESS, "Récupération de la liste de toutes les connexions")
        all_connections = dss_client.list_connections()
        log(LogLevel.DEBUG, Step.PROCESS, f"Nombre total de connexions: {len(all_connections)}")

        # Identification des connexions impactées
        log(LogLevel.INFO, Step.PROCESS, f"Identification des connexions à nettoyer pour le groupe: {group_name}")
        impacted_connections = {
            key: value
            for key, value in all_connections.items()
            if (group_name in value.get("allowedGroups", []) or
                group_name in value["detailsReadability"].get("allowedGroups", [])) and
               (key not in to_keep_connections)
        }

        impacted_connections_names = list(impacted_connections.keys())
        log(LogLevel.INFO, Step.PROCESS, f"Nombre de connexions impactées: {len(impacted_connections_names)}")
        if impacted_connections_names:
            log(LogLevel.DEBUG, Step.PROCESS, f"Connexions impactées: {impacted_connections_names}")

        # Nettoyage des permissions pour chaque connexion impactée
        for connection_name in impacted_connections_names:
            log(LogLevel.INFO, Step.PROCESS, f"Nettoyage de la connexion: {connection_name}")

            try:
                # Récupération de la connexion
                log(LogLevel.DEBUG, Step.PROCESS, f"Récupération de la connexion: {connection_name}")
                connection_obj = dss_client.get_connection(connection_name)
                conn_settings = connection_obj.get_settings()

                # Récupération des groupes actuels
                usable_groups = conn_settings.usable_by_allowed_groups
                details_readability_groups = conn_settings.details_readability.allowed_groups

                log(LogLevel.DEBUG, Step.PROCESS, f"Groupes utilisables avant nettoyage: {usable_groups}")
                log(LogLevel.DEBUG, Step.PROCESS, f"Groupes lisibles avant nettoyage: {details_readability_groups}")

                # Nettoyage des groupes
                new_usable_groups = list({item for item in usable_groups if item != group_name})
                new_details_readability_groups = list(
                    {item for item in details_readability_groups if item != group_name})

                log(LogLevel.DEBUG, Step.PROCESS, f"Groupes utilisables après nettoyage: {new_usable_groups}")
                log(LogLevel.DEBUG, Step.PROCESS, f"Groupes lisibles après nettoyage: {new_details_readability_groups}")

                # Mise à jour des permissions
                conn_settings.set_usability(False, *new_usable_groups)
                conn_settings.details_readability.set_readability(False, *new_details_readability_groups)
                conn_settings.save()

                log(LogLevel.INFO, Step.PROCESS, f"Connexion {connection_name} nettoyée avec succès")

            except Exception as conn_error:
                log(LogLevel.ERROR, Step.PROCESS,
                    f"Erreur lors du nettoyage de la connexion {connection_name}: {str(conn_error)}")
                continue  # Passe à la connexion suivante en cas d'erreur

        log(LogLevel.INFO, Step.PROCESS, f"Fin du nettoyage des permissions pour le groupe: {group_name}")

    except Exception as e:
        log(LogLevel.ERROR, Step.PROCESS, f"Erreur lors du nettoyage des permissions pour {group_name}: {str(e)}")


def create_or_update_connection(dss_client, connection_name, connection_type, connection_params,
                                connection_governance, description=""):
    """
    Crée ou met à jour une connexion Dataiku avec les paramètres et gouvernance spécifiés.

    Args:
        dss_client: Client Dataiku
        connection_name: Nom de la connexion
        connection_type: Type de connexion (EC2, Oracle, PostgreSQL)
        connection_params: Dictionnaire des paramètres de connexion
        connection_governance: Dictionnaire de gouvernance
        description: Description de la connexion (optionnel)
    """
    try:
        log(LogLevel.INFO, Step.CONNECTION, f"Début du traitement de la connexion: {connection_name}")

        # Vérifier si la connexion existe déjà
        try:
            connections = dss_client.list_connections(as_type="dictitems")
            connection_exists = any(c == connection_name for c in connections)
        except Exception as e:
            log(LogLevel.ERROR, Step.CONNECTION,
                f"Erreur lors de la vérification de l'existence de la connexion {connection_name}: {str(e)}")
            raise

        if not connection_exists:
            try:
                log(LogLevel.INFO, Step.CONNECTION, f"Création de la nouvelle connexion: {connection_name}")
                dss_client.create_connection(
                    name=connection_name,
                    type=connection_type,
                    params=connection_params,
                    usable_by=connection_governance["usableBy"],
                    allowed_groups=connection_governance["allowedGroups"],
                    description=description
                )
                log(LogLevel.INFO, Step.CONNECTION, f"Connexion {connection_name} créée avec succès")
            except Exception as e:
                log(LogLevel.ERROR, Step.CONNECTION,
                    f"Erreur lors de la création de la connexion {connection_name}: {str(e)}")
                raise

        # Récupération de la connexion pour mise à jour
        try:
            connection = dss_client.get_connection(connection_name)
            connection_settings_object = connection.get_settings()
            connection_settings = connection_settings_object.get_raw()
            log(LogLevel.INFO, Step.CONNECTION, f"Connexion {connection_name} récupérée pour mise à jour")
        except Exception as e:
            log(LogLevel.ERROR, Step.CONNECTION,
                f"Erreur lors de la récupération de la connexion {connection_name}: {str(e)}")
            raise

        # Mise à jour des paramètres de gouvernance
        try:
            connection_settings["allowWrite"] = connection_governance["allowWrite"]
            connection_settings["allowManagedDatasets"] = connection_governance["allowManagedDatasets"]
            connection_settings["allowManagedFolders"] = connection_governance["allowManagedFolders"]

            connection_settings["usableBy"] = connection_governance["usableBy"]
            for group in connection_governance["allowedGroups"]:
                if group not in connection_settings["allowedGroups"]:
                    connection_settings["allowedGroups"].append(group)

            details_readability_groups = connection_settings["detailsReadability"].get("allowedGroups")

            for group in connection_governance["detailsReadability"].get("allowedGroups"):
                if group not in details_readability_groups:
                    details_readability_groups.append(group)

            connection_settings["detailsReadability"] = {
                "allowed_groups": details_readability_groups,
                "readableBy": "ALLOWED"
            }
            log(LogLevel.INFO, Step.CONNECTION, f"Paramètres de gouvernance mis à jour pour {connection_name}")
        except Exception as e:
            log(LogLevel.ERROR, Step.CONNECTION,
                f"Erreur lors de la mise à jour des paramètres de gouvernance pour {connection_name}: {str(e)}")
            raise

        # Mise à jour des paramètres de connexion
        try:
            actual_params = connection_settings['params']

            if "accessKey" in connection_params and connection_params["accessKey"]:
                actual_params["accessKey"] = connection_params["accessKey"]

            if "secretKey" in connection_params and connection_params["secretKey"]:
                actual_params["secretKey"] = connection_params["secretKey"]

            if "user" in connection_params and connection_params["user"]:
                actual_params["user"] = connection_params["user"]

            if "password" in connection_params and connection_params["password"]:
                actual_params["password"] = connection_params["password"]

            # Mise à jour des autres paramètres
            for key, value in connection_params.items():
                if key not in ["accessKey", "secretKey", "user", "password"] and value is not None:
                    actual_params[key] = value

            connection_settings["params"] = actual_params
            log(LogLevel.INFO, Step.CONNECTION, f"Paramètres de connexion mis à jour pour {connection_name}")
        except Exception as e:
            log(LogLevel.ERROR, Step.CONNECTION,
                f"Erreur lors de la mise à jour des paramètres de connexion pour {connection_name}: {str(e)}")
            raise

        # Sauvegarde des modifications
        try:
            connection_settings_object.save()
            log(LogLevel.INFO, Step.CONNECTION, f"Connexion {connection_name} sauvegardée avec succès")
        except Exception as e:
            log(LogLevel.ERROR, Step.CONNECTION,
                f"Erreur lors de la sauvegarde de la connexion {connection_name}: {str(e)}")
            raise

        log(LogLevel.INFO, Step.CONNECTION, f"Fin du traitement de la connexion: {connection_name}")
        return connection

    except Exception as e:
        log(LogLevel.ERROR, Step.CONNECTION,
            f"Erreur critique lors du traitement de la connexion {connection_name}: {str(e)}")
        raise