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
    __abstract__ = True  # define as an abstract class not linked to a table
    __bind_key__ = 'mysql'  # default connector to the mysql database

    hidden_attribs: tuple = ()
    HIDDEN_VALUE: str = "<hidden>"

    @classmethod
    def change_binds(cls, bind_key):
        """
        Define the bind for related tables Track and Config

        Attributes:
            Bind Key: reference to the database config to use
        """
        cls.__bind_key__ = bind_key
        return cls

    def __repr__(self):
        """
        Return a string representation of the instance.

        Returns:
            str: A string representation of the instance in the format '<ClassName id>'.
        """
        return f'<{self.__class__.__name__} {self.id}>'

    def __str__(self):
        """
        Returns a comprehensive string representation of the object.
        Includes basic information and detailed attribute values.
        """
        # Basic representation
        return_string = self.__class__.__name__ + ": "

        # Detailed attribute representation
        for attr, value in self.__dict__.items():
            if attr in self.hidden_attribs:
                value = self.HIDDEN_VALUE
            return_string += f"({attr}={value}) "

        return return_string.strip()  # Remove trailing space

    def list_params(self):
        """Returns a string of the object"""
        return_string = self.__class__.__name__ + ": "
        for attr, value in self.__dict__.items():
            if return_string:
                return_string = return_string + "\n"
            if str(attr) in self.hidden_attribs and value:
                value = self.HIDDEN_VALUE
            return_string = return_string + str(attr) + ":" + str(value)

        return return_string

    def get_d(self) -> dict:
        """
        Return a dict of class - exclude any sensitive info and specific internal attributes.

        :return: dict containing all attribs from class
        """
        return_dict = {}
        for key, value in self.__dict__.items():
            if key not in self.hidden_attribs and '_sa_instance_state' not in key:
                return_dict[str(key)] = str(value)
        return return_dict
