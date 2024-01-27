def migrate(cr, version):
    cr.execute(
        """
        ALTER TABLE product_import
        RENAME COLUMN type TO product_type
    """
    )
