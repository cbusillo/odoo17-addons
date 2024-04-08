import configparser
import sys


def get_odoo_config_values(
    file_path: str,
) -> tuple[str, str, str, str, str]:
    config = configparser.ConfigParser()
    config.read(file_path)

    db_host = config.get("options", "db_host", fallback="localhost")
    db_port = config.get("options", "db_port", fallback="5432")
    db_user = config.get("options", "db_user", fallback="odoo")
    db_password = config.get("options", "db_password", fallback="")
    db_name = config.get("options", "db_name", fallback="odoo")

    return db_host, db_port, db_name, db_user, db_password


if __name__ == "__main__":
    config_file_path = sys.argv[1]
    print(" ".join(get_odoo_config_values(config_file_path)))
