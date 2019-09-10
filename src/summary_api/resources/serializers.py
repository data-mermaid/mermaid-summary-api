from collections import OrderedDict
from django.core.exceptions import ImproperlyConfigured
from rest_framework.serializers import (
    ModelSerializer, ListSerializer, LIST_SERIALIZER_KWARGS,
    UUIDField, CharField, SerializerMethodField,
)
from ..models import SummarySiteView
from ..utils import set_precision


class GeoFeatureModelListSerializer(ListSerializer):
    @property
    def data(self):
        return super(ListSerializer, self).data

    def to_representation(self, data):
        """
        Add GeoJSON compatible formatting to a serialized queryset list
        """
        return OrderedDict((
            ("type", "FeatureCollection"),
            ("features", super().to_representation(data))
        ))


# Subset of https://github.com/djangonauts/django-rest-framework-gis
# stripped down to what we need to deal with simple points, sans GDAL
class GeoFeatureModelSerializer(ModelSerializer):

    @classmethod
    def many_init(cls, *args, **kwargs):
        child_serializer = cls(*args, **kwargs)
        list_kwargs = {'child': child_serializer}
        list_kwargs.update(dict([
            (key, value) for key, value in kwargs.items()
            if key in LIST_SERIALIZER_KWARGS
        ]))
        meta = getattr(cls, 'Meta', None)
        list_serializer_class = getattr(meta, 'list_serializer_class', GeoFeatureModelListSerializer)
        return list_serializer_class(*args, **list_kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        meta = getattr(self, 'Meta')
        default_id_field = None
        primary_key = self.Meta.model._meta.pk.name
        # use primary key as id_field when possible
        if not hasattr(meta, 'fields') or meta.fields == '__all__' or primary_key in meta.fields:
            default_id_field = primary_key
        meta.id_field = getattr(meta, 'id_field', default_id_field)

        if not hasattr(meta, 'geo_field') or not meta.geo_field:
            raise ImproperlyConfigured("You must define a 'geo_field'.")

        def check_excludes(field_name, field_role):
            """make sure the field is not excluded"""
            if hasattr(meta, 'exclude') and field_name in meta.exclude:
                raise ImproperlyConfigured("You cannot exclude your '{0}'.".format(field_role))

        def add_to_fields(field_name):
            """Make sure the field is included in the fields"""
            if hasattr(meta, 'fields') and meta.fields != '__all__':
                if field_name not in meta.fields:
                    if type(meta.fields) is tuple:
                        additional_fields = (field_name,)
                    else:
                        additional_fields = [field_name]
                    meta.fields += additional_fields

        check_excludes(meta.geo_field, 'geo_field')
        add_to_fields(meta.geo_field)

    def to_representation(self, instance):
        feature = OrderedDict()
        # the list of fields that will be processed by get_properties
        # we will remove fields that have been already processed
        # to increase performance on large numbers
        fields = list(self.fields.values())

        # optional id attribute
        if self.Meta.id_field:
            field = self.fields[self.Meta.id_field]
            value = field.get_attribute(instance)
            feature["id"] = field.to_representation(value)
            fields.remove(field)

        # required type attribute
        # must be "Feature" according to GeoJSON spec
        feature["type"] = "Feature"

        # required geometry attribute
        # MUST be present in output according to GeoJSON spec
        field = self.fields[self.Meta.geo_field]
        geo_value = field.get_attribute(instance)
        feature["geometry"] = field.to_representation(geo_value)
        if hasattr(self.Meta, 'coord_precision') and self.Meta.coord_precision is not None:
            feature["geometry"]["coordinates"] = set_precision(
                feature["geometry"]["coordinates"],
                self.Meta.coord_precision
            )
        fields.remove(field)

        # GeoJSON properties
        feature["properties"] = self.get_properties(instance, fields)

        return feature

    def get_properties(self, instance, fields):
        properties = OrderedDict()

        for field in fields:
            if field.write_only:
                continue
            value = field.get_attribute(instance)
            representation = None
            if value is not None:
                representation = field.to_representation(value)
            properties[field.field_name] = representation

        return properties

    def to_internal_value(self, data):
        """
        Override the parent method to first remove the GeoJSON formatting
        """
        if 'properties' in data:
            data = self.unformat_geojson(data)
        return super().to_internal_value(data)

    def unformat_geojson(self, feature):
        """
        This function should return a dictionary containing keys which maps
        to serializer fields.

        Remember that GeoJSON contains a key "properties" which contains the
        feature metadata. This should be flattened to make sure this
        metadata is stored in the right serializer fields.

        :param feature: The dictionary containing the feature data directly
                        from the GeoJSON data.
        :return: A new dictionary which maps the GeoJSON values to
                 serializer fields
        """
        attrs = feature["properties"]

        if 'geometry' in feature:
            attrs[self.Meta.geo_field] = feature['geometry']

        return attrs


class SummarySiteSerializer(GeoFeatureModelSerializer):
    site_id = UUIDField(required=False)
    site_name = CharField(required=False)
    project_id = UUIDField(required=False)
    project_name = CharField(required=False)
    country_name = CharField(required=False)
    contact_link = CharField(required=False)
    data_policy_beltfish = CharField(required=False)
    data_policy_benthiclit = CharField(required=False)
    data_policy_benthicpit = CharField(required=False)
    data_policy_habitatcomplexity = CharField(required=False)
    data_policy_bleachingqc = CharField(required=False)
    reef_type = CharField(required=False)
    reef_zone = CharField(required=False)
    exposure = CharField(required=False)
    point = SerializerMethodField()
    # lat = DecimalField(max_digits=16, decimal_places=14, coerce_to_string=False, required=False)
    # lon = DecimalField(max_digits=17, decimal_places=14, coerce_to_string=False, required=False)

    def get_point(self, obj):
        return {
            'type': 'Point',
            'coordinates': [obj.lon, obj.lat]
        }

    class Meta:
        model = SummarySiteView
        geo_field = 'point'
        coord_precision = 6  # to nearest 10cm
        fields = ['site_id', 'site_name', 'site_notes', 'project_id', 'project_name', 'project_notes',
                  'country_name', 'contact_link',
                  'data_policy_beltfish', 'data_policy_benthiclit',
                  'data_policy_benthicpit', 'data_policy_habitatcomplexity', 'data_policy_bleachingqc',
                  'reef_type', 'reef_zone',
                  'exposure', 'tags', 'project_admins', 'date_min', 'date_max', 'depth',
                  'management_regimes', 'protocols']
