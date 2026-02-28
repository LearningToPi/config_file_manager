from collections import UserList, UserDict
from typing import Any, Callable, Iterable
from logging_handler import INFO, create_logger
from .crypto import decrypt_data, encrypt_data


class ConfigDict(UserDict):
    ''' A simple config manager that can be used to store and retrieve configuration data. This is used to store data that needs to be accessed by multiple modules, such as the SQL connections. '''
    def __init__(self, *args, log_level:str=INFO, encryption_key:bytes|None=None, encryption_key_file:str|None=None, update_callback:Callable|None=None, **kwargs):
        self._logger, self._log_level = create_logger(log_level, name=self.__class__.__name__), log_level
        if encryption_key_file is not None:
            with open(encryption_key_file, 'rb') as key_file:
                self._encryption_key = key_file.read()
        else:
            self._encryption_key = encryption_key
        self._update_callback = update_callback
        super().__init__(**kwargs)
        self.load_config(*args)

    def __repr__(self):
        return {key: value for key, value in self.items()}.__repr__()

    def __getitem__(self, key: Any) -> Any:
        data = super().__getitem__(key)
        if isinstance(data, str) and self._encryption_key is not None and data.startswith('gAAAA'):
            data = decrypt_data(data, self._encryption_key)
        return data

    def __setitem__(self, key: Any, item: Any) -> None:
        if isinstance(item, str) and self._encryption_key is not None and self.is_encrypted(key):
            item = encrypt_data(item, self._encryption_key)
        super().__setitem__(key, item)
        if self._update_callback is not None:
            self._update_callback()

    def __delitem__(self, key) -> None:
        super().__delitem__(key)
        if self._update_callback is not None:
            self._update_callback()

    def _save_callback(self):
        ''' Callback function to save the config file when a config value is updated if save_on_change is True '''

    def load_config(self, *args):
        ''' Pass a string to load a json config file, or a dict to load config data from a dict '''
        self.data = {}
        for arg in args:
            for key, value in arg.items():
                if isinstance(value, dict):
                    self.data[key] = ConfigDict(log_level=self._log_level, encryption_key=self._encryption_key, update_callback=self._update_callback)
                    self.data[key].load_config(value)
                elif isinstance(value, list):
                    self.data[key] = ConfigList(log_level=self._log_level, encryption_key=self._encryption_key, update_callback=self._update_callback)
                    self.data[key].load_config(value)
                else:
                    self.data[key] = value

    def is_encrypted(self, key):
        ''' Check if the value for a key is encrypted. For the dict, check if value is a string and starts with 'gAAAA' which is the prefix for Fernet encrypted data '''
        if key in self.data and isinstance(self.data[key], str) and self.data[key].startswith('gAAAA'):
            return True
        return False

    def encrypt(self, key):
        ''' Encrypt a key in the config if it is not already encrypted '''
        if self._encryption_key is None:
            self._logger.warning(f"Encryption key not provided, cannot encrypt config key '{key}'")
            return
        if key in self.data:
            if not self.is_encrypted(key):
                value = self.data[key]
                encrypted_value = encrypt_data(value, self._encryption_key)
                self.data[key] = encrypted_value
                self._logger.info(f"Config key '{key}' has been encrypted")
                if self._update_callback is not None:
                    self._update_callback()
            else:
                self._logger.info(f"Config key '{key}' is already encrypted")
        else:
            self._logger.error(f"Config key '{key}' not found when trying to encrypt")
            raise KeyError(f"Config key '{key}' not found when trying to encrypt")

    def decrypt(self, key):
        ''' Decrypt a key in the config if it is encrypted '''
        if self._encryption_key is None:
            self._logger.warning(f"Encryption key not provided, cannot decrypt config key '{key}'")
            return
        if key in self.data:
            if self.is_encrypted(key):
                value = self.data[key]
                decrypted_value = decrypt_data(value, self._encryption_key)
                self.data[key] = decrypted_value
                self._logger.info(f"Config key '{key}' has been decrypted")
                if self._update_callback is not None:
                    self._update_callback()
            else:
                self._logger.info(f"Config key '{key}' is not encrypted")
        else:
            self._logger.error(f"Config key '{key}' not found when trying to decrypt")
            raise KeyError(f"Config key '{key}' not found when trying to decrypt")


class ConfigList(UserList):
    ''' A simple config list that can be used to store and retrieve configuration data in a list format. 
    This is used to store data that needs to be accessed by multiple modules, such as the SQL connections. '''
    def __init__(self, *args, log_level:str=INFO, encryption_key=None, update_callback:Callable|None=None, **kwargs):
        self._logger, self._log_level = create_logger(log_level, name=self.__class__.__name__), log_level
        self._encryption_key = encryption_key
        self._update_callback = update_callback
        super().__init__(**kwargs)
        self.load_config(*args)

    def __repr__(self) -> str:
        return [item for item in self].__repr__()

    def load_config(self, *args):
        ''' Pass a string to load a json config file, or a list to load config data from a list '''
        self.data = []
        for arg in args:
            for item in arg:
                if isinstance(item, dict):
                    new_item = ConfigDict(log_level=self._log_level, encryption_key=self._encryption_key, update_callback=self._update_callback)
                    new_item.load_config(item)
                    self.data.append(new_item)
                elif isinstance(item, list):
                    new_item = ConfigList(log_level=self._log_level, encryption_key=self._encryption_key, update_callback=self._update_callback)
                    new_item.load_config(item)
                    self.data.append(new_item)
                else:
                    self.data.append(item)

    def is_encrypted(self, index):
        ''' Check if an item in the list is encrypted '''
        if index < len(self.data):
            item = self.data[index]
            if isinstance(item, str) and item.startswith('gAAAA'):
                return True
        return False

    def encrypt(self, index):
        ''' Encrypt an item in the list if it is not already encrypted '''
        if self._encryption_key is None:
            self._logger.warning(f"Encryption key not provided, cannot encrypt config item at index '{index}'")
            return
        if index < len(self.data):
            if not self.is_encrypted(index):
                value = self.data[index]
                encrypted_value = encrypt_data(value, self._encryption_key)
                self.data[index] = encrypted_value
                self._logger.info(f"Config item at index '{index}' has been encrypted")
                if self._update_callback is not None:
                    self._update_callback()

            else:
                self._logger.info(f"Config item at index '{index}' is already encrypted")
        else:
            self._logger.error(f"Config item index '{index}' is out of range for encryption")

    def decrypt(self, index):
        ''' Decrypt an item in the list if it is encrypted '''
        if self._encryption_key is None:
            self._logger.warning(f"Encryption key not provided, cannot decrypt config item at index '{index}'")
            return
        if index < len(self.data):
            if self.is_encrypted(index):
                value = self.data[index]
                decrypted_value = decrypt_data(value, self._encryption_key)
                self.data[index] = decrypted_value
                self._logger.info(f"Config item at index '{index}' has been decrypted")
                if self._update_callback is not None:
                    self._update_callback()
            else:
                self._logger.info(f"Config item at index '{index}' is not encrypted")
        else:
            self._logger.error(f"Config item index '{index}' is out of range for decryption")

    def __getitem__(self, index: int) -> Any:
        ''' Return the value for the requested config key '''
        data = super().__getitem__(index)
        if isinstance(data, str) and data.startswith('gAAAA'):
            if self._encryption_key is not None:
                try:
                    decrypted_data = decrypt_data(data, self._encryption_key)
                    return decrypted_data
                except Exception as e:
                    self._logger.error(f"Error decrypting config item at index '{index}': {e}")
                    raise ValueError(f"Error decrypting config item at index '{index}': {e}") from e
            else:
                self._logger.warning(f"Encryption key not provided, cannot decrypt config item at index '{index}'")
        return data

    def __setitem__(self, index: int, item: Any) -> None:
        ''' Update the config data when a config value is set '''
        super().__setitem__(index, item)
        if self._update_callback is not None:
            self._update_callback()

    def __delitem__(self, i) -> None:
        super().__delitem__(i)
        if self._update_callback is not None:
            self._update_callback()

    def __add__(self, other: Iterable):
        return_data = super().__add__(other)
        if self._update_callback is not None:
            self._update_callback()
        return return_data

    def __radd__(self, other: Iterable):
        return_data = super().__radd__(other)
        if self._update_callback is not None:
            self._update_callback()
        return return_data

    def __iadd__(self, other: Iterable):
        return_data = super().__iadd__(other)
        if self._update_callback is not None:
            self._update_callback()
        return return_data

    def __mul__(self, n: int):
        return_data = super().__mul__(n)
        if self._update_callback is not None:
            self._update_callback()
        return return_data

    def __imul__(self, n: int):
        return_data = super().__imul__(n)
        if self._update_callback is not None:
            self._update_callback()
        return return_data

    def append(self, item: Any) -> None:
        super().append(item)
        if self._update_callback is not None:
            self._update_callback()

    def insert(self, i: int, item: Any) -> None:
        super().insert(i, item)
        if self._update_callback is not None:
            self._update_callback()

    def pop(self, i: int = -1) -> Any:
        return_data = super().pop(i)
        if self._update_callback is not None:
            self._update_callback()
        if isinstance(return_data, str) and return_data.startswith('gAAAA'):
            if self._encryption_key is not None:
                try:
                    decrypted_data = decrypt_data(return_data, self._encryption_key)
                    return decrypted_data
                except Exception as e:
                    self._logger.error(f"Error decrypting config item at index '{i}': {e}")
                    raise ValueError(f"Error decrypting config item at index '{i}': {e}") from e
            else:
                self._logger.warning(f"Encryption key not provided, cannot decrypt config item at index '{i}'")
        return return_data

    def remove(self, item: Any) -> None:
        super().remove(item)
        if self._update_callback is not None:
            self._update_callback()

    def clear(self) -> None:
        super().clear()
        if self._update_callback is not None:
            self._update_callback()

    def reverse(self) -> None:
        super().reverse()
        if self._update_callback is not None:
            self._update_callback()

    def sort(self, *, key=None, reverse=False) -> None:
        super().sort(key=key, reverse=reverse)
        if self._update_callback is not None:
            self._update_callback()

    def extend(self, other: Iterable) -> None:
        super().extend(other)
        if self._update_callback is not None:
            self._update_callback()
