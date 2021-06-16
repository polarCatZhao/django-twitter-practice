from django.core import serializers
from utils.json_encoder import JSONEncoder


class DjangoModelSerializer:

    @classmethod
    def serialize(cls, instance):
        # Because Django's serializers would serialize a queryset
        # (or any iterator that returns database objects),
        # the instance needs to be made into a list first by adding [].
        return serializers.serialize('json', [instance], cls=JSONEncoder)

    @classmethod
    def deserialize(cls, serialized_data):
        # .object needs to be added to obtain the original object of the model,
        # otherwise the return value is a DeserializedObject rather than an ORM object
        return list(serializers.deserialize('json', serialized_data))[0].object
