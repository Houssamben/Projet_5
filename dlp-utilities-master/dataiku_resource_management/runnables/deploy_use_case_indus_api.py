from pathlib import Path
from core.parser import build_parser
from core.logger import log, LogLevel, Step
from utils.helpers import load_config
from model.deploy_use_case_indus_api import UseCaseIndusAPIDeployer


def main():
    log(LogLevel.INFO, Step.MAIN, "Début de l'exécution du script")
    try:
        params = [
            ("design-rd-user-api-key", True),
            ("deployer-api-key", True),
            ("project-key", True),
            ("api-service-id", True),
            ("infra-id", True),
            ("api-version", False),
        ]

        parser = build_parser(params)
        args = parser.parse_args()

        design_rd_user_api_key = args.design_rd_user_api_key
        deployer_api_key = args.deployer_api_key
        project_key = args.project_key
        api_service_id = args.api_service_id
        infra_id = args.infra_id
        api_version = args.api_version if args.api_version else ""

        # Chargement des configurations
        global_config = load_config(Path(__file__).parent.parent / 'conf' / 'global_config.json')
        api_config = load_config(
            Path(__file__).parent.parent / 'conf' / 'design_rd' / 'package_use_case_indus_api.json'
        )

        if not global_config or not api_config:
            log(LogLevel.ERROR, Step.MAIN, "Configuration manquante, arrêt du script")
            exit(1)

        design_rd_host = global_config["design_rd"]["host"]
        deployer_host = global_config["deploy"]["host"]
        api_groups_permissions = api_config["api_groups_permissions"]

        log(LogLevel.INFO, Step.MAIN, f"Déploiement API du projet '{project_key}' sur infra '{infra_id}'")

        deployer = UseCaseIndusAPIDeployer(
            design_rd_host=design_rd_host,
            design_rd_user_api_key=design_rd_user_api_key,
            project_key=project_key,
            deployer_host=deployer_host,
            deployer_api_key=deployer_api_key,
            api_service_id=api_service_id,
            infra_id=infra_id,
            api_version=api_version,
            api_groups_permissions=api_groups_permissions
        )
        deployer.run()

        log(LogLevel.INFO, Step.MAIN, f"Fin du déploiement API pour le projet '{project_key}'")

    except Exception as e:
        log(LogLevel.ERROR, Step.MAIN, f"Erreur lors de l'exécution du script: {str(e)}")
        exit(1)

    log(LogLevel.INFO, Step.MAIN, "Fin de l'exécution du script")


if __name__ == '__main__':
    main()
