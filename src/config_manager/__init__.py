from logging_handler import INFO
from .config import ConfigDict, ConfigList
from .config_yaml import ConfigManagerYamlDict
from .config_json import ConfigManagerJsonDict
from .crypto import generate_encryption_key


VERSION = (1,0,0)


def load_file(filename:str, encryption_key:bytes|None=None, encryption_key_file:str|None=None, log_level=INFO, save_on_change=False):
    ''' Load a config file and return a ConfigDict or ConfigList based on the file extension '''
    if filename.endswith('.json'):
        return ConfigManagerJsonDict(config_file=filename, log_level=log_level, encryption_key=encryption_key, encryption_key_file=encryption_key_file, save_on_change=save_on_change)
    if filename.endswith('.yaml') or filename.endswith('.yml'):
        return ConfigManagerYamlDict(config_file=filename, log_level=log_level, encryption_key=encryption_key, encryption_key_file=encryption_key_file, save_on_change=save_on_change)
    raise ValueError(f"Unsupported config file type for file '{filename}'")
