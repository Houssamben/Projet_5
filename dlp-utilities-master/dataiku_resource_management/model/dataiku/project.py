from core.logger import log, LogLevel, Step

from core.logger import log, LogLevel, Step


def get_or_create_project(dss_client, project_key, project_name, project_description,
                          project_owner, project_settings, folder_id):
    """
    Crée un projet s'il n'existe pas déjà.

    Args:
        dss_client: Client Dataiku
        project_key: Clé du projet
        project_name: Nom du projet
        project_description: Description du projet
        project_owner: Propriétaire du projet
        project_settings: Paramètres du projet
        folder_id: ID du dossier parent

    Returns:
        Objet projet Dataiku
    """
    log(LogLevel.INFO, Step.PROJECT, f"Début de la création/récupération du projet: {project_key}")

    try:
        # Récupération de la liste des projets existants
        log(LogLevel.DEBUG, Step.PROJECT, "Récupération de la liste des projets existants")
        projects = [p["projectKey"] for p in dss_client.list_projects()]
        log(LogLevel.DEBUG, Step.PROJECT, f"Projets existants: {projects}")

        # Vérification si le projet existe
        if project_key not in projects:
            log(LogLevel.INFO, Step.PROJECT, f"Création du nouveau projet: {project_key}")
            log(LogLevel.DEBUG, Step.PROJECT,
                f"Paramètres de création: name={project_name}, owner={project_owner}, folder_id={folder_id}")

            # Création du projet
            project = dss_client.create_project(
                project_key,
                project_name,
                owner=project_owner,
                description=project_description,
                settings=project_settings,
                project_folder_id=folder_id
            )

            log(LogLevel.INFO, Step.PROJECT, f"Projet {project_key} créé avec succès")
            return project
        else:
            log(LogLevel.INFO, Step.PROJECT, f"Récupération du projet existant: {project_key}")
            project = dss_client.get_project(project_key)
            log(LogLevel.INFO, Step.PROJECT, f"Projet {project_key} récupéré avec succès")
            return project

    except Exception as e:
        log(LogLevel.ERROR, Step.PROJECT,
            f"Erreur lors de la création/récupération du projet {project_key}: {str(e)}")
        raise


def set_project_permissions(project, project_permissions, overwrite=False):
    """
    Attribue des permissions à un projet.

    Args:
        project: Objet projet Dataiku
        project_permissions: Liste de permissions à appliquer
        overwrite: Si True, remplace toutes les permissions existantes

    """
    log(LogLevel.INFO, Step.PROJECT, f"Début de la configuration des permissions pour le projet: {project.get_summary()['projectKey']}")

    try:
        # Récupération des permissions actuelles
        log(LogLevel.DEBUG, Step.PROJECT, "Récupération des permissions actuelles du projet")
        permissions = project.get_permissions()
        log(LogLevel.DEBUG, Step.PROJECT, f"Permissions actuelles: {permissions}")

        # Gestion des permissions selon le mode
        if overwrite:
            log(LogLevel.INFO, Step.PROJECT, "Remplacement de toutes les permissions existantes")
            permissions["permissions"] = project_permissions
            log(LogLevel.DEBUG, Step.PROCESS, f"Nouvelle liste de permissions: {project_permissions}")
        else:
            log(LogLevel.INFO, Step.PROJECT, "Ajout des nouvelles permissions aux permissions existantes")
            for perm in project_permissions:
                log(LogLevel.DEBUG, Step.PROCESS, f"Ajout de la permission: {perm}")
                permissions["permissions"].append(perm)

        # Vérification des permissions finales
        log(LogLevel.DEBUG, Step.PROJECT, f"Permissions finales: {permissions['permissions']}")

        # Application des permissions
        log(LogLevel.DEBUG, Step.PROJECT, "Application des permissions au projet")
        project.set_permissions(permissions)

        log(LogLevel.INFO, Step.PROJECT, f"Fin de la configuration des permissions pour le projet: {project.get_summary()['projectKey']}")

    except Exception as e:
        log(LogLevel.ERROR, Step.PROJECT,
            f"Erreur lors de la configuration des permissions pour le projet {project.get_summary()['projectKey']}: {str(e)}")
        raise


def set_project_code_env(project, code_env_name):
    """
    Configure l'environnement de code Python pour un projet.

    Args:
        project: Objet projet Dataiku
        code_env_name: Nom de l'environnement de code à appliquer
    """
    log(LogLevel.INFO, Step.PROJECT, f"Début de la configuration de l'environnement de code pour le projet: {project.get_summary()['projectKey']}")
    log(LogLevel.DEBUG, Step.PROJECT, f"Environnement de code cible: {code_env_name}")

    try:
        # Récupération des paramètres actuels
        log(LogLevel.DEBUG, Step.PROJECT, "Récupération des paramètres actuels du projet")
        project_settings = project.get_settings()

        # Configuration de l'environnement de code
        log(LogLevel.INFO, Step.PROJECT, f"Configuration de l'environnement de code: {code_env_name}")
        project_settings.set_python_code_env(code_env_name)

        # Sauvegarde des paramètres
        log(LogLevel.DEBUG, Step.PROJECT, "Sauvegarde des paramètres du projet")
        project_settings.save()

    except Exception as e:
        log(LogLevel.ERROR, Step.PROJECT,
            f"Erreur lors de la configuration de l'environnement de code pour le projet {project.get_summary()['projectKey']}: {str(e)}")
        raise
