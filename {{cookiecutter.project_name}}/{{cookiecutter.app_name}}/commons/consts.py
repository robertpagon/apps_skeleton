'''
    Konstante koje koriste skripte
    Globalne varijable
'''
ROOT_DIR = '{{cookiecutter.app_name}}'
BIN_DIR = f"{ROOT_DIR}/bin"  # Ovo se trenutno ne koristi, valjda bi se koristilo u deploymentu
LOG_DIR = f"{ROOT_DIR}/log"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

PODVUCI = '-'*80

