import configparser


def get_odoo_config_values(
    config_file_path: str,
) -> tuple[str, str, str, str, str]:
    config = configparser.ConfigParser()
    config.read(config_file_path)

    db_host = config.get("options", "db_host", fallback="localhost")
    db_port = config.get("options", "db_port", fallback="5432")
    db_user = config.get("options", "db_user", fallback="odoo")
    db_password = config.get("options", "db_password", fallback=False)
    db_name = config.get("options", "db_name", fallback="odoo")

    return db_host, db_port, db_name, db_user, db_password
