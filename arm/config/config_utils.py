import re


def arm_yaml_check_groups(comments: dict[str, str], key: str) -> str:
    """
    Check the current key to be added to arm.yaml and insert the group
    separator comment, if the key matches\n
    :param comments: comments dict, containing all comments from the arm.yaml
    :param key: the current post key from form.args
    :return: arm.yaml config with any new comments added
    """
    comment_groups = {'COMPLETED_PATH': "\n" + comments['ARM_CFG_GROUPS']['DIR_SETUP'],
                      'WEBSERVER_IP': "\n" + comments['ARM_CFG_GROUPS']['WEB_SERVER'],
                      'SET_MEDIA_PERMISSIONS': "\n" + comments['ARM_CFG_GROUPS']['FILE_PERMS'],
                      'RIPMETHOD': "\n" + comments['ARM_CFG_GROUPS']['MAKE_MKV'],
                      'HB_PRESET_DVD': "\n" + comments['ARM_CFG_GROUPS']['HANDBRAKE'],
                      'EMBY_REFRESH': "\n" + comments['ARM_CFG_GROUPS']['EMBY']
                                      + "\n" + comments['ARM_CFG_GROUPS']['EMBY_ADDITIONAL'],
                      'NOTIFY_RIP': "\n" + comments['ARM_CFG_GROUPS']['NOTIFY_PERMS'],
                      'APPRISE': "\n" + comments['ARM_CFG_GROUPS']['APPRISE']}
    if key in comment_groups:
        arm_cfg = comment_groups[key]
    else:
        arm_cfg = ""
    return arm_cfg


def arm_yaml_test_bool(key: str, value: str) -> str:
    """
    we need to test if the key is a bool, as we need to lower() it for yaml\n\n
    or check if key is the webserver ip. \nIf not we need to wrap the value with quotes\n
    :param key: the current key
    :param value: the current value
    :return: the new updated arm.yaml config with new key: values
    """
    if value.lower() == 'false' or value.lower() == "true":
        arm_cfg = f"{key}: {value.lower()}\n"
    else:
        # If we got here, the only key that doesn't need quotes is the webserver key
        # everything else needs "" around the value
        if key == "WEBSERVER_IP":
            arm_cfg = f"{key}: {value.lower()}\n"
        else:
            # This isn't intended to be safe, it's to stop breakages - replace all non escaped quotes with escaped
            escaped = re.sub(r"(?<!\\)[\"\'`]", r'\"', value)
            arm_cfg = f"{key}: \"{escaped}\"\n"
    return arm_cfg


def arm_yaml_check_bool(value: str) -> bool:
    """
    we need to test if the key is a bool, as we need to lower() it for yaml\n\n
    or check if key is the webserver ip. \nIf not we need to wrap the value with quotes\n
    :param key: the current key
    :param value: the current value
    :return: the new updated arm.yaml config with new key: values
    """
    if value.lower() == 'false' or value.lower() == "true":
        return True
    else:
        return False


def arm_yaml_return_bool(key: str, value: str) -> str:
    """
    we need to test if the key is a bool, as we need to lower() it for yaml\n\n
    or check if key is the webserver ip. \nIf not we need to wrap the value with quotes\n
    :param key: the current key
    :param value: the current value
    :return: the new updated arm.yaml config with new key: values
    """
    if value.lower() == 'false' or value.lower() == "true":
        return f"{key}: {value.lower()}\n"
    else:
        raise ValueError("Value is not a boolean string.")


def arm_yaml_test_and_clean_text(text: str) -> str:
    """
    Basic text cleaning for text fields.  Removes non-ASCII and non-printable characters.
    Strips leading/trailing whitespace and removes all internal whitespace characters.

    This is not the safest way to do things.
    It assumes the user isn't trying to mess with us.
    This really should be hard coded.
    """
    if not all(ord(c) < 128 for c in text):
        raise Exception("Field must not contain non-ASCII characters.")
        # check for non-printable characters
    if not all(c.isprintable() for c in text):
        raise Exception("Field must not contain non-printable characters.")
    # remove whitespace
    return text.strip().replace("\t", "").replace("\n", "").replace("\r", "").replace("\f", "").replace("\v", "")


def arm_yaml_is_int(text: str) -> bool:
    """
    Check if the provided text can be converted to an integer.
    :param text: The text to check.
    :return: True if the text can be converted to an integer, False otherwise.
    """
    try:
        int(text)
        return True
    except ValueError:
        return False


def arm_key_value(key: str, value: str) -> str:
    """
    Return a key: value pair for arm.yaml, with the value lowercased.
    This is used for boolean values.
    :param key: The key to use.
    :param value: The value to use.
    :return: A string in the format "key: value\n"
    """
    return f"{key}: {value.lower()}\n"
