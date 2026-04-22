from core.logger import log, LogLevel, Step

def create_or_update_group(dss_client, group_name, group_description=None, group_source_type='LOCAL', ssoGroupNames=[],
                           group_permissions={}):
    log(LogLevel.INFO, Step.GROUP, f"Début de la création/mise à jour du groupe: {group_name}")
    try:
        groups = dss_client.list_groups()
        use_case_group_name = next((group["name"] for group in groups if group["name"] == group_name), None)
        if use_case_group_name is None:
            log(LogLevel.INFO, Step.GROUP, f"Création du nouveau groupe: {group_name}")
            use_case_group = dss_client.create_group(group_name, description=group_description,
                                                     source_type=group_source_type)
        else:
            use_case_group = dss_client.get_group(use_case_group_name)
            log(LogLevel.INFO, Step.GROUP, f"Mise à jour du groupe existant: {group_name}")

        group_definition = use_case_group.get_definition()

        group_definition["sourceType"] = group_source_type
        group_definition["ssoGroupNames"] = ssoGroupNames
        group_definition.update(group_permissions)
        use_case_group.set_definition(group_definition)
        log(LogLevel.INFO, Step.GROUP, f"Fin de la création/mise à jour du groupe: {group_name}")
    except Exception as e:
        log(LogLevel.ERROR, Step.GROUP, f"Erreur lors de la création/mise à jour du groupe {group_name}: {str(e)}")
        raise