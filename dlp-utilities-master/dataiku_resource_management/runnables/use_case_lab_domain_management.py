from pathlib import Path
from core.parser import build_parser
from core.logger import log, LogLevel, Step
from utils.helpers import load_config
from model.use_case_lab_domain import UseCaseLabDomain

def main():
    log(LogLevel.INFO, Step.MAIN, "Début de l'exécution du script")
    try:
        # Configuration des paramètres
        params = [
            ("design-rd-user-api-key", True),
            ("domain-code", False)
        ]

        parser = build_parser(params)
        args = parser.parse_args()

        # Récupération des paramètres
        design_rd_user_api_key = args.design_rd_user_api_key
        domain_code = args.domain_code

        # Chargement des configurations
        global_config = load_config(Path(__file__).parent.parent / 'conf' / 'global_config.json')
        domain_config_list = load_config(Path(__file__).parent.parent / 'conf' / 'design_rd' / 'lab_domain.json')
        lab_domain_gouvernance = load_config(Path(__file__).parent.parent / 'conf' / 'design_rd' / 'lab_domain_governance.json')

        if not domain_config_list or not lab_domain_gouvernance or not global_config:
            log(LogLevel.ERROR, Step.MAIN, "Configuration manquante, arrêt du script")
            exit(1)

        design_rd_host = global_config["design_rd"]["host"]

        # Exécution pour un domaine spécifique ou tous les domaines
        if domain_code:
            log(LogLevel.INFO, Step.MAIN, f"Exécution pour le domaine spécifique: {domain_code}")
            if domain_code in domain_config_list:
                domain_config = domain_config_list[domain_code]
                lab_domain = UseCaseLabDomain(
                    domain_code,
                    domain_config,
                    lab_domain_gouvernance,
                    design_rd_host=design_rd_host,
                    design_rd_user_api_key=design_rd_user_api_key
                )
                lab_domain.run()
                log(LogLevel.INFO, Step.MAIN, f"Fin de traitement pour le domaine: {domain_code}")
            else:
                log(LogLevel.ERROR, Step.MAIN, f"Domaine {domain_code} non trouvé dans la configuration")
                exit(1)
        else:
            log(LogLevel.INFO, Step.MAIN, "Exécution pour tous les domaines")
            for current_domain_code, domain_config in domain_config_list.items():
                log(LogLevel.INFO, Step.MAIN, f"Traitement du domaine: {current_domain_code}")
                lab_domain = UseCaseLabDomain(
                    current_domain_code,
                    domain_config,
                    lab_domain_gouvernance,
                    design_rd_host=design_rd_host,
                    design_rd_user_api_key=design_rd_user_api_key
                )
                lab_domain.run()
                log(LogLevel.INFO, Step.MAIN, f"Fin de traitement pour le domaine {current_domain_code}")

        log(LogLevel.INFO, Step.MAIN, "Fin de l'exécution du script")
    except Exception as e:
        log(LogLevel.ERROR, Step.MAIN, f"Erreur lors de l'exécution du script: {str(e)}")
        exit(1)

if __name__ == '__main__':
    main()