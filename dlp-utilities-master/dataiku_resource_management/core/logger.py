from datetime import datetime
from enum import Enum

class LogLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"

class Step(Enum):
    MAIN = "MAIN"
    CONFIG = "CONFIG"
    INIT = "INIT"
    RUN = "RUN"
    PROCESS = "PROCESS"
    GROUP = "GROUP"
    FOLDER = "FOLDER"
    DATA_COLLECTION = "DATA_COLLECTION"
    CODE_ENV = "CODE_ENV"
    PROJECT = "PROJECT"
    CONNECTION = "CONNECTION"
    DEPLOY = "DEPLOY"
    PACKAGE = "PACKAGE"
    BUNDLE = "BUNDLE"
    API_DEPLOY = "API_DEPLOY"
    API_PACKAGE = "API_PACKAGE"

def log(level: LogLevel, step: Step, message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] [{level.value}] [{step}] {message}"
    print(log_message)