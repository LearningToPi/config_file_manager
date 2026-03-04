import unittest
import json
import yaml
import os
from logging_handler import create_logger, INFO
from config_file_manager import ConfigDict, ConfigList, generate_encryption_key, load_file
from config_file_manager.database import ConfigManagerDB


class config_manager_test(unittest.TestCase):
    ''' Uniittest for the config_manager packages '''
    def test_1_dict(self):
        ''' Test loading and modifying a dict object '''
        logger = create_logger(INFO, name='Test_DICT')
        logger.info("Testing DICT create")
        config = ConfigDict({'test1': 'value1', 'test2': 2, 'test3': [0, 1, 2], 'test4': {'test4-1': 'value1'}})
        self.assertTrue(config['test1'] == 'value1')
        self.assertTrue(config['test2'] == 2)
        self.assertTrue(config['test3'] == [0, 1, 2])
        self.assertTrue(isinstance(config['test3'], ConfigList))
        self.assertTrue(isinstance(config['test4'], ConfigDict))
        self.assertTrue(config['test4']['test4-1'] == 'value1')

        logger.info("Testing encrypting")
        key = generate_encryption_key()
        config = ConfigDict({'test1': 'value1', 'test2': 2, 'test3': [0, 1, 2], 'test4': {'test4-1': 'value1'}}, encryption_key=key.encode())
        # verify data is unencrypted
        self.assertTrue(config['test1'] == config.data['test1'])
        self.assertFalse(config.is_encrypted('test1'))

        # encrypt and verify data is now encrypted
        config.encrypt('test1')
        logger.info(f"{config['test1']},  {config.data['test1']}")
        self.assertTrue(config.is_encrypted('test1'))
        self.assertTrue(config['test1'] != config.data['test1'])
        self.assertTrue(config['test1'] == 'value1')

        # decrypt data and verify back to original
        config.decrypt('test1')
        self.assertTrue(config['test1'] == config.data['test1'])
        self.assertFalse(config.is_encrypted('test1'))

        # Test encrypting 1 value in list and sub key
        self.assertTrue(config['test3'] == [0 ,1, 2])
        self.assertTrue(config['test3'] == config['test3'].data)

        # encrypt and verify now encrypted
        config['test3'].encrypt(1)
        logger.info(f"{config['test3']},  {config['test3'].data}")
        self.assertTrue(config['test3'].is_encrypted(1))
        self.assertTrue(config['test3'][1] != config['test3'].data[1])
        self.assertTrue(config['test3'][1] == 1)

        # decrypt and verify back to original
        config['test3'].decrypt(1)
        self.assertTrue(config['test3'] == [0 ,1, 2])
        self.assertTrue(config['test3'] == config['test3'].data)

    def test_2_json_yaml(self):
        ''' Test loading and modifying a json file '''
        logger = create_logger(INFO, name='Test_JSON')
        logger.info("Resetting JSON file...")
        with open('tests/config1-orig.json', 'r', encoding='utf-8') as input_file:
            config = json.load(input_file)
            with open('tests/config1.json', 'w', encoding='utf-8') as output_file:
                json.dump(config, output_file, indent=4)
            with open('tests/config1.yaml', 'w', encoding='utf-8') as output_file:
                yaml.safe_dump(config, output_file)

        for file in ['tests/config1.json', 'tests/config1.yaml']:
            logger.info(f"Loading {file}...")
            config = load_file(filename=file, encryption_key_file='tests/config1_encryption', save_on_change=True)

            # verify data is unencrypted
            self.assertTrue(config['key1'] == config.data['key1'])
            self.assertFalse(config.is_encrypted('key1'))

            # encrypt and verify data is now encrypted
            config.encrypt('key1')
            logger.info(f"{config['key1']},  {config.data['key1']}")
            self.assertTrue(config.is_encrypted('key1'))
            self.assertTrue(config['key1'] != config.data['key1'])
            self.assertTrue(config['key1'] == 'value1')

            # load config file and verify the value is encrypted
            with open(file, 'r', encoding='utf-8') as input_file:
                config_file = json.load(input_file) if file.endswith('.json') else yaml.safe_load(input_file)
            logger.info(f"Verifying key1 encryped in file: {config_file['key1']}")
            self.assertTrue(config_file['key1'].startswith('gAAAA'))
            self.assertTrue(config_file['key1'] == config.data['key1'])

            # decrypt data and verify back to original
            config.decrypt('key1')
            self.assertTrue(config['key1'] == config.data['key1'])
            self.assertFalse(config.is_encrypted('key1'))

            # load config file and verify the value is not encrypted
            with open(file, 'r', encoding='utf-8') as input_file:
                config_file = json.load(input_file) if file.endswith('.json') else yaml.safe_load(input_file)
            logger.info(f"Verifying key1 encryped in file: {config_file['key1']}")
            self.assertFalse(config_file['key1'].startswith('gAAAA'))
            self.assertTrue(config_file['key1'] == config['key1'])

            # Test encrypting 1 value in list
            self.assertTrue(config['key3'] == [1 ,2, 3])
            self.assertTrue(config['key3'] == config['key3'].data)

            # encrypt and verify now encrypted
            config['key3'].encrypt(1)
            logger.info(f"{config['key3']},  {config['key3'].data}")
            self.assertTrue(config['key3'].is_encrypted(1))
            self.assertTrue(config['key3'][1] != config['key3'].data[1])
            self.assertTrue(config['key3'][1] == 2)

            # load config file and verify the value is encrypted
            with open(file, 'r', encoding='utf-8') as input_file:
                config_file = json.load(input_file) if file.endswith('.json') else yaml.safe_load(input_file)
            self.assertTrue(config_file['key3'][1].startswith('gAAAA'))
            self.assertTrue(config_file['key3'] == config.data['key3'])

            # decrypt and verify back to original
            config['key3'].decrypt(1)
            self.assertTrue(config['key3'] == [1 ,2, 3])
            self.assertTrue(config['key3'] == config['key3'].data)

            # Test encrypting 1 value in subkey
            self.assertTrue(config['key4']['subkey4']['subsubkey2'] == 789)
            self.assertTrue(config['key4']['subkey4']['subsubkey2'] == config['key4']['subkey4'].data['subsubkey2'])

            # encrypt and verify now encrypted
            config['key4']['subkey4'].encrypt('subsubkey2')
            logger.info(f"{config['key4']['subkey4']['subsubkey2']},  {config['key4']['subkey4'].data['subsubkey2']}")
            self.assertTrue(config['key4']['subkey4'].is_encrypted('subsubkey2'))
            self.assertTrue(config['key4']['subkey4']['subsubkey2'] != config['key4']['subkey4'].data['subsubkey2'])
            self.assertTrue(config['key4']['subkey4']['subsubkey2'] == 789)

            # load config file and verify the value is encrypted
            with open(file, 'r', encoding='utf-8') as input_file:
                config_file = json.load(input_file) if file.endswith('.json') else yaml.safe_load(input_file)
            self.assertTrue(config_file['key4']['subkey4']['subsubkey2'].startswith('gAAAA'))
            self.assertTrue(config_file['key4']['subkey4']['subsubkey2'] == config['key4']['subkey4'].data['subsubkey2'])

            # decrypt and verify back to original
            config['key4']['subkey4'].decrypt('subsubkey2')
            self.assertTrue(config['key4']['subkey4']['subsubkey2'] == 789)
            self.assertTrue(config['key4']['subkey4']['subsubkey2'] == config['key4']['subkey4'].data['subsubkey2'])


    def test_3_db_mysql(self):
        ''' Test loading and configuring a MYSQL database '''
        logger = create_logger(INFO, name='Test_MYSQL')
        db_config_file = 'local/config_manager_test.json'
        logger.info(f"Loading DB config file {db_config_file}")
        db_config = load_file(db_config_file)
        key = generate_encryption_key()
        config = ConfigManagerDB(**db_config, encryption_key=key.encode())
        config.load_config({'test1': 'value1', 'test2': 2, 'test3': [0, 1, 2], 'test4': {'test4-1': 'value1'}})
        self.assertTrue(config['test1'] == 'value1')
        self.assertTrue(config['test2'] == 2)
        self.assertTrue(config['test3'] == [0, 1, 2])
        self.assertTrue(isinstance(config['test3'], ConfigList))
        self.assertTrue(isinstance(config['test4'], ConfigDict))
        self.assertTrue(config['test4']['test4-1'] == 'value1')

        logger.info("Testing encrypting")
        # verify data is unencrypted
        self.assertFalse(config.is_encrypted('test1'))

        # encrypt and verify data is now encrypted
        config.encrypt('test1')
        self.assertTrue(config.is_encrypted('test1'))
        self.assertTrue(config['test1'] == 'value1')

        # decrypt data and verify back to original
        config.decrypt('test1')
        self.assertFalse(config.is_encrypted('test1'))

        # Test encrypting 1 value in list and sub key
        self.assertTrue(config['test3'] == [0 ,1, 2])

        # encrypt and verify now encrypted
        config['test3'].encrypt(1)
        self.assertTrue(config['test3'].is_encrypted(1))
        self.assertTrue(config['test3'][1] == 1)

        # decrypt and verify back to original
        config['test3'].decrypt(1)
        self.assertFalse(config.is_encrypted('test3'))
        self.assertTrue(config['test3'] == [0 ,1, 2])

    def test_4_db_sqlite3(self):
        ''' Test loading and configuring a SQLLITE3 database '''
        logger = create_logger(INFO, name='Test_SQLITE3')
        db_file = '/tmp/sqlite3-test.db'
        if os.path.exists(db_file):
            logger.info(f"Removing {db_file}")
            os.remove(db_file)
        logger.info(f"Creating {db_file}")
        key = generate_encryption_key()
        config = ConfigManagerDB(database=db_file, db_type='sqlite3', encryption_key=key.encode(), log_level='debug')
        config.load_config({'test1': 'value1', 'test2': 2, 'test3': [0, 1, 2], 'test4': {'test4-1': 'value1'}})
        self.assertTrue(config['test1'] == 'value1')
        self.assertTrue(config['test2'] == 2)
        self.assertTrue(config['test3'] == [0, 1, 2])
        self.assertTrue(isinstance(config['test3'], ConfigList))
        self.assertTrue(isinstance(config['test4'], ConfigDict))
        self.assertTrue(config['test4']['test4-1'] == 'value1')

        logger.info("Testing encrypting")
        # verify data is unencrypted
        self.assertFalse(config.is_encrypted('test1'))

        # encrypt and verify data is now encrypted
        config.encrypt('test1')
        self.assertTrue(config.is_encrypted('test1'))
        self.assertTrue(config['test1'] == 'value1')

        # decrypt data and verify back to original
        config.decrypt('test1')
        self.assertFalse(config.is_encrypted('test1'))

        # Test encrypting 1 value in list and sub key
        self.assertTrue(config['test3'] == [0 ,1, 2])

        # encrypt and verify now encrypted
        config['test3'].encrypt(1)
        self.assertTrue(config['test3'].is_encrypted(1))
        self.assertTrue(config['test3'][1] == 1)

        # decrypt and verify back to original
        config['test3'].decrypt(1)
        self.assertFalse(config.is_encrypted('test3'))
        self.assertTrue(config['test3'] == [0 ,1, 2])


if __name__ == '__main__':
    unittest.main()
