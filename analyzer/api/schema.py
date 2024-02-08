from datetime import date

from marshmallow import Schema, validates, ValidationError, validates_schema
from marshmallow.fields import Str, Int, Date, List, Nested
from marshmallow.validate import Length, OneOf, Range

from analyzer.config import Config
from analyzer.db.schema import Gender


class PatchCitizenSchema(Schema):
    name = Str(validate=Length(min=1, max=256))
    gender = Str(validate=OneOf([gender.value for gender in Gender]))
    birth_date = Date(format=Config.BIRTH_DATE_FORMAT)
    town = Str(validate=Length(min=1, max=256))
    street = Str(validate=Length(min=1, max=256))
    building = Str(validate=Length(min=1, max=256))
    apartment = Int(validate=Range(min=0), strict=True)
    relatives = List(Int(validate=Range(min=0), strict=True))

    @validates("birth_date")
    def validate_birth_date(self, value: date):
        if value > date.today():
            raise ValidationError("Birth date can't be in the future")

    @validates("relatives")
    def validate_relatives_unique(self, value: list):
        if len(value) != len(set(value)):
            raise ValidationError("relatives ids must be unique values")


class CitizenSchema(PatchCitizenSchema):
    citizen_id = Int(validate=Range(min=0), strict=True, required=True)
    name = Str(validate=Length(min=1, max=256), required=True)
    gender = Str(validate=OneOf([gender.value for gender in Gender]), required=True)
    birth_date = Date(format=Config.BIRTH_DATE_FORMAT, required=True)
    town = Str(validate=Length(min=1, max=256), required=True)
    street = Str(validate=Length(min=1, max=256), required=True)
    building = Str(validate=Length(min=1, max=256), required=True)
    apartment = Int(validate=Range(min=0), strict=True, required=True)
    relatives = List(Int(validate=Range(min=0), strict=True), required=True)


class CitizensResponseSchema(Schema):
    data = Nested(CitizenSchema(), required=True)


class ImportsSchema(Schema):
    citizens = Nested(
        CitizenSchema,
        many=True,
        required=True,
        validate=Length(max=Config.MAX_CITIZEN_INSTANCES_WITHIN_IMPORT),
    )

    @validates_schema
    def validate_unique_citizen_id(self, data, **_):
        citizen_ids = set()
        for citizen in data["citizens"]:
            if citizen["citizen_id"] in citizen_ids:
                raise ValidationError(
                    f"citizen_id {citizen['citizen_id']} is not unique"
                )

            citizen_ids.add(citizen["citizen_id"])

    @validates_schema
    def validate_bidirectional_relation_between_relatives(self, data, **_):
        relatives = {
            citizen["citizen_id"]: set(citizen["relatives"])
            for citizen in data["citizens"]
        }
        for citizen_id, relative_ids in relatives.items():
            for relative_id in relative_ids:
                if citizen_id not in relatives.get(relative_id, set()):
                    raise ValidationError(
                        f"citizen {relative_id} does not have relation with {citizen_id}"
                    )


class ImportsIdSchema(Schema):
    import_id = Int(validate=Range(min=0), strict=True, required=True)


class ImportsResponseSchema(Schema):
    data = Nested(ImportsIdSchema(), required=True)
