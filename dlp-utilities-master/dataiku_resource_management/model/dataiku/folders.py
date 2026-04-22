from core.logger import log, LogLevel, Step

def get_or_create_folder(dss_client, parent_folder, folder_name, folder_permissions):
    log(LogLevel.INFO, Step.FOLDER, f"Début du traitement du dossier: {folder_name}")
    try:
        child_folders = parent_folder.list_child_folders()

        folder_id = None
        for child_folder in child_folders:
            if child_folder.name == folder_name:
                folder_id = child_folder.id

        if folder_id is None:
            log(LogLevel.INFO, Step.FOLDER, f"Création du nouveau dossier: {folder_name}")
            folder = parent_folder.create_sub_folder(folder_name)
        else:
            log(LogLevel.INFO, Step.FOLDER, f"Utilisation du dossier existant: {folder_name}")
            folder = dss_client.get_project_folder(folder_id)

        folder_settings = folder.get_settings()
        folder_settings_permissions = folder_settings.get_permissions()
        granted_groups = [p["group"] for p in folder_settings_permissions]
        for perm in folder_permissions:
            if perm["group"] in granted_groups:
                for p in folder_settings_permissions:
                    if p["group"] == perm["group"]:
                        p.update(perm)
                        break
            else:
                folder_settings_permissions.append(perm)

        folder_settings.save()
        log(LogLevel.INFO, Step.FOLDER, f"Fin du traitement du dossier: {folder_name}")
        return folder
    except Exception as e:
        log(LogLevel.ERROR, Step.FOLDER, f"Erreur lors du traitement du dossier {folder_name}: {str(e)}")
        raise