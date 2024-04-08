import configparser
import sys
import json


def get_odoo_config_values(file_path: str) -> str:
    config = configparser.ConfigParser()
    config.read(file_path)

    fallback_values = {
        "db_host": "localhost",
        "db_port": "5432",
        "db_user": "odoo",
        "db_password": "",
        "db_name": "odoo",
    }

    config_values = {}
    for key, fallback in fallback_values.items():
        value = config.get("options", key, fallback=fallback)
        config_values[key] = value if value != "False" else fallback

    return json.dumps(config_values)


if __name__ == "__main__":
    config_file_path = sys.argv[1]
    print(get_odoo_config_values(config_file_path))
