import argparse
from pprint import pprint
from . import load_file



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manage configuration or configuration files. Configuration can include encrypted values in a dictionary. '
                                     'JSON or YAML files can be configured to auto save on update. Database tables can be used as configuration files.', prog='config_manager.py')
    parser.add_argument('config_file', type=str, help='Path to the config file to load')
    parser.add_argument('--log-level', type=str, default='INFO', help='Logging level to use for the config manager')
    parser.add_argument('--encryption-key', '-e', type=str, help='Encryption key to use for encrypting/decrypting config values')
    args = parser.parse_args()

    config = load_file(args.config_file, log_level=args.log_level, encryption_key_file=args.encryption_key, save_on_change=True)
    config['key1'] = config.get('key1', 'default_value') + 'test'
    config['key3'].append(7)
    config['key4']['subkey1'] = config['key4']['subkey1'] + '_updated'
    config['key4']['subkey2'] += 1000
    config['key4']['subkey3'].append('new_value')
    config['key4']['subkey4']['subsubkey1'] += '_nested_value1'
    config['key4']['subkey4']['subsubkey2'] += 1000
    config['key4']['subkey4']['subsubkey3'].append('new_nested_value')
    config.encrypt('key1')
    config['key3'].encrypt(0)
    config['key4'].encrypt_key('subkey1')
    config['key4']['subkey4'].encrypt_key('subsubkey1')
    config['key4']['subkey4']['subsubkey3'].encrypt(0)
    pprint(config)
