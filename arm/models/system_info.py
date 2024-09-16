from models.arm_models import ARMModel
from ui.ui_setup import db


class SystemInfo(ARMModel):
    """
    ARM Database Model - System Information

    This class holds details about the system (server), including system ID,
    name, CPU, description, and total memory.

    Database Table:
        system_info

    Attributes:
        id (int): The unique identifier for the system information.
        name (str): The name of the system.
        cpu (str): CPU information of the system.
        description (str): Description of the system.
        mem_total (float): Total memory of the system.

    Relationships:
        None
    """
    __tablename__ = 'system_info'

    id = db.Column(db.Integer, index=True, primary_key=True)
    name = db.Column(db.String(100))
    cpu = db.Column(db.String(20))
    description = db.Column(db.Unicode(200))
    mem_total = db.Column(db.Float())

    def __init__(self, name: str = "ARM Server", description: str = "Automatic Ripping Machine UI server"):
        self.name = name
        self.description = description
