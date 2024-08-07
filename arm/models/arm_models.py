from ui.ui_setup import db


class ARMModel(db.Model):
    """
        ARM Database Model - ARM Base Class

        The ARM Model base class, defining global model properties
        for all ARM database models

        Database Table:
            None

        Attributes:
            None

        Relationships:
            None

        """
    __abstract__ = True         # define as an abstract class not linked to a table
    __bind_key__ = 'mysql'      # default connector to the mysql database

    @classmethod
    def change_binds(cls, bind_key):
        """
        Define the bind for related tables Track and Config

        Attributes:
            Bind Key: reference to the database config to use
        """
        cls.__bind_key__ = bind_key
        return cls
