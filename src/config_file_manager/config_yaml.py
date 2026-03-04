from typing import Any
import yaml
from logging_handler import INFO
from . import ConfigDict, ConfigList


def ConfigDictRepresenter(dumper, data):
    ''' Custom YAML representer for ConfigDict objects that represents them as their underlying data dictionary '''
    return dumper.represent_dict(data.data)

def ConfigListRepresenter(dumper, data):
    ''' Custom YAML representer for ConfigList objects that represents them as their underlying data list '''
    return dumper.represent_list(data.data)

yaml.add_representer(ConfigDict, ConfigDictRepresenter)
yaml.add_representer(ConfigList, ConfigListRepresenter)

class ConfigManagerYamlDict(ConfigDict):
    ''' A config manager that can load config data from a YAML file. '''
    def __init__(self, *args, config_file:str, log_level=INFO, encryption_key=None, save_on_change=False, **kwargs):
        super().__init__(log_level=log_level, encryption_key=encryption_key, *args, **kwargs)
        self._config_file = config_file
        self._save_on_change = save_on_change

        # Set the update callback to save the config file when a config value is updated if save_on_change is True
        self._update_callback = self.__save_callback

        with open(self._config_file, 'r', encoding='utf-8') as input_file:
            config_data = yaml.safe_load(input_file)
            self.load_config(config_data)

    @property
    def save_on_change(self):
        ''' Get the save_on_change value '''
        return self._save_on_change

    @save_on_change.setter
    def save_on_change(self, value:bool):
        ''' Set the save_on_change value '''
        self._save_on_change = value

    def __save_callback(self):
        ''' Callback function to save the config file when a config value is updated if save_on_change is True '''
        if self._save_on_change:
            self.save_config()

    def __setitem__(self, key: Any, item: Any) -> None:
        ''' Update the config data in the YAML file when a config value is set '''
        super().__setitem__(key, item)
        if self._save_on_change:
            self.save_config()

    def save_config(self):
        ''' Save the current config data to the YAML file '''
        with open(self._config_file, 'w', encoding='utf-8') as output_file:
            yaml.dump(self.data, output_file, default_flow_style=False)

    def encrypt(self, key):
        ''' Encrypt a key in the config and save the file if save_on_change is True '''
        super().encrypt(key)
        if self._save_on_change:
            self.save_config()

    def decrypt(self, key):
        ''' Decrypt a key in the config and save the file if save_on_change is True '''
        super().decrypt(key)
        if self._save_on_change:
            self.save_config()
