from collections.abc import Iterable
from logging_handler import INFO
from typing import Any, Callable
import json
from .config import ConfigDict, ConfigList
from .crypto import encrypt_data, decrypt_data
from .config_json import ConfigJsonEncoder


class DBConnectError(Exception):
    ''' Issue with the database connection '''

class DBTableCreateError(Exception):
    ''' Issue creating the DB table '''

class DBTableFormatError(Exception):
    ''' Issue with the format of the database table '''

class DBQueryError(Exception):
    ''' Issue with data returned from the database '''

class DBNotFound(Exception):
    ''' Raised when a result is not found in the database '''

class DBCryptoError(Exception):
    ''' Raised when an error occurs when attempting to encrypt or decrypt a key '''

MYSQL = 'mysql'
MARIADB = 'mysql'
SQLITE3 = 'sqlite3'

TABLE_COLUMNS = ('k', 'v', 'cast', 'encrypted') # order of the columns for sqlite3 that returns a tuple instead of a dict

SUPPORTED_DB_TYPES = "Supported DB types are 'mysql' for MYSQL and MARIADB and 'sqlite3' for SQLITE3."

CREATE_TABLE = {
    MYSQL: """CREATE TABLE `{table}` (
                `k` varchar(45) NOT NULL,
                `v` text,
                `cast` varchar(45),
                `encrypted` tinyint(3) unsigned zerofill NOT NULL DEFAULT '000',
                PRIMARY KEY (`k`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;""",
    SQLITE3: """CREATE TABLE `{table}` (
                `k` varchar(45) NOT NULL,
                `v` text,
                `cast` varchar(45),
                `encrypted` tinyint(3) NOT NULL DEFAULT '000',
                PRIMARY KEY (`k`)
                );"""
}

KEY_ENCRYPTED = {
    MYSQL: "SELECT encrypted FROM `{table}` WHERE k='{key}';",
    SQLITE3: "SELECT encrypted FROM `{table}` WHERE k='{key}';"
}

ENCRYPTED_FORMATS = {
    0: None,
    1: 'Fernet'
}

CHECK_TABLE = {
    MYSQL: "SHOW COLUMNS in `{table}`;",
    SQLITE3: "PRAGMA table_info('{table}')"
}

CHECK_TABLE_K = {
    MYSQL: {'Field': 'k', 'Type': 'varchar(45)', 'Null': 'NO', 'Key': 'PRI', 'Default': None},
    SQLITE3: (0, 'k', 'varchar(45)', 1, None, 1)
}

CHECK_TABLE_V = {
    MYSQL: {'Field': 'v', 'Type': 'text', 'Null': 'YES', 'Key': '', 'Default': None},
    SQLITE3: (1, 'v', 'TEXT', 0, None, 0)
}

CHECK_TABLE_CAST = {
    MYSQL: {'Field': 'cast', 'Type': 'varchar(45)', 'Null': 'YES', 'Key': '', 'Default': None},
    SQLITE3: (2, 'cast', 'varchar(45)', 0, None, 0)
}

CHECK_TABLE_ENCRYPTED = {
    MYSQL: {'Field': 'encrypted', 'Type': 'tinyint(3) unsigned zerofill', 'Null': 'NO', 'Key': '', 'Default': '000'},
    SQLITE3: (3, 'encrypted', 'tinyint(3)', 1, "'000'", 0)
}

SET_ITEM = {
    MYSQL: """INSERT INTO {table} (`k`, `v`, `cast`, `encrypted`)
              VALUES ('{k}', '{v}', '{cast}', '{encrypted}')
              ON DUPLICATE KEY UPDATE
                `v` = '{v}',
                `cast` = '{cast}',
                `encrypted` = '{encrypted}'; """,
    SQLITE3: """INSERT INTO {table} (`k`, `v`, `cast`, `encrypted`)
              VALUES ('{k}', '{v}', '{cast}', '{encrypted}')
              ON CONFLICT(`k`)
              DO UPDATE SET
                `v` = '{v}',
                `cast` = '{cast}',
                `encrypted` = '{encrypted}'; """

}

GET_ITEM = {
    MYSQL: """SELECT `k`, `v`, `cast`, `encrypted` FROM {table}
              WHERE k = '{k}';""",
    SQLITE3: """SELECT `k`, `v`, `cast`, `encrypted` FROM {table}
              WHERE k = '{k}';"""
}

DEL_ITEM = {
    MYSQL: """DELETE FROM `{database}`.`{table}`
              WHERE `k` = '{k}';""",
    SQLITE3: """DELETE FROM `{table}`
              WHERE `k` = '{k}';"""
}

TABLE_LENGTH = {
    MYSQL: "select count(k) as length from {table};",
    SQLITE3: "select count(k) as length from {table};",
}

GET_KEYS = {
    MYSQL: "SELECT k from {table};",
    SQLITE3: "SELECT k from {table};"
}

CAST_TYPES = {
    'int': int,
    'float': float,
    'dict': json.loads,
    'list': json.loads,
    'tuple': tuple
}


class ConfigDictDB(ConfigDict):
    ''' Represent a dict object loaded from the database '''
    def __init__(self, data:str|dict, key:str, callback:Callable, **kwargs):
        if isinstance(data, str):
            data = json.loads(data)
        super().__init__(data, update_callback=self._save_callback, **kwargs)
        self._key, self._db_callback = key, callback

    def _save_callback(self):
        ''' Save the configuration back to the database '''
        self._db_callback(self._key, self.data)


class ConfigListDB(ConfigList):
    ''' Represent a list object loaded from the database '''
    def __init__(self, data:str|list, key:str, callback:Callable, **kwargs):
        if isinstance(data, str):
            data = json.loads(data)
        super().__init__(data, update_callback=self._save_callback, **kwargs)
        self._key, self._db_callback = key, callback

    def _save_callback(self):
        ''' Save the configuration back to the database '''
        self._db_callback(self._key, self.data)


class ConfigManagerDB(ConfigDict):
    ''' A config manager that can load config data from a SQL database. The config data should be stored in a table with 'k' and 'v' columns for key and value, respectively. '''
    def __init__(self, *args, database:str, table:str='kv', db_type:str=MYSQL, log_level=INFO, encryption_key:bytes|None=None, encryption_key_file:str|None=None, encryption_format:str='Fernet', **kwargs):
        super().__init__(log_level=log_level)
        self._log_level = log_level
        self._table, self._db_type = table, db_type
        self._encryption_key, self._encryption_format = encryption_key, encryption_format

        if encryption_key_file is not None:
            with open(encryption_key_file, 'rb') as input_file:
                self._encryption_key = input_file.read()

        # init connection to database
        if db_type == MYSQL: # MYSQL and MARIADB
            try:
                import pymysql
                self._logger.debug(f"Connecting to database {kwargs.get('host')}, {database}...")
                self._db_conn = pymysql.connect(database=database, cursorclass=pymysql.cursors.DictCursor, **kwargs)
                if not self.connected():
                    raise DBConnectError("Database not connected")
            except Exception as e:
                raise DBConnectError(f"Database connection error: {e.__class__.__name__}: {e}") from e
        elif db_type == SQLITE3:
            try:
                import sqlite3
                self._logger.debug(f"Connecting to SQLITE3 database {database}")
                self._db_conn = sqlite3.connect(database=database, **kwargs)
                self._db_file = database
                if not self._db_conn:
                    raise DBConnectError("Database not connected")
            except Exception as e:
                raise DBConnectError(f"Database connection error: {e.__class__.__name__}: {e}") from e
        else:
            raise ValueError(f"DB Type '{db_type}' not known. {SUPPORTED_DB_TYPES}")

        # check that the table format is correct
        self.check_table()

        # load any provided config directly into the database
        self.load_config(*args)

    def connected(self) -> bool:
        ''' Return TRUE of the database is connected '''
        if self._db_type == MYSQL:
            self._logger.debug(f"Database connected: {self._db_conn.open}") # pyright: ignore[reportAttributeAccessIssue]
            return self._db_conn.open # pyright: ignore[reportAttributeAccessIssue]
        elif self._db_type == SQLITE3:
            self._logger.debug(f"Database connected: {self._db_conn is not None}")
            return self._db_conn is not None
        self._logger.debug("Database connected: FALSE")
        return False

    def load_config(self, *args):
        ''' Load a set of data into the database '''
        for arg in args:
            if not isinstance(arg, dict):
                raise ValueError(f"Data provided for loading into a database must be in dict format, received {type(arg)} for {arg}")
            for key, value in arg.items():
                self.set(key, value)

    def create_table(self, table:str):
        ''' Create a table in the database on the MYSQL server.  NOTE: This implies that the user account used has sufficient priviledges to create tables. '''
        if self._db_type == MYSQL:
            cursor = self._db_conn.cursor()
            rows = cursor.execute(CREATE_TABLE[MYSQL].format(table=table))
            cursor.close()
            self._logger.debug(f"DB_CREATE: affected rows: {rows}")
            self._logger.info(f"Table '{table}' created. Switching to new table.")
            self._table = table
            self.check_table(create_table=False)
            return
        elif self._db_type == SQLITE3:
            cursor = self._db_conn.cursor()
            cursor.execute(CREATE_TABLE[SQLITE3].format(table=table))
            rows = cursor.rowcount
            cursor.close()
            self._logger.debug(f"DB_CREATE: affected rows: {rows}")
            self._logger.info(f"Table '{table}' created. Switching to new table.")
            self._table = table
            self.check_table(create_table=False)
            return
        
        raise ValueError(f"DB Type '{self._db_type}' not known. {SUPPORTED_DB_TYPES}")

    def switch_table(self, table:str):
        ''' Switch the config manager to point to a new table '''
        old_table = self._table
        try:
            self._table = table
            self.check_table()
        except Exception as e:
            self._table = old_table
            self._logger.error(f"Error changing to table '{table}'. {e.__class__.__name__}: {e}")
            raise e

    def check_table(self, create_table=True) -> bool:
        ''' Check the DB connection and vierfy that the table is formatted as expected '''
        if self._db_type == MYSQL:
            import pymysql
            try:
                cursor = self._db_conn.cursor()
                rows = cursor.execute(CHECK_TABLE[MYSQL].format(table=self._table))
                results = cursor.fetchall()
            except pymysql.err.ProgrammingError as e:
                if 'Table' in str(e) and "doesn't exist" in str(e) and create_table:
                    self.create_table(self._table)
                    return self.check_table(create_table=False)
                else:
                    raise e
            cursor.close()
            self._logger.debug(f"DB_CHECK: table: {self._table}, columns: {rows}, data: {results}")
            if rows == 0 and create_table:
                self.create_table(self._table)
                return self.check_table(create_table=False)
            if rows != 4:
                raise DBTableFormatError(f"MYSQL/MARIADB table '{self._table}' should have 3 columns and has {rows}")
            k = v = encrypted = cast = False
            for row in results:
                if {key: value for key, value in row.items() if key in CHECK_TABLE_K[MYSQL]} == CHECK_TABLE_K[MYSQL]:
                    k = True
                if {key: value for key, value in row.items() if key in CHECK_TABLE_V[MYSQL]} == CHECK_TABLE_V[MYSQL]:
                    v = True
                if {key: value for key, value in row.items() if key in CHECK_TABLE_CAST[MYSQL]} == CHECK_TABLE_CAST[MYSQL]:
                    cast = True
                if {key: value for key, value in row.items() if key in CHECK_TABLE_ENCRYPTED[MYSQL]} == CHECK_TABLE_ENCRYPTED[MYSQL]:
                    encrypted = True
            if not k:
                raise DBTableFormatError(f"DB table '{self._table}' must have 3 columns (k, v, encrypted). 'k' column returned "
                                         f"{[x for x in results if x.get('Field') == 'k']} and should be {CHECK_TABLE_K[MYSQL]}")
            if not v:
                raise DBTableFormatError(f"DB table '{self._table}' must have 3 columns (k, v, encrypted). 'v' column returned "
                                         f"{[x for x in results if x.get('Field') == 'v']} and should be {CHECK_TABLE_V[MYSQL]}")
            if not cast:
                raise DBTableFormatError(f"DB table '{self._table}' must have 3 columns (k, v, encrypted). 'cast' column returned "
                                         f"{[x for x in results if x.get('Field') == 'cast']} and should be {CHECK_TABLE_CAST[MYSQL]}")
            if not encrypted:
                raise DBTableFormatError(f"DB table '{self._table}' must have 3 columns (k, v, encrypted). 'encrypted' column returned "
                                         f"{[x for x in results if x.get('Field') == 'encrypted']} and should be {CHECK_TABLE_ENCRYPTED[MYSQL]}")
            self._logger.debug(f"DB_CHECK: table: '{self._table}', OK")
            return True
        elif self._db_type == SQLITE3:
            cursor = self._db_conn.cursor()
            cursor.execute(CHECK_TABLE[SQLITE3].format(table=self._table))
            rows = cursor.rowcount
            results = cursor.fetchall()
            cursor.close()
            self._logger.debug(f"DB_CHECK: table: {self._table}, columns: {rows}, data: {results}")
            if len(results) == 0:
                # table doesn't exist, create it
                self.create_table(self._table)
                return self.check_table()
            if len(results) != 4:
                raise DBTableFormatError(f"MYSQL/MARIADB table '{self._table}' should have 4 columns and has {rows}")
            k = v = encrypted = cast = False
            for row in results:
                if row == CHECK_TABLE_K[SQLITE3]:
                    k = True
                if row == CHECK_TABLE_V[SQLITE3]:
                    v = True
                if row == CHECK_TABLE_CAST[SQLITE3]:
                    cast = True
                if row == CHECK_TABLE_ENCRYPTED[SQLITE3]:
                    encrypted = True
            if not k:
                raise DBTableFormatError(f"DB table '{self._table}' must have 3 columns (k, v, encrypted). 'k' column returned "
                                         f"{[x for x in results if x[1] == 'k']} and should be {CHECK_TABLE_K[SQLITE3]}") # pyright: ignore[reportArgumentType]
            if not v:
                raise DBTableFormatError(f"DB table '{self._table}' must have 3 columns (k, v, encrypted). 'v' column returned "
                                         f"{[x for x in results if x[1] == 'v']} and should be {CHECK_TABLE_V[SQLITE3]}") # pyright: ignore[reportArgumentType]
            if not cast:
                raise DBTableFormatError(f"DB table '{self._table}' must have 3 columns (k, v, encrypted). 'cast' column returned "
                                         f"{[x for x in results if x[1] == 'cast']} and should be {CHECK_TABLE_CAST[SQLITE3]}") # pyright: ignore[reportArgumentType]
            if not encrypted:
                raise DBTableFormatError(f"DB table '{self._table}' must have 3 columns (k, v, encrypted). 'encrypted' column returned "
                                         f"{[x for x in results if x[1] == 'encrypted']} and should be {CHECK_TABLE_ENCRYPTED[SQLITE3]}") # pyright: ignore[reportArgumentType]
            self._logger.debug(f"DB_CHECK: table: '{self._table}', OK")
            return True
        
        raise ValueError(f"DB Type '{self._db_type}' not known. {SUPPORTED_DB_TYPES}")
    
    def _encrypted_format(self, key) -> int:
        ''' Return the integer associated to the encryption format for the key in the database '''
        if self._db_type == MYSQL:
            cursor = self._db_conn.cursor()
            rows = cursor.execute(KEY_ENCRYPTED[MYSQL].format(table=self._table, key=key))
            results = cursor.fetchall()
            cursor.close()
            if rows == 0:
                raise DBNotFound
            if rows != 1:
                raise DBQueryError(f"Query for if key '{key}' is encrypted should return 1 row, recieved {rows}")
            if results[0].get('encrypted', -1) not in ENCRYPTED_FORMATS:
                raise DBQueryError(f"Query for if key '{key}' is encrypted returned {results[0].get('encrypted')}, supported options are {ENCRYPTED_FORMATS}")
            self._logger.debug(f"ENCRYPTED_FORMAT: Key '{key}' using {results[0].get('encrypted')} ({ENCRYPTED_FORMATS.get(results[0].get('encrypted', -1))})")
            return results[0].get('encrypted', -1)
        elif self._db_type == SQLITE3:
            cursor = self._db_conn.cursor()
            cursor.execute(KEY_ENCRYPTED[SQLITE3].format(table=self._table, key=key))
            results = cursor.fetchall()
            results = [dict(zip(('encrypted',), x)) for x in results]
            cursor.close()
            if len(results) == 0:
                raise DBNotFound
            if len(results) != 1:
                raise DBQueryError(f"Query for if key '{key}' is encrypted should return 1 row, recieved {len(results)}")
            if results[0].get('encrypted', -1) not in ENCRYPTED_FORMATS:
                raise DBQueryError(f"Query for if key '{key}' is encrypted returned {results[0].get('encrypted')}, supported options are {ENCRYPTED_FORMATS}")
            self._logger.debug(f"ENCRYPTED_FORMAT: Key '{key}' using {results[0].get('encrypted')} ({ENCRYPTED_FORMATS.get(int(results[0].get('encrypted', 0)))})")
            return int(results[0].get('encrypted', -1))

        raise ValueError(f"DB Type '{self._db_type}' not known. {SUPPORTED_DB_TYPES}")

    def is_encrypted(self, key) -> bool:
        ''' Check if the value for a key set is to be encrypted '''
        try:
            return self._encrypted_format(key) > 0
        except DBNotFound:
            return False
        except Exception as e:
            raise DBQueryError from e

    def __setitem__(self, key: Any, value: Any) -> None:
        ''' Update the config data in the SQL database when a config value is set '''
        self.set(key, value)

    def __getitem__(self, key: Any) -> Any:
        ''' Return the value from the database for the requested config key '''
        return self.get(key, raise_not_found=True)

    def __len__(self) -> int:
        ''' Return the number of config items in the database '''
        if self._db_type == MYSQL:
            cursor = self._db_conn.cursor()
            rows = cursor.execute(TABLE_LENGTH[MYSQL].format(table=self._table))
            results = cursor.fetchall()
            cursor.close()
            if rows != 1:
                raise DBQueryError(f"Table length expected to get 1 row but received {rows}")
            if 'length' not in results[0]:
                raise DBQueryError("Table length not returned in query.")
            return results[0].get('length', 0)
        elif self._db_type == SQLITE3:
            cursor = self._db_conn.cursor()
            cursor.execute(TABLE_LENGTH[SQLITE3].format(table=self._table))
            results = cursor.fetchall()
            cursor.close()
            if len(results) != 1:
                raise DBQueryError(f"Table length expected to get 1 row but received {len(results)}")
            return results[0][0] # pyright: ignore[reportArgumentType]

        raise ValueError(f"DB Type '{self._db_type}' not known. {SUPPORTED_DB_TYPES}")

    def __delitem__(self, key: Any) -> None:
        ''' Delete the config value from the database for the requested config key '''
        if self._db_type == MYSQL:
            cursor = self._db_conn.cursor()
            rows = cursor.execute(DEL_ITEM[MYSQL].format(database=self._db_conn.db.decode('utf-8'), table=self._table, k=key)) # type: ignore
            if rows == 0:
                return
            if rows != 1:
                self._db_conn.rollback()
                raise DBQueryError(f"Delete expected to affect 1 row but received {rows}")
            self._db_conn.commit()
            cursor.close()
            return
        elif self._db_type == SQLITE3:
            cursor = self._db_conn.cursor()
            cursor.execute(DEL_ITEM[SQLITE3].format(table=self._table, k=key)) # type: ignore
            self._db_conn.commit()
            cursor.close()
            return

        raise ValueError(f"DB Type '{self._db_type}' not known. {SUPPORTED_DB_TYPES}")

    def __iter__(self) -> Iterable:
        ''' Return an iterator over the config keys '''
        if self._db_type == MYSQL:
            cursor = self._db_conn.cursor()
            cursor.execute(GET_KEYS[MYSQL].format(table=self._table))
            results = cursor.fetchall()
            cursor.close()
            for row in results:
                yield row['k']
            return
        elif self._db_type == SQLITE3:
            cursor = self._db_conn.cursor()
            cursor.execute(GET_KEYS[SQLITE3].format(table=self._table))
            results = cursor.fetchall()
            results = [dict(zip(('k',), x)) for x in results]
            cursor.close()
            for row in results:
                yield row['k']
            return

        raise ValueError(f"DB Type '{self._db_type}' not known. {SUPPORTED_DB_TYPES}")

    def __repr__(self):
        ''' Return a string representation of the database connection '''
        if self._db_type == MYSQL:
            return f"{self.__class__.__name__}(host={self._db_conn.host}, port={self._db_conn.port}, db={self._db_conn.db.decode('utf-8')}, table={self._table}, ssl={self._db_conn.ssl}, connected={self.connected()})" # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        if self._db_type == SQLITE3:
            return f"{self.__class__.__name__}(file={self._db_file})"

    def get(self, key: Any, default: Any = None, raise_not_found:bool=False) -> Any:
        ''' Return the value from the database for the requested config key, or the default value if the key is not found '''
        if self._db_type == MYSQL:
            cursor = self._db_conn.cursor()
            rows = cursor.execute(GET_ITEM[MYSQL].format(table=self._table, k=key))
            results = cursor.fetchall()
            cursor.close()
            self._logger.debug(f"GET_ITEM: results: {results}")
            if rows == 0:
                if raise_not_found:
                    raise KeyError(key)
                return default
            if rows != 1:
                raise DBQueryError(f"Set Item expected to update 1 row for {key} but received {rows}")
            if results[0].get('encrypted') == 0:
                if results[0].get('cast') in CAST_TYPES:
                    if results[0].get('cast') == 'dict':
                        return ConfigDictDB(results[0].get('v',''), key=results[0].get('k', ''), callback=self.set, encryption_key=self._encryption_key, log_level=self._log_level)
                    elif results[0].get('cast') == 'list':
                        return ConfigListDB(results[0].get('v',''), key=results[0].get('k', ''), callback=self.set, encryption_key=self._encryption_key, log_level=self._log_level)
                    return CAST_TYPES[results[0].get('cast', '')](results[0].get('v', None))
                return results[0].get('v')
            if results[0].get('encrypted') == 1:
                if self._encryption_key is None:
                    raise DBCryptoError(f"Key {key} is encrypted and no encryption key present.")
                if results[0].get('cast') in CAST_TYPES:
                    return CAST_TYPES[results[0].get('cast', '')](decrypt_data(results[0].get('v', ''), self._encryption_key))
                return decrypt_data(results[0].get('v', ''), self._encryption_key)
            raise DBQueryError(f"Query for if key '{key}' is encrypted returned {results[0].get('encrypted')}, supported options are {ENCRYPTED_FORMATS}")
        elif self._db_type == SQLITE3:
            cursor = self._db_conn.cursor()
            cursor.execute(GET_ITEM[SQLITE3].format(table=self._table, k=key))
            results = cursor.fetchall()
            results = [dict(zip(TABLE_COLUMNS, x)) for x in results]
            cursor.close()
            self._logger.debug(f"GET_ITEM: results: {results}")
            if len(results) == 0:
                if raise_not_found:
                    raise KeyError(key)
                return default
            if len(results) != 1:
                raise DBQueryError(f"Set Item expected to update 1 row for {key} but received {len(results)}")
            if results[0].get('encrypted') == 0:
                if results[0].get('cast') in CAST_TYPES:
                    if results[0].get('cast') == 'dict':
                        return ConfigDictDB(results[0].get('v',''), key=results[0].get('k', ''), callback=self.set, encryption_key=self._encryption_key, log_level=self._log_level)
                    elif results[0].get('cast') == 'list':
                        self._logger.debug(f"GET: {results[0].get('v','')}")
                        return ConfigListDB(results[0].get('v',''), key=results[0].get('k', ''), callback=self.set, encryption_key=self._encryption_key, log_level=self._log_level)
                    return CAST_TYPES[results[0].get('cast', '')](results[0].get('v', None))
                return results[0].get('v')
            if results[0].get('encrypted') == 1:
                if self._encryption_key is None:
                    raise DBCryptoError(f"Key {key} is encrypted and no encryption key present.")
                if results[0].get('cast') in CAST_TYPES:
                    return CAST_TYPES[results[0].get('cast', '')](decrypt_data(results[0].get('v', ''), self._encryption_key))
                return decrypt_data(results[0].get('v', ''), self._encryption_key)
            raise DBQueryError(f"Query for if key '{key}' is encrypted returned {results[0].get('encrypted')}, supported options are {ENCRYPTED_FORMATS}")
        
        raise ValueError(f"DB Type '{self._db_type}' not known. {SUPPORTED_DB_TYPES}")

    def set(self, key: Any, value: Any, encrypt:str|None|bool=None):
        ''' Set a value int the database '''
        # check if item is encrypted and encrypt if needed
        if encrypt is not None:
            if encrypt in ['no', 'none', False]:
                encrypted_format = 0
            elif encrypt in ['yes', True]:
                encrypted_format = next((key for key, value in ENCRYPTED_FORMATS.items() if value == self._encryption_format))
            else:
                raise ValueError(f"Encrypt must be 'no', 'none', False, 'yes' or True, got {encrypt}")
        else:
            try:
                encrypted_format = self._encrypted_format(key)
            except DBNotFound:
                encrypted_format = 0

        # get the type to see if casting required
        cast_type = type(value).__name__ if type(value).__name__ in CAST_TYPES else None
        if cast_type in ['dict', 'list', 'tuple']:
            # if we get a dict or list, dump to a json string before loading into the database
            value = json.dumps(value, cls=ConfigJsonEncoder)
        if encrypted_format == 1:
            if not self._encryption_key:
                raise DBCryptoError(f"Cannot encrypt '{key}' using Fernet, no encryption key present.")
            value = encrypt_data(value, self._encryption_key)
        if self._db_type == MYSQL:
            cursor = self._db_conn.cursor()
            cursor.execute(SET_ITEM[MYSQL].format(table=self._table, k=key, v=value, cast=cast_type, encrypted=encrypted_format))
            rows = cursor.rowcount
            cursor.close()
            if rows == 0:
                self._logger.debug(f"SET_ITEM: No update made for key '{key}'")
            elif rows == 1:
                self._logger.debug(f"SET_ITEM: key '{key}' inserted, encryption {encrypted_format}")
            elif rows == 2:
                self._logger.debug(f"SET_ITEM: key '{key}' updated, encryption {encrypted_format}")
            else: # 2 for update, 1 for insert, 0 for no change
                self._db_conn.rollback()
                raise DBQueryError(f"Set Item expected to update 1 row for {key} but received {rows}")
            self._db_conn.commit()
            return
        if self._db_type == SQLITE3:
            cursor = self._db_conn.cursor()
            cursor.execute(SET_ITEM[SQLITE3].format(table=self._table, k=key, v=value, cast=cast_type, encrypted=encrypted_format))
            cursor.close()
            self._logger.debug(f"SET_ITEM: '{key}'")
            self._db_conn.commit()
            return

        raise ValueError(f"DB Type '{self._db_type}' not known. {SUPPORTED_DB_TYPES}")

    def encrypt(self, key):
        ''' Encrypt a key in the database if it is not already encrypted '''
        self.set(key, self.get(key), encrypt=True)

    def decrypt(self, key):
        ''' Decrypt a key in the database if it is encrypted '''
        self.set(key, self.get(key), encrypt=False)
