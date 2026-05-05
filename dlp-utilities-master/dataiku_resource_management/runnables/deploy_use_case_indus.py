from pathlib import Path
from core.parser import build_parser
from core.logger import log, LogLevel, Step
from utils.helpers import load_config
from model.deploy_use_case_indus import UseCaseIndusDeployer


def main():
    log(LogLevel.INFO, Step.MAIN, "Début de l'exécution du script")
    try:
        params = [
            ("design-rd-user-api-key", True),
            ("deployer-api-key", True),
            ("automation-api-key", True),
            ("infra-id", True),
            ("project-key", True),
            ("version", False),
        ]

        parser = build_parser(params)
        args = parser.parse_args()

        design_rd_user_api_key = args.design_rd_user_api_key
        deployer_api_key = args.deployer_api_key
        automation_api_key = args.automation_api_key
        infra_id = args.infra_id
        project_key = args.project_key
        version = args.version if args.version else ""

        # Chargement des configurations
        conf = Path(__file__).parent.parent / 'conf'
        global_config = load_config(conf / 'global_config.json')
        env_config = load_config(conf / infra_id / 'deploy_use_case_indus.json')

        if not global_config or not env_config:
            log(LogLevel.ERROR, Step.MAIN, "Configuration manquante, arrêt du script")
            exit(1)

        design_rd_host = global_config["design_rd"]["host"]
        deployer_host = global_config["deploy"]["host"]
        automation_host = global_config[infra_id]["host"]

        deploy_config = {
            "use_case_groups":                 global_config["use_case_groups"],
            "folder_permissions":              global_config["folder_permissions"],
            "use_case_project_permissions":    env_config["use_case_project_permissions"],
            "data_source_project_permissions": env_config["data_source_project_permissions"],
        }

        log(LogLevel.INFO, Step.MAIN, f"Déploiement du projet '{project_key}' sur infra '{infra_id}'")

        deployer = UseCaseIndusDeployer(
            design_rd_host=design_rd_host,
            design_rd_user_api_key=design_rd_user_api_key,
            deployer_host=deployer_host,
            deployer_api_key=deployer_api_key,
            automation_host=automation_host,
            automation_api_key=automation_api_key,
            project_key=project_key,
            infra_id=infra_id,
            version=version,
            deploy_config=deploy_config
        )
        deployer.run()

        log(LogLevel.INFO, Step.MAIN, f"Fin du déploiement pour le projet '{project_key}'")

    except Exception as e:
        log(LogLevel.ERROR, Step.MAIN, f"Erreur lors de l'exécution du script: {str(e)}")
        exit(1)

    log(LogLevel.INFO, Step.MAIN, "Fin de l'exécution du script")


if __name__ == '__main__':
    main()
