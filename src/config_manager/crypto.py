'''
Helper functions for the config manager, including encryption and decryption of sensitive data.
'''

from cryptography.fernet import Fernet, InvalidToken


TYPE_CAST_LIST = [int, float, bool, str]
TYPE_CAST_DICT = {t.__name__: t for t in TYPE_CAST_LIST}

def encrypt_data(data, key:bytes):
    ''' Encrypt the password and return it as a UTF-8 string '''
    if key:
        cipher_suite = Fernet(key)
        # if data isn't a string, convert to a string and append the type to the end so it can be cast back to the original type when decrypted
        if type(data) not in TYPE_CAST_LIST:
            raise ValueError(f"Data of type '{type(data).__name__}' cannot be encrypted, only the following types are supported: {', '.join([t.__name__ for t in TYPE_CAST_LIST])}")

        if not isinstance(data, str) and type(data) in TYPE_CAST_LIST:
            data = f"{str(data)}||::||{type(data).__name__}"

        # Encrypt the password (must be bytes) and decode the result to a string
        return cipher_suite.encrypt(data.encode()).decode('utf-8')

    # Return the original password if no key is provided
    return data


def decrypt_data(str_encrypted, key:bytes):
    ''' decrypt the password and return it, assumes encrypted and key are in UTF-8 format '''
    if key:
        cipher_suite = Fernet(key)
        try:
            decrypted = cipher_suite.decrypt(str_encrypted.encode()).decode('utf-8')
            # If the decrypted data contains the type marker, attempt to cast it back to the original type
            if '||::||' in decrypted:
                value, type_name = decrypted.rsplit('||::||', 1)
                if type_name in TYPE_CAST_DICT:
                    return TYPE_CAST_DICT[type_name](value)
            return decrypted
        except InvalidToken:
            # decrypt failed, so return the original string
            return str_encrypted

    # return the original string if no key provided
    return str_encrypted


def generate_encryption_key(filename:str|None=None):
    ''' Generate a new encryption key and return it as a UTF-8 string '''
    key = Fernet.generate_key()
    if filename:
        with open(filename, 'wb') as f:
            f.write(key)
    return key.decode('utf-8')


def is_encryption_key_valid(str_key):
    ''' Check if the provided encryption key is valid by trying to create a Fernet cipher suite with it. Returns True if valid, False if not. '''
    try:
        Fernet(str_key.encode())
        return True
    except Exception:
        return False


def is_data_encrypted(str_data, str_key):
    ''' Check if the provided data is encrypted by trying to decrypt it with the provided key. Returns True if decryption is successful, False if not. '''
    try:
        decrypt_data(str_data, str_key)
        return True
    except Exception:
        return False


