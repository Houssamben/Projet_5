from core.logger import log, LogLevel, Step

def create_or_update_code_env(dss_client, code_env_name, code_env_permissions):
    """Crée ou met à jour un environnement de code dans Dataiku"""
    log(LogLevel.INFO, Step.CODE_ENV, f"Début de la création/mise à jour de l'environnement de code: {code_env_name}")

    try:
        code_env_lang = "PYTHON"
        log(LogLevel.DEBUG, Step.CODE_ENV, f"Langage de l'environnement: {code_env_lang}")

        # Récupération de la liste des environnements existants
        log(LogLevel.DEBUG, Step.CODE_ENV, "Récupération de la liste des environnements de code existants")
        code_env_list = dss_client.list_code_envs(as_objects=False)
        code_env_name_list = [code_env['envName'] for code_env in code_env_list]
        log(LogLevel.DEBUG, Step.CODE_ENV, f"Environnements existants: {code_env_name_list}")

        # Création ou mise à jour de l'environnement
        if code_env_name not in code_env_name_list:
            log(LogLevel.INFO, Step.CODE_ENV, f"Création du nouvel environnement de code: {code_env_name}")
            code_env = dss_client.create_code_env(
                env_lang=code_env_lang,
                env_name=code_env_name,
                deployment_mode="DESIGN_MANAGED"
            )
        else:
            log(LogLevel.INFO, Step.CODE_ENV, f"Mise à jour de l'environnement de code existant: {code_env_name}")
            code_env = dss_client.get_code_env(code_env_lang, code_env_name)

        # Configuration des paramètres
        log(LogLevel.DEBUG, Step.CODE_ENV, "Configuration des paramètres de l'environnement")
        code_env_settings = code_env.get_settings()

        log(LogLevel.DEBUG, Step.CODE_ENV, "Mise à jour des paramètres de base")
        code_env_settings.settings["desc"]["owner"] = "admin"
        code_env_settings.settings["usableByAll"] = False
        code_env_settings.settings["permissions"] = code_env_permissions
        code_env_settings.settings["desc"]["installCorePackages"] = True
        code_env_settings.settings["desc"]["installJupyterSupport"] = True

        log(LogLevel.DEBUG, Step.CODE_ENV, f"Permissions configurées: {code_env_permissions}")

        # Sauvegarde des paramètres
        log(LogLevel.DEBUG, Step.CODE_ENV, "Sauvegarde des paramètres de l'environnement")
        code_env_settings.save()

        # Mise à jour des packages
        log(LogLevel.INFO, Step.CODE_ENV, "Mise à jour des packages de l'environnement")
        code_env.update_packages()

        # Activation du support Jupyter
        log(LogLevel.INFO, Step.CODE_ENV, "Activation du support Jupyter")
        code_env.set_jupyter_support(active=True)

        log(LogLevel.INFO, Step.CODE_ENV, f"Fin de la création/mise à jour de l'environnement de code: {code_env_name}")

    except Exception as e:
        log(LogLevel.ERROR, Step.CODE_ENV,
            f"Erreur lors de la création/mise à jour de l'environnement de code {code_env_name}: {str(e)}")
        raise