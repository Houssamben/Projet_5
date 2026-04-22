import argparse

def build_parser(params):
    parser = argparse.ArgumentParser(description='Script de gestion des domaines Lab')
    for param, required in params:
        parser.add_argument(f"--{param}", required=required)
    return parser