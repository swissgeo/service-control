from decimal import Decimal

from harvest.import_models import DynamoDBParsableModel


def test_dynamodb_parsable_model():
    class MyModel(DynamoDBParsableModel):
        string: str
        number_int: Decimal
        number_float: Decimal
        list: list
        map: dict
        null: None
        bool_true: bool
        bool_false: bool

    model = MyModel.from_dynamodb_item(
        {
            "string": {"S": "value"},
            "number_int": {"N": "10"},
            "number_float": {"N": "10.1"},
            "list": {"L": [{"S": "value"}]},
            "map": {"M": {"key": {"S": "value"}}},
            "null": {"NULL": True},
            "bool_true": {"BOOL": True},
            "bool_false": {"BOOL": False},
        }
    )
    assert model.string == "value"
    assert model.number_int == Decimal(10)
    assert model.number_float == Decimal("10.1")
    assert model.list == ["value"]
    assert model.map == {"key": "value"}
    assert model.null is None
    assert model.bool_true is True
    assert model.bool_false is False
