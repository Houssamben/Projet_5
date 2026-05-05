import json
from pathlib import Path
from core.parser import build_parser
from core.logger import log, LogLevel, Step
from utils.helpers import load_config
from model.package_use_case_indus import PackageUseCaseIndus


def main():
    log(LogLevel.INFO, Step.MAIN, "Début de l'exécution du script")
    try:
        params = [
            ("design-rd-user-api-key", True),
            ("deployer-api-key", True),
        ]

        parser = build_parser(params)
        args = parser.parse_args()

        design_rd_user_api_key = args.design_rd_user_api_key
        deployer_api_key = args.deployer_api_key

        print("[INFO] Executing step: reading project key from params.json")
        with open('params.json', 'r') as f:
            project_key = json.load(f).get("name")
        print(f"[INFO] project_key = {project_key}")

        # Chargement des configurations
        conf = Path(__file__).parent.parent / 'conf'
        global_config = load_config(conf / 'global_config.json')
        design_rd_config = load_config(conf / 'design_rd' / 'package_use_case_indus.json')

        if not global_config or not design_rd_config:
            log(LogLevel.ERROR, Step.MAIN, "Configuration manquante, arrêt du script")
            exit(1)

        design_rd_host = global_config["design_rd"]["host"]
        deployer_host = global_config["deploy"]["host"]

        package_config = {
            "use_case_groups":              global_config["use_case_groups"],
            "deployer_project_permissions": design_rd_config["deployer_project_permissions"],
        }

        log(LogLevel.INFO, Step.MAIN, f"Packaging du projet '{project_key}'")

        packager = PackageUseCaseIndus(
            project_key=project_key,
            design_rd_host=design_rd_host,
            design_rd_user_api_key=design_rd_user_api_key,
            deployer_host=deployer_host,
            deployer_api_key=deployer_api_key,
            package_config=package_config
        )
        packager.run()

        log(LogLevel.INFO, Step.MAIN, f"Fin du packaging pour le projet '{project_key}'")

    except Exception as e:
        log(LogLevel.ERROR, Step.MAIN, f"Erreur lors de l'exécution du script: {str(e)}")
        exit(1)

    log(LogLevel.INFO, Step.MAIN, "Fin de l'exécution du script")


if __name__ == '__main__':
    main()
