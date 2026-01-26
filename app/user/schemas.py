from ninja import Schema


class MachineUserSchema(Schema):
    name: str
    client_id: str
    # client_secret only returned on initial creation of machine user
    client_secret: str | None = None


class MachineUserListSchema(Schema):
    items: list[MachineUserSchema]


class CreateMachineUserSchema(Schema):
    name: str
    token_duration_min: int | None = None
