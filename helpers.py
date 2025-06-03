from hashlib import sha3_512
from queries import get_user_password, create_user


def hash_password(password):
    return sha3_512(password.encode('utf-8')).hexdigest()


def verify_signup(user_name, full_name, address, bio, avatar_url, password):
    '''checks if username is available and tries to create user.
    Returns (True, user_dict) or (False, error_message)
    '''
    username_available = not get_user_password(user_name)
    if username_available:
        encrypted_password = hash_password(password)
        new_user = create_user(user_name, full_name, address, bio, avatar_url, encrypted_password)
        if new_user:
            return True, new_user
        else:
            return False, "Something went wrong. Couldn't create your account"
    else:
        return False, "Username already exists"


def verify_signin(user_name, password):
    '''checks if password is valid for given username
    Returns (True, None) or (False, error_message)
    '''
    user_password = get_user_password(user_name)

    if user_password:  # user exists
        entered_password = hash_password(password)
        if entered_password == user_password:
            return True, None
        else:
            return False,    "Incorrect password"
    else:
        return False, "Username not found"
