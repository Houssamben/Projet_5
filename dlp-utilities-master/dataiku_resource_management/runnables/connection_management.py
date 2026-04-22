from pathlib import Path
from core.parser import build_parser
from core.logger import log, LogLevel, Step
from model.dataikuConnection import DataikuConnection
from utils.helpers import load_config


def main():
    log(LogLevel.INFO, Step.MAIN, "Début de l'exécution du script")
    try:
        # Configuration des paramètres
        params = [
            ("node-name", True),
            ("node-api-key", True),
            ("connection-name", False),
            ("connection-access-key", False),
            ("connection-secret-key", False),
            ("connection-user", False),
            ("connection-password", False)
        ]

        parser = build_parser(params)
        args = parser.parse_args()

        # Récupération des paramètres
        node_name = args.node_name
        node_api_key = args.node_api_key
        connection_name = args.connection_name
        connection_access_key = args.connection_access_key
        connection_secret_key = args.connection_secret_key
        connection_user = args.connection_user
        connection_password = args.connection_password

        # Chargement des configurations
        global_config = load_config(Path(__file__).parent.parent / 'conf' / 'global_config.json')

        # Vérification que le node_name est dans la configuration globale
        if node_name not in global_config:
            log(LogLevel.ERROR, Step.MAIN, f"Node {node_name} non trouvé dans la configuration globale")
            exit(1)

        use_case_indus = load_config(
            Path(__file__).parent.parent / 'conf' / f'{node_name}' / 'use_case_indus.json')
        use_case_indus_governance = load_config(
            Path(__file__).parent.parent / 'conf' / f'{node_name}' / 'use_case_indus_governance.json')
        lab_domain = {}
        lab_domain_governance = {}
        if node_name == "design_rd":
            lab_domain = load_config(Path(__file__).parent.parent / 'conf' / 'design_rd' / 'lab_domain.json')
            lab_domain_governance = load_config(
                Path(__file__).parent.parent / 'conf' / 'design_rd' / 'lab_domain_governance.json')

        global_connection = load_config(
            Path(__file__).parent.parent / 'conf' / f'{node_name}' / 'global_connection.json')
        global_connection_governance = load_config(
            Path(__file__).parent.parent / 'conf' / f'{node_name}' / 'global_connection_governance.json')
        use_case_connection = load_config(
            Path(__file__).parent.parent / 'conf' / f'{node_name}' / 'use_case_connection.json')
        use_case_connection_governance = load_config(
            Path(__file__).parent.parent / 'conf' / f'{node_name}' / 'use_case_connection_governance.json')

        if ((not global_config) or
                (not use_case_indus) or
                (not use_case_indus_governance) or
                (not global_connection) or
                (not global_connection_governance) or
                (not use_case_connection) or
                (not use_case_connection_governance) or
                (not lab_domain and node_name == "design_rd") or
                (not lab_domain_governance and node_name == "design_rd")):
            log(LogLevel.ERROR, Step.MAIN, "Configuration manquante, arrêt du script")
            exit(1)

        connections = []

        #Global
        for env, env_cfg in global_connection.items():
            for conn_type in ('cos_connection', 'db_connection'):
                for conn in env_cfg.get(conn_type, []):
                    if conn_type == 'cos_connection':
                        formatted_name = f"s3-{conn['name']}-{conn['cos']}"
                    else:
                        if 'resource' in conn:
                            formatted_name = f"db-{conn['name']}-{conn['resource']}"
                        else:
                            formatted_name = conn['name']

                    connections.append({
                        'name': formatted_name,
                        'type': conn_type,
                        'scope': 'global',
                        'env': env,
                        'config': conn
                    })

        #Use‑case
        for uc, uc_cfg in use_case_connection.items():
            for conn_type in ('cos_connection', 'db_connection'):
                for conn in uc_cfg.get(conn_type, []):
                    if conn_type == 'cos_connection':
                        formatted_name = f"s3-{conn['name']}-{conn['cos']}"
                    else:
                        if 'resource' in conn:
                            formatted_name = f"db-{conn['name']}-{conn['resource']}"
                        else:
                            formatted_name = conn['name']
                    connections.append({
                        'name': formatted_name,
                        'type': conn_type,
                        'scope': 'use_case',
                        'use_case': uc,
                        'config': conn
                    })

        use_case_indus_index = {}
        if use_case_indus:
            for uc, uc_info in use_case_indus.items():
                for name in uc_info.get('cos_connection', []) + uc_info.get('db_connection', []):
                    use_case_indus_index[name] = {
                        'use_case': uc,
                        'ap_code': uc_info.get('ap_code'),
                        'lots': uc_info.get('lots', [])
                    }

        lab_domain_index = {}
        if node_name == 'design_rd' and lab_domain:
            for lab, lab_cfg in lab_domain.items():
                for ct in ('cos_connection', 'db_connection'):
                    for c in lab_cfg.get(ct, []):
                        lab_domain_index.setdefault(c, set()).add(lab)

        for conn in connections:
            name = conn['name']

            if name in use_case_indus_index:
                uc_ctx = use_case_indus_index[name]
                conn['scope'] = 'use_case_indus'
                conn['use_case'] = uc_ctx['use_case']
                conn['ap_code'] = uc_ctx['ap_code']
                conn['lots'] = uc_ctx['lots']
                continue

            if name in lab_domain_index:
                conn['scope'] = 'lab_domain'
                conn['lab'] = sorted(lab_domain_index[name])
                conn.pop('use_case', None)

        if connection_name:
            connection = next((c for c in connections if c['name'] == connection_name), None)
            if not connection:
                log(LogLevel.ERROR, Step.MAIN,
                    f"Connexion '{connection_name}' introuvable parmi les {len(connections)} ")
                exit(1)

            vault_informations = {}
            if connection_access_key:
                log(LogLevel.INFO, Step.MAIN, f"Prise en compte de l'access key pour {connection_name}.")
                vault_informations["access_key"] = connection_access_key
            if connection_secret_key:
                log(LogLevel.INFO, Step.MAIN, f"Prise en compte de la secret key pour {connection_name}.")
                vault_informations["secret_key"] = connection_secret_key
            if connection_user:
                log(LogLevel.INFO, Step.MAIN, f"Prise en compte du user pour {connection_name}.")
                vault_informations["user"] = connection_user
            if connection_password:
                log(LogLevel.INFO, Step.MAIN, f"Prise en compte du password pour {connection_name}.")
                vault_informations["password"] = connection_password

            dataiku_connection = DataikuConnection(
                connection_config=connection,
                vault_informations=vault_informations,
                use_case_connection_governance=use_case_connection_governance,
                global_connection_governance=global_connection_governance,
                host=global_config[node_name]["host"],
                api_key=node_api_key
            )
            dataiku_connection.run()
            log(LogLevel.INFO, Step.MAIN, f"Fin de traitement pour la connecion: {connection_name}")
        else:
            for connection in connections:
                dataiku_connection = DataikuConnection(
                    connection_config=connection,
                    vault_informations={},
                    use_case_connection_governance=use_case_connection_governance,
                    global_connection_governance=global_connection_governance,
                    host=global_config[node_name]["host"],
                    api_key=node_api_key
                )
                dataiku_connection.run()
                log(LogLevel.INFO, Step.MAIN, f"Fin de traitement pour la connecion: {connection['name']}")

        log(LogLevel.INFO, Step.MAIN, "Fin de l'exécution du script")
    except Exception as e:
        log(LogLevel.ERROR, Step.MAIN, f"Erreur lors de l'exécution du script: {str(e)}")
        exit(1)


if __name__ == '__main__':
    main()
