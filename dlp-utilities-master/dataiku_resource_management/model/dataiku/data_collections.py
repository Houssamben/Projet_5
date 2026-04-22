from core.logger import log, LogLevel, Step


def set_data_collection_permissions(dss_client, collection_name, collection_permissions):
    """Configure les permissions pour une collection de données"""
    log(LogLevel.INFO, Step.DATA_COLLECTION,
        f"Début de la configuration des permissions pour la collection: {collection_name}")

    try:
        # Récupération de la liste des collections
        log(LogLevel.DEBUG, Step.DATA_COLLECTION, "Récupération de la liste des collections de données")
        data_collections = dss_client.list_data_collections()

        # Recherche de la collection par display_name
        log(LogLevel.DEBUG, Step.DATA_COLLECTION, f"Recherche de la collection avec display_name: {collection_name}")
        data_collection = next((obj for obj in data_collections if obj.display_name == collection_name), None)

        if not data_collection:
            log(LogLevel.ERROR, Step.DATA_COLLECTION, f"Collection {collection_name} non trouvée")
            return

        log(LogLevel.INFO, Step.DATA_COLLECTION,
            f"Collection trouvée: {data_collection.display_name} (ID: {data_collection.id})")

        # Récupération des paramètres de la collection
        log(LogLevel.DEBUG, Step.DATA_COLLECTION, f"Récupération des paramètres de la collection {data_collection.id}")
        collection_settings = dss_client.get_data_collection(data_collection.id).get_settings()

        # Ajout des permissions
        log(LogLevel.INFO, Step.DATA_COLLECTION,
            f"Ajout de {len(collection_permissions)} permission(s) à la collection")
        for perm in collection_permissions:
            log(LogLevel.DEBUG, Step.DATA_COLLECTION, f"Ajout de la permission: {perm}")
            collection_settings.permissions.append(perm)

        # Sauvegarde des paramètres
        log(LogLevel.DEBUG, Step.DATA_COLLECTION, "Sauvegarde des paramètres de la collection")
        collection_settings.save()

        log(LogLevel.INFO, Step.DATA_COLLECTION,
            f"Fin de la configuration des permissions pour la collection: {collection_name}")

    except Exception as e:
        log(LogLevel.ERROR, Step.DATA_COLLECTION,
            f"Erreur lors de la configuration des permissions pour {collection_name}: {str(e)}")
        raise


def clean_data_collection(dss_client, to_keep_collections, group_name):
    """Nettoie les permissions d'une collection de données en retirant un groupe spécifique"""
    log(LogLevel.INFO, Step.DATA_COLLECTION,
        f"Début du nettoyage des permissions pour le groupe: {group_name} (collections)")

    try:
        # Récupération de toutes les collections
        log(LogLevel.DEBUG, Step.DATA_COLLECTION, "Récupération de la liste de toutes les collections de données")
        all_collections = dss_client.list_data_collections(as_type="objects")
        log(LogLevel.DEBUG, Step.DATA_COLLECTION, f"Nombre total de collections: {len(all_collections)}")

        # Identification des collections impactées
        log(LogLevel.INFO, Step.DATA_COLLECTION,
            f"Identification des collections à nettoyer pour le groupe: {group_name}")
        impacted_collections = []

        for collection in all_collections:
            try:
                settings = collection.get_settings()
                # Vérifier si le groupe est dans les permissions
                group_in_permissions = any(
                    perm.get("group") == group_name
                    for perm in settings.permissions
                    if isinstance(perm, dict) and "group" in perm
                )

                # Vérifier si la collection doit être conservée
                should_keep = settings.display_name in to_keep_collections

                if group_in_permissions and not should_keep:
                    impacted_collections.append(collection)

            except Exception as coll_error:
                log(LogLevel.WARNING, Step.DATA_COLLECTION,
                    f"Erreur lors de la vérification de la collection {collection.display_name}: {str(coll_error)}")
                continue

        impacted_collection_names = [col.get_settings().display_name for col in impacted_collections]
        log(LogLevel.INFO, Step.DATA_COLLECTION, f"Nombre de collections impactées: {len(impacted_collections)}")
        if impacted_collection_names:
            log(LogLevel.DEBUG, Step.DATA_COLLECTION, f"Collections impactées: {impacted_collection_names}")

        # Nettoyage des permissions pour chaque collection impactée
        for col in impacted_collections:
            collection = col.get_settings()
            log(LogLevel.INFO, Step.DATA_COLLECTION, f"Nettoyage de la collection: {collection.display_name}")

            try:
                # Récupération de la collection
                log(LogLevel.DEBUG, Step.DATA_COLLECTION, f"Récupération de la collection: {collection.display_name}")
                collection_obj = dss_client.get_data_collection(collection.id)
                collection_settings = collection_obj.get_settings()

                # Récupération des groupes actuels
                current_permissions = collection_settings.permissions

                # Nettoyage des groupes dans les permissions (avec vérification)
                new_permissions = []
                for perm in current_permissions:
                    if isinstance(perm, dict) and "group" in perm:
                        if perm.get("group") != group_name:
                            new_permissions.append(perm)
                    else:
                        log(LogLevel.WARNING, Step.DATA_COLLECTION, f"Permission invalide trouvée: {perm}")
                        new_permissions.append(perm)

                # Mise à jour des permissions
                collection_settings.permissions = new_permissions
                collection_settings.save()

                log(LogLevel.INFO, Step.DATA_COLLECTION, f"Collection {collection.display_name} nettoyée avec succès")

            except Exception as coll_error:
                log(LogLevel.ERROR, Step.DATA_COLLECTION,
                    f"Erreur lors du nettoyage de la collection {collection.display_name}: {str(coll_error)}")
                continue  # Passe à la collection suivante en cas d'erreur

        log(LogLevel.INFO, Step.DATA_COLLECTION,
            f"Fin du nettoyage des permissions pour le groupe: {group_name} (collections)")

    except Exception as e:
        log(LogLevel.ERROR, Step.DATA_COLLECTION,
            f"Erreur lors du nettoyage des permissions pour {group_name} (collections): {str(e)}")
        raise


def create_or_update_data_collection(dss_client, collection_name, collection_permissions, overwrite=False):
    """
    Crée ou met à jour une collection de données.

    Args:
        dss_client: Client Dataiku
        collection_name: Nom de la collection à créer/mettre à jour
        collection_permissions: Liste des permissions à appliquer
    """
    log(LogLevel.INFO, Step.DATA_COLLECTION, f"Début de la création/mise à jour de la collection: {collection_name}")

    try:
        # Récupération de la liste des collections existantes
        log(LogLevel.DEBUG, Step.DATA_COLLECTION, "Récupération de la liste des collections existantes")
        collections = dss_client.list_data_collections()
        collections_names = [c.display_name for c in collections]
        log(LogLevel.DEBUG, Step.DATA_COLLECTION, f"Collections existantes: {collections_names}")

        # Vérification si la collection existe
        if collection_name not in collections_names:
            log(LogLevel.INFO, Step.DATA_COLLECTION, f"Création de la nouvelle collection: {collection_name}")
            log(LogLevel.DEBUG, Step.DATA_COLLECTION, f"Permissions initiales: {collection_permissions}")

            # Création de la collection
            dss_client.create_data_collection(
                collection_name,
                permissions=collection_permissions
            )

            log(LogLevel.INFO, Step.DATA_COLLECTION, f"Collection {collection_name} créée avec succès")

        else:
            log(LogLevel.INFO, Step.DATA_COLLECTION, f"Mise à jour de la collection existante: {collection_name}")

            # Récupération de la collection existante
            collection = next(c for c in collections if c.display_name == collection_name)

            # Mise à jour des permissions
            collection_obj = dss_client.get_data_collection(collection.get_raw()["id"])
            collection_settings = collection_obj.get_settings()

            log(LogLevel.DEBUG, Step.DATA_COLLECTION,
                f"Permissions avant mise à jour: {collection_settings.permissions}")
            log(LogLevel.DEBUG, Step.DATA_COLLECTION, f"Nouvelle liste de permissions: {collection_permissions}")
            if overwrite:
                collection_settings.permissions = collection_permissions
            else:
                actuel_permissions = collection_settings.permissions
                permissions_dict = {}
                for perm in actuel_permissions:
                    # Utiliser 'group' si disponible, sinon 'user'
                    key = perm.get('group') or perm.get('user')
                    if key:
                        permissions_dict[key] = perm
                # Mise à jour avec les nouvelles permissions
                for new_perm in collection_permissions:
                    group_name = new_perm.get('group') or new_perm.get('user')

                    if group_name in permissions_dict:
                        # Mise à jour des permissions existantes
                        permissions_dict[group_name].update(new_perm)
                    else:
                        # Ajout d'une nouvelle permission
                        permissions_dict[group_name] = new_perm

                collection_settings.permissions = list(permissions_dict.values())
            collection_settings.save()

    except StopIteration:
        log(LogLevel.ERROR, Step.DATA_COLLECTION, f"Collection {collection_name} non trouvée malgré la vérification")
        raise
    except Exception as e:
        log(LogLevel.ERROR, Step.DATA_COLLECTION,
            f"Erreur lors de la création/mise à jour de la collection {collection_name}: {str(e)}")
        raise


def add_dataset_to_data_collection(dss_client, data_collection_name, source_project, datasets, overwrite=False):
    """
    Ajoute des datasets à une collection de données existante.

    Args:
        dss_client: Client Dataiku
        data_collection_name: Nom de la collection de données
        source_project: Clé du projet source des datasets
        datasets: Liste des noms de datasets à ajouter
        overwrite: Si True, supprime les datasets non listés en paramètres
    """
    log(LogLevel.INFO, Step.DATA_COLLECTION, f"Début de l'ajout de datasets à la collection: {data_collection_name}")

    try:
        # Vérification de l'existence de la collection
        log(LogLevel.DEBUG, Step.DATA_COLLECTION, "Vérification de l'existence de la collection")
        collections = dss_client.list_data_collections()
        collections_names = [c.display_name for c in collections]

        if data_collection_name not in collections_names:
            log(LogLevel.WARNING, Step.DATA_COLLECTION, f"Collection {data_collection_name} non trouvée")
            return

        # Récupération de la collection
        log(LogLevel.DEBUG, Step.DATA_COLLECTION, f"Récupération de la collection {data_collection_name}")
        collection = next(c for c in collections if c.display_name == data_collection_name)
        collection_obj = dss_client.get_data_collection(collection.id)

        # Récupération des datasets actuels
        log(LogLevel.DEBUG, Step.DATA_COLLECTION, "Récupération des datasets actuels dans la collection")
        current_datasets_obj = collection_obj.list_objects()
        current_datasets = []

        for cd in current_datasets_obj:
            cd_raw = cd.get_raw()
            if cd_raw["projectKey"] == source_project:
                if overwrite and cd_raw["id"] not in datasets:
                    log(LogLevel.INFO, Step.DATA_COLLECTION,
                        f"Suppression du dataset {cd_raw['id']} (non listé en paramètres)")
                    cd.remove()
                else:
                    current_datasets.append(cd_raw["id"])
                    log(LogLevel.DEBUG, Step.DATA_COLLECTION,
                        f"Dataset {cd_raw['id']} déjà présent dans la collection")

        # Préparation des nouveaux datasets à ajouter
        log(LogLevel.DEBUG, Step.DATA_COLLECTION,
            f"Datasets actuels: {current_datasets}")
        new_datasets = [item for item in datasets if item not in current_datasets]
        log(LogLevel.INFO, Step.DATA_COLLECTION,
            f"Nouveaux datasets à ajouter: {new_datasets}")

        if not new_datasets:
            log(LogLevel.INFO, Step.DATA_COLLECTION, "Aucun nouveau dataset à ajouter")
            return

        # Création des références pour les nouveaux datasets
        log(LogLevel.DEBUG, Step.DATA_COLLECTION, "Création des références pour les nouveaux datasets")
        for dataset in new_datasets:
            reference = {
                "projectKey": source_project,
                "type": "DATASET",
                "id": dataset
            }
            # Ajout des datasets à la collection
            collection_obj.add_object(reference)

        log(LogLevel.INFO, Step.DATA_COLLECTION,
            f"Fin de l'ajout de datasets à la collection: {data_collection_name}")

    except StopIteration:
        log(LogLevel.ERROR, Step.DATA_COLLECTION,
            f"Collection {data_collection_name} non trouvée malgré la vérification")
        raise
    except Exception as e:
        log(LogLevel.ERROR, Step.DATA_COLLECTION,
            f"Erreur lors de l'ajout de datasets à la collection {data_collection_name}: {str(e)}")
        raise
