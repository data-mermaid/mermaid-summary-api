import uuid
import geojson
from json.decoder import JSONDecodeError
from django.utils.translation import ugettext as _
from rest_framework.exceptions import ParseError


def check_uuid(pk):
    if isinstance(pk, uuid.UUID):
        return pk
    try:
        uuid.UUID(pk)
        return pk
    except (ValueError, TypeError):
        raise ParseError(
            detail=_("'%(value)s' is not a valid uuid") % {'value': pk}
        )


# a valid geojson poly input string is one that serializes to a dict with a 'coordinates' key at the top level,
# and can be used to create a valid Polygon or MultiPolygon that can be used in a postgis query
# This is currently based on a simple Geometry, but could easily be extended to support a Feature
def valid_poly(value):
    value = value.replace("'", "\"")
    try:
        d = geojson.loads(value)  # adds empty 'coordinates' item to dict
        if 'coordinates' not in d or len(d['coordinates']) == 0:
            raise ParseError(
                detail=_("Unable to find 'coordinates' in search GeoJSON object")
            )
        else:
            coords = d['coordinates']
            poly = geojson.Polygon(coords)
            multipoly = geojson.MultiPolygon(coords)
            if not poly.is_valid and not multipoly.is_valid:
                raise ParseError(
                    detail=_("Not a valid geojson polygon or multipolygon: '{}'".format(value))
                )
    except JSONDecodeError:
        raise ParseError(
            detail=_("Not a valid geojson polygon or multipolygon: '{}'".format(value))
        )

    return value


# From https://github.com/perrygeo/geojson-precision sans shapely dependency
def set_precision(coords, precision):
    result = []
    try:
        return round(coords, int(precision))
    except TypeError:
        for coord in coords:
            result.append(set_precision(coord, precision))
    return result
