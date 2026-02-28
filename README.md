<!-- build_manager_tag start -->
![](https://img.shields.io/badge/tests.py-passing-green)![](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)
<!-- build_manager_tag stop -->
# Config Manager

This python library is built to manage JSON / YAML configuration files, or use a MYSQL database table as a configuration file.  The script is presented with a dict object that can be manipulated like any other dict.  You can optionally set to have the soruce JSON/YAML file updated automatically when an option is changed.

Configuration values can be optionally encrypted.  The library will automatically decrypt and re-encrypt when configuration vaules are read and written.

The MYSQL based configuration manager will use a table as a source.  Encryption for values is supported.  All updates are auto-written to the database.

Installation without database connectivity

    pip3 install config_manager

Installation with mysql/mariadb database connectivity

    pip3 install config_manager[mysql]

## Encryption

The encryption uses the cryptography.fernet symmectric encryption.  The encryption key is 32 bytes and can be provided as a path to a file, or provided as a string (for example if you store your encryption key in Hashicorp Vault or another vault system).

Additional encryption options may be added later (in particular for the DB configuration manager).

## JSON / YAML Files

    >>> import config_manager
    >>> config_json = config_manager.load_file('tests/config1.json', encryption_key_file='tests/config1_encryption', log_level='info', save_on_change=True)
    >>>
    >>> config_json
   {'key1': 'value1_updated_updated_updatedtesttest', 'key2': 123, 'key3': [1, 2, 3, 4, 5, 6, 7, 7, 7, 7], 'key4': {'subkey1': 'subvalue1_updated_updated', 'subkey2': 2456, 'subkey3': [4, 5, 6, 'new_value', 'new_value'], 'subkey4': {'subsubkey1': 'subsubvalue1_nested_value1_nested_value1', 'subsubkey2': 2789, 'subsubkey3': [7, 8, 9, 'new_nested_value', 'new_nested_value']}}}
    >>>
    >>> config_json['key1'] = 'test123'
    >>> config_json.decrypt('key1')
    2026-02-20 19:19:41,984 - ConfigManagerJsonDict - INFO - Config key 'key1' has been decrypted
    >>> config_json.encrypt('key1')
    2026-02-20 19:19:56,920 - ConfigManagerJsonDict - INFO - Config key 'key1' has been encrypted

If save_on_change is disabled, you can call the `config_json.save_config()` function to save to the file.

### Nested list and dict object

Multiple leves of list and dict objects are supported.  Individual entries in lists can be encrypted.  Any update to the nested objects will trigger a save for the root config_manager object.

## Config Manager Functions

Each config manager object has the following functions available:

- is_encrypted(key) -- Returns TRUE if the dict key (or list index) is encrypted
- encrypt(key) -- Encrypt the specified key or list index (encrypts in memory and for saving)
- decrypt(key) -- Decrypt the specified key or list index (decrypts in memory and for saving)
- get(key) -- get the unencrypted value (if encrypted)

JSON / YAML config managers will have all the preceding as well as the following:

- @property save_on_change -- Set to TRUE to auto save when a key or index is updated, FALSE to disable autosave
- save_config() -- Save the configuration back to the original file

## MYSQL

Currently MYSQL (or MARIADB) is supported (tested with MYSQL 9.6.0).  Since relational databases are tabular, nested list or dict object are not supported.  The MYSQL database is configured to support other encryption options that may be added in the future, for now it uses the same cryptography Fernet library.

The MYSQL config manager provides some additional functions:

- connected() -- Returns TRUE if connected to the database
- create_table(table) -- creates the specified table in the database
- switch_table(table) -- switch the config manager to point to a different database table
- check_table() -- checks the current table to ensure proper configuration (this is run at start, table create or switch)
- set(key, value, encrypted) -- Set a value in the database, encrypted can be set to TRUE or FALSE to force the value to be either encrypted or not.  If left as NONE, the value will only be encrypted if it already exists and is encrypted.

Sample:

    >>> from config_manager.database import ConfigManagerDB
    >>> config = ConfigManagerDB(host='svc1', user='test_api_query', password='******', database='portal', log_level='debug', ssl_ca='********', encryption_key='******')
    2026-02-20 19:48:23,952 - ConfigManagerDB - DEBUG - Connecting to database svc1, portal...
    2026-02-20 19:48:24,036 - ConfigManagerDB - DEBUG - Database connected: True
    2026-02-20 19:48:24,039 - ConfigManagerDB - DEBUG - DB_CHECK: table: kv, columns: 4, data: [{'Field': 'k', 'Type': 'varchar(45)', 'Null': 'NO', 'Key': 'PRI', 'Default': None, 'Extra': ''}, {'Field': 'v', 'Type': 'text', 'Null': 'YES', 'Key': '', 'Default': None, 'Extra': ''}, {'Field': 'cast', 'Type': 'varchar(45)', 'Null': 'YES', 'Key': '', 'Default': None, 'Extra': ''}, {'Field': 'encrypted', 'Type': 'tinyint(3) unsigned zerofill', 'Null': 'NO', 'Key': '', 'Default': '000', 'Extra': ''}]
    2026-02-20 19:48:24,039 - ConfigManagerDB - DEBUG - DB_CHECK: table: 'kv', OK
    >>> 
    >>> config.create_table('kv2')
    2026-02-20 19:49:11,807 - ConfigManagerDB - DEBUG - DB_CREATE: affected rows: 0
    2026-02-20 19:49:11,807 - ConfigManagerDB - INFO - Table 'kv2' created. Switching to new table.
    2026-02-20 19:49:11,809 - ConfigManagerDB - DEBUG - DB_CHECK: table: kv2, columns: 4, data: [{'Field': 'k', 'Type': 'varchar(45)', 'Null': 'NO', 'Key': 'PRI', 'Default': None, 'Extra': ''}, {'Field': 'v', 'Type': 'text', 'Null': 'YES', 'Key': '', 'Default': None, 'Extra': ''}, {'Field': 'cast', 'Type': 'varchar(45)', 'Null': 'YES', 'Key': '', 'Default': None, 'Extra': ''}, {'Field': 'encrypted', 'Type': 'tinyint(3) unsigned zerofill', 'Null': 'NO', 'Key': '', 'Default': '000', 'Extra': ''}]
    2026-02-20 19:49:11,809 - ConfigManagerDB - DEBUG - DB_CHECK: table: 'kv2', OK
    >>> 
    >>> config.set('key1', 'value', encrypt=True)
    2026-02-20 19:49:46,422 - ConfigManagerDB - DEBUG - SET_ITEM: key 'key1' inserted, encryption 1
    >>> config['key1']
    2026-02-20 19:50:04,294 - ConfigManagerDB - DEBUG - GET_ITEM: results: [{'k': 'key1', 'v': 'gAAAAABpmR1K5NRCwj9yv0mg5Al6fUmoQ9-TLRl9Rbr0UspG-bLsBOAlMEo0HB7AXYY8aRP5q-dfCtrnbrnC2Ajfv3t_bIX-WQ==', 'cast': 'None', 'encrypted': 1}]
    'value'
    >>> 

NOTE: Extra options added to the ConfigManagerDB object will be passed through to PyMySql.  In the example above, a path to a CA certificate is provided to enable a TLS encrypted session to the database server.

## SQLite3

SQLite3 is integrated in python and can be used as a database with config_manager.  SQLite3 supports multiple tables in a db file as well as encrypted keys.

The MYSQL config manager provides some additional functions:

- connected() -- Returns TRUE if connected to the database
- create_table(table) -- creates the specified table in the database
- switch_table(table) -- switch the config manager to point to a different database table
- check_table() -- checks the current table to ensure proper configuration (this is run at start, table create or switch)
- set(key, value, encrypted) -- Set a value in the database, encrypted can be set to TRUE or FALSE to force the value to be either encrypted or not.  If left as NONE, the value will only be encrypted if it already exists and is encrypted.

Sample:

    >>> from config_manager.database import ConfigManagerDB
    >>> 
    >>> config = ConfigManagerDB(database='local/sqlite3-test.db', db_type='sqlite3', log_level='debug')
    2026-02-28 10:18:48,509 - ConfigManagerDB - DEBUG - Connecting to SQLITE3 database local/sqlite3-test.db
    2026-02-28 10:18:48,510 - ConfigManagerDB - DEBUG - DB_CHECK: table: kv, columns: -1, data: [(0, 'k', 'varchar(45)', 1, None, 1), (1, 'v', 'TEXT', 0, None, 0), (2, 'cast', 'varchar(45)', 0, None, 0), (3, 'encrypted', 'tinyint(3)', 1, "'000'", 0)]
    2026-02-28 10:18:48,510 - ConfigManagerDB - DEBUG - DB_CHECK: table: 'kv', OK
    >>> 
    >>> config.create_table('kv2')
    2026-02-28 10:19:13,980 - ConfigManagerDB - DEBUG - DB_CREATE: affected rows: -1
    2026-02-28 10:19:13,980 - ConfigManagerDB - INFO - Table 'kv2' created. Switching to new table.
    2026-02-28 10:19:13,980 - ConfigManagerDB - DEBUG - DB_CHECK: table: kv2, columns: -1, data: [(0, 'k', 'varchar(45)', 1, None, 1), (1, 'v', 'TEXT', 0, None, 0), (2, 'cast', 'varchar(45)', 0, None, 0), (3, 'encrypted', 'tinyint(3)', 1, "'000'", 0)]
    2026-02-28 10:19:13,980 - ConfigManagerDB - DEBUG - DB_CHECK: table: 'kv2', OK
    >>> config.set('key1', 'abc123')
    2026-02-28 10:19:36,864 - ConfigManagerDB - DEBUG - SET_ITEM: 'key1'
    >>> config['key1']
    2026-02-28 10:19:41,253 - ConfigManagerDB - DEBUG - GET_ITEM: results: [{'k': 'key1', 'v': 'abc123', 'cast': 'None', 'encrypted': 0}]
    'abc123'
    >>> 

NOTE: Extra options added to the ConfigManagerDB object will be passed through to SQLite3.



Enjoy!  Feel free to open an issue here to report any bugs, or request features.

