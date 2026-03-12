from enum import Enum


# Role definitions that will be used across multiple applications.
# Changing these strings will have implications outside of this code base.
class VPRole(Enum):
    ORG_ADMIN = "org_admin"
    DATASET_ADMIN = "dataset_admin"
    DATASET_CONTRIBUTOR = "dataset_contributor"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(key.value, key.name) for key in cls]


# Verified permissions actions
# These strings must match the actions defined in verified permissions schema.
class VPAction(Enum):
    UPDATE_ORGANIZATION = "updateOrganization"
    GET_ORGANIZATION = "getOrganization"
    CREATE_UNIT = "createUnit"
    UPDATE_UNIT = "updateUnit"
    LIST_UNITS = "listUnits"
    GET_UNIT = "getUnit"
    DELETE_UNIT = "deleteUnit"

    CREATE_MACHINE_USER = "createMachineUser"
    LIST_MACHINE_USERS = "listMachineUsers"
    DELETE_MACHINE_USER = "deleteMachineUser"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(key.value, key.name) for key in cls]
