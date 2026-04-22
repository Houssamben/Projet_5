from pathlib import Path
from core.parser import build_parser
from core.logger import log, LogLevel, Step
from utils.helpers import load_config
from model.use_case_indus import UseCaseIndus


def main():
    log(LogLevel.INFO, Step.MAIN, "Début de l'exécution du script")
    try:
        # Configuration des paramètres
        params = [
            ("design-rd-user-api-key", True),
            ("use-case-indus-trigram", False)
        ]

        parser = build_parser(params)
        args = parser.parse_args()

        # Récupération des paramètres
        design_rd_user_api_key = args.design_rd_user_api_key
        use_case_indus_trigram = args.use_case_indus_trigram

        # Chargement des configurations
        global_config = load_config(Path(__file__).parent.parent / 'conf' / 'global_config.json')
        use_case_indus_list = load_config(Path(__file__).parent.parent / 'conf' / 'design_rd' / 'use_case_indus.json')
        use_case_indus_governance = load_config(
            Path(__file__).parent.parent / 'conf' / 'design_rd' / 'use_case_indus_governance.json')

        if not use_case_indus_list or not use_case_indus_governance or not global_config:
            log(LogLevel.ERROR, Step.MAIN, "Configuration manquante, arrêt du script")
            exit(1)

        design_rd_host = global_config["design_rd"]["host"]

        # Exécution pour un use case indus spécifique ou tous les use cases indus
        if use_case_indus_trigram:
            log(LogLevel.INFO, Step.MAIN, f"Exécution pour le use case indus spécifique: {use_case_indus_trigram}")
            if use_case_indus_trigram in use_case_indus_list:
                use_case_indus_config = use_case_indus_list[use_case_indus_trigram]
                use_case_indus = UseCaseIndus(
                    use_case_trigram=use_case_indus_trigram,
                    use_case_config=use_case_indus_config,
                    use_case_gouvernance=use_case_indus_governance,
                    design_rd_host=design_rd_host,
                    design_rd_user_api_key=design_rd_user_api_key
                )
                use_case_indus.run()
                log(LogLevel.INFO, Step.MAIN, f"Fin de traitement pour le use case indus: {use_case_indus_trigram}")
            else:
                log(LogLevel.ERROR, Step.MAIN, f"Use Case Indus {use_case_indus_trigram} non trouvé dans la configuration")
                exit(1)
        else:
            log(LogLevel.INFO, Step.MAIN, "Exécution pour tous les use cases indus")
            for current_use_case_indus_trigram, use_case_indus_config in use_case_indus_list.items():
                log(LogLevel.INFO, Step.MAIN, f"Traitement du use case indus: {current_use_case_indus_trigram}")
                use_case_indus = UseCaseIndus(
                    use_case_trigram=current_use_case_indus_trigram,
                    use_case_config=use_case_indus_config,
                    use_case_gouvernance=use_case_indus_governance,
                    design_rd_host=design_rd_host,
                    design_rd_user_api_key=design_rd_user_api_key
                )
                use_case_indus.run()
                log(LogLevel.INFO, Step.MAIN, f"Fin de traitement pour le use case indus {current_use_case_indus_trigram}")

        log(LogLevel.INFO, Step.MAIN, "Fin de l'exécution du script")
    except Exception as e:
        log(LogLevel.ERROR, Step.MAIN, f"Erreur lors de l'exécution du script: {str(e)}")
        exit(1)


if __name__ == '__main__':
    main()
