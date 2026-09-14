from logging_handler import INFO
from .config import ConfigDict, ConfigList
from .config_yaml import ConfigManagerYamlDict
from .config_json import ConfigManagerJsonDict
from .crypto import generate_encryption_key
from .database import ConfigManagerDB


VERSION = (1, 0, 6)    # updated 2026-09-13 22:23:42.358116 from : (1, 0, 5)


def load_file(filename:str, encryption_key:bytes|None=None, encryption_key_file:str|None=None, log_level=INFO, save_on_change=False):
    ''' Load a config file and return a ConfigDict or ConfigList based on the file extension '''
    if filename.endswith('.json'):
        return ConfigManagerJsonDict(config_file=filename, log_level=log_level, encryption_key=encryption_key, encryption_key_file=encryption_key_file, save_on_change=save_on_change)
    if filename.endswith('.yaml') or filename.endswith('.yml'):
        return ConfigManagerYamlDict(config_file=filename, log_level=log_level, encryption_key=encryption_key, encryption_key_file=encryption_key_file, save_on_change=save_on_change)
    raise ValueError(f"Unsupported config file type for file '{filename}'")


def load_sqlite3_db(filename:str, table:str='kv', encryption_key:bytes|None=None, encryption_key_file:str|None=None, log_level=INFO, **kwargs):
    ''' Load or create a SQLite3 database and return a ConfigManagerDB instance '''
    return ConfigManagerDB(database=filename, db_type='sqlite3', table=table, log_level=log_level, encryption_key=encryption_key, encryption_key_file=encryption_key_file, **kwargs)


def load_mysql_db(host:str, user:str, password:str, database:str, table:str='kv', encryption_key:bytes|None=None, encryption_key_file:str|None=None, log_level=INFO, **kwargs):
    ''' Load a MySQL database and return a ConfigManagerDB instance '''
    return ConfigManagerDB(host=host, db_type='mysql',user=user, password=password, database=database, table=table, log_level=log_level, encryption_key=encryption_key,
                           encryption_key_file=encryption_key_file, **kwargs)
