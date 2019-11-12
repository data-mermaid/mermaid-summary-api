from django.db import models
from django.db.models import Q
from rest_framework import viewsets, mixins
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.utils.urls import remove_query_param, replace_query_param
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from drf_yasg.views import get_schema_view
from drf_yasg.openapi import Info, Contact, License, Schema, Items
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.inspectors import CoreAPICompatInspector, NotHandled
from ..utils import *
from .serializers import *


class GeoJsonPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'limit'
    max_page_size = 1000

    def paginate_queryset(self, queryset, request, view=None):
        if not request.query_params._mutable:
            request.query_params._mutable = True
        for p in [self.page_size_query_param, self.page_query_param]:
            if p in request.data:
                request.query_params[p] = request.data[p]
        return super(GeoJsonPagination, self).paginate_queryset(queryset, request, view)

    def get_next_link(self):
        if not self.page.has_next():
            return None
        page_number = self.page.next_page_number()
        if self.request.method == 'POST':
            return page_number
        url = self.request.build_absolute_uri()
        return replace_query_param(url, self.page_query_param, page_number)

    def get_previous_link(self):
        if not self.page.has_previous():
            return None
        page_number = self.page.previous_page_number()
        if self.request.method == 'POST':
            return page_number
        url = self.request.build_absolute_uri()
        if page_number == 1:
            return remove_query_param(url, self.page_query_param)
        return replace_query_param(url, self.page_query_param, page_number)

    # Based on https://github.com/djangonauts/django-rest-framework-gis/blob/master/rest_framework_gis/pagination.py
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('type', 'FeatureCollection'),
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('features', data['features'])
        ]))


class SummarySiteFilterSet(filters.FilterSet):
    tag_id = filters.UUIDFilter(field_name='tags', method='tag_by_id')
    tag_name = filters.CharFilter(field_name='tags', method='tag_by_name')
    management_regime_id = filters.UUIDFilter(field_name='management_regimes', method='mr_by_id')
    management_regime_name = filters.CharFilter(field_name='management_regimes', method='mr_by_name')
    geometry = filters.CharFilter(method='site_by_multipoly')
    date_min = filters.DateFromToRangeFilter()
    date_max = filters.DateFromToRangeFilter()
    include_test = filters.BooleanFilter(method='test_data_included')

    class Meta:
        model = SummarySiteView
        fields = ['site_id', 'site_name', 'project_id', 'project_name',
                  'data_policy_beltfish', 'data_policy_benthiclit',
                  'data_policy_benthicpit', 'data_policy_habitatcomplexity', 'data_policy_bleachingqc',
                  'country_name', 'tag_id', 'tag_name', 'management_regime_id', 'management_regime_name', 'geometry',
                  'date_min', 'date_max']

        filter_overrides = {
            models.CharField: {
                'filter_class': filters.CharFilter,
                'extra': lambda f: {
                    'lookup_expr': 'icontains',
                },
            },
        }

    def tag_by_id(self, queryset, name, value):
        # pk = check_uuid(value)
        return queryset.filter(tags__0__id=str(value))

    def tag_by_name(self, queryset, name, value):
        return queryset.filter(tags__0__name__icontains=value)

    def mr_by_id(self, queryset, name, value):
        return queryset.filter(management_regimes__0__id=str(value))

    def mr_by_name(self, queryset, name, value):
        return queryset.filter(management_regimes__0__name__icontains=value)

    def site_by_multipoly(self, queryset, name, value):
        poly = valid_poly(value)
        sql = """
            ST_Within(
                ST_Point(lon, lat), 
                ST_GeomFromGeoJSON('{}')
            )
        """.format(poly)

        return queryset.extra(where=[sql])

    def test_data_included(self, queryset, name, value):
        if value is True:
            return queryset.union(SummarySiteView.objects.filter(project_status=SummarySiteView.TEST))


class SummarySiteFilterInspector(CoreAPICompatInspector):
    field_descriptions = {
        'site_id': 'uuid of a site',
        'site_name': 'Name of a site; matching is done with case-insensitive "contains"',
        'project_id': 'uuid of a project',
        'project_name': 'Name of a project; matching is done with case-insensitive "contains"',
        'data_policy_beltfish': 'data policy chosen for project beltfish transects: private, public summary, or public',
        'data_policy_benthiclit': 'data policy chosen for project benthic LIT transects: private, public summary, '
                                  'or public',
        'data_policy_benthicpit': 'data policy chosen for project benthic PIT transects: private, public summary, '
                                  'or public',
        'data_policy_habitatcomplexity': 'data policy chosen for project habitat complexity transects: private, '
                                         'public summary, or public',
        'data_policy_bleachingqc': 'data policy chosen for project bleaching quadrat collections: private, '
                                   'public summary, or public',
        'country_name': 'Name of a country; matching is done with case-insensitive "contains"',
        'tag_id': 'uuid of a tag',
        'tag_name': 'Name of a tag associated with projects; matching is done with case-insensitive "contains". '
                    'Example: Wildlife Conservation Society',
        'management_regime_id': 'uuid of a management regime',
        'management_regime_name': 'Name of a management regime; matching is done with case-insensitive "contains"',
        'geometry': 'GeoJSON Polygon or MultiPolygon containing sites.\nFor details on geojson polygon and '
                    'multipolygon geometry formatting: https://tools.ietf.org/html/rfc7946#section-3.1.6 and '
                    'http://geojson.io/',
        'date_min': 'Range filter for specifying earliest date of data collected at site.\nSearch using parameters '
                    '"date_min_before" or "date_min_after" with date format like YYYY-MM-DD.',
        'date_max': 'Range filter for specifying earliest date of data collected at site.\nSearch using parameters '
                    '"date_max_before" or "date_max_after" with date format like YYYY-MM-DD.',
    }

    def get_filter_parameters(self, filter_backend):
        if isinstance(filter_backend, filters.DjangoFilterBackend):
            result = super().get_filter_parameters(filter_backend)
            for param in result:
                if self.field_descriptions.get(param.name):
                    param.description = self.field_descriptions[param.name]
            return result
        return NotHandled


class SummarySiteViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    serializer_class = SummarySiteSerializer
    pagination_class = GeoJsonPagination
    filterset_class = SummarySiteFilterSet

    def get_queryset(self):
        return SummarySiteView.objects.exclude(
            Q(project_status=SummarySiteView.TEST)
            | Q(management_regimes__isnull=True)
        ).order_by('project_name', 'site_name')

    geometry_example = """
    {"geometry": {"type": "MultiPolygon", "coordinates": [[[[179.044189453125, -18.280866245832026], 
    [179.6587371826172, -18.280866245832026], [179.6587371826172, -17.728412648167435], [179.044189453125, 
    -17.728412648167435], [179.044189453125, -18.280866245832026]]]]}}
    """

    template_response_feature = """
            {
                "id": "5a9daca8-b003-4d4c-8cac-77b2d5ef0bb1",
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        -73.696289,
                        41.013066
                    ]
                },
                "properties": {
                    "site_name": "Bronx Zoo",
                    "site_notes": "",
                    "project_id": "2c56b92b-ba1c-491f-8b62-23b1dc728890",
                    "project_name": "Bronx River",
                    "project_notes": "This is a project about the Great Bronx River Reef.",
                    "country_name": "United States",
                    "contact_link": "https://datamermaid.org/contact-project/?project_id=project_id=2c56b92b-ba1c-491f-8b62-23b1dc728890",
                    "data_policy_beltfish": "public summary",
                    "data_policy_benthiclit": "public summary",
                    "data_policy_benthicpit": "public summary",
                    "data_policy_habitatcomplexity": "public summary",
                    "data_policy_bleachingqc": "public summary",
                    "reef_type": "lagoon",
                    "reef_zone": "back reef",
                    "exposure": "very sheltered",
                    "tags": [
                        {	
                            "id": "24bd51ab-eab8-4a5b-896d-4fddd3885029",	
                            "name": "Wildlife Conservation Society"	
                        }
                    ],
                    "project_admins": [
                        {
                            "name": "Kim Fisher"
                        }
                    ],
                    "date_min": "2018-04-16",  // earliest sample unit date
                    "date_max": "2018-12-12",  // latest sample unit date
                    "depth": {
                        "max": 5.0,  // maximum depth of all sample units associated with site
                        "min": 1.0  // minimum depth of all sample units associated with site
                    },
                    "management_regimes": [  // all management regimes associated with all sample units associated 
                    with site. 
                        {
                            "id": "7d944a52-2174-4221-b0e0-5c9bdc59188b",
                            "name": "Bronx Zoo",
                            "notes": "Test Bronx Zoo management regime"
                        }
                    ],
                    "protocols": {
                        "beltfish": {
                            "biomass_kgha": 248.0,  // omitted if data_policy_beltfish = "private"	
                            "biomass_kgha_tg": [  // omitted if data_policy_beltfish = "private"
                                {
                                    "omnivore": 39.5
                                },
                                {
                                    "invertivore-mobile": 2.4
                                },
                                {
                                    "herbivore-macroalgae": 7.2
                                },
                                {
                                    "herbivore-detritivore": 131.2
                                },
                                {
                                    "planktivore": 2.8
                                },
                                {
                                    "piscivore": 64.8
                                }
                            ],
                            "sample_unit_count": 6
                        },
                        "benthiclit": {
                            "coral_cover": [  // omitted if data_policy_benthiclit = "private"	
                                {	
                                    "Fleshy macroalgae": 0.3
                                },	
                                {	
                                    "Hard coral": 0.7
                                }	
                            ],
                            "sample_unit_count": 1
                        },
                        "benthicpit": {
                            "coral_cover": [  // omitted if data_policy_benthicpit = "private"
                                {
                                    "Turf algae": 0.7
                                },
                                {
                                    "Hard coral": 0.3
                                }
                            ],
                            "sample_unit_count": 1
                        },
                        "habitatcomplexity": {
                            "score_avg": 2.5,  // omitted if data_policy_habitatcomplexity = "private"
                            "sample_unit_count": 1
                        },
                        "colonies_bleached": {  // all properties except "sample_unit_count" omitted if 
                        data_policy_bleachingqc = "private"
                            "avg_count_total": 236.0,
                            "avg_count_genera": 22.0,
                            "avg_percent_pale": 19.0,
                            "sample_unit_count": 1,
                            "avg_percent_normal": 76.0,
                            "avg_percent_bleached": 4.0
                        },
                        "quadrat_benthic_percent": {  // all properties except "sample_unit_count" omitted if 
                        data_policy_bleachingqc = "private"
                            "avg_percent_hard": 23.8,
                            "avg_percent_soft": 14.3,
                            "avg_percent_algae": 7.5,
                            "avg_quadrat_count": 20.0,
                            "sample_unit_count": 1
                        }
                    }
                }
            }"""

    list_description = """
    Endpoint for site-level data summaries. A site is associated with only one project, but many projects may have 
    sites at the same location. Summary metrics are therefore aggregated as averages of sample unit results for a 
    particular project at a particular site (i.e., a place (lat/lon) with a set of characteristics). If there are no 
    sites satisfying filter criteria, an empty list is returned for "features".
    
    This endpoint will return the same results from either GET or POST methods; POST is provided to allow for 
    larger filter parameter values than can be accomodated in urls (in particular, querying by complex polygons). 
    Filters are specified via key/val pairs. Filters can be specified via normal query string parameters, 
    for GET requests, or in a JSON object passed as the payload to the POST request, e.g.:
    {"site_name": "Bronx Zoo"}
    {"project_id": "2c56b92b-ba1c-491f-8b62-23b1dc728890"}
    {"site_name": "Bronx Zoo", "date_min": "2017-12-27", "date_max": "2018-01-10"}
    Multiple filters with different keys are combined using AND logic; multiple filters with the same key are combined 
    using OR logic.
    
    %s
    
    All results are paginated. Default page size is 100. Page size of up to 1000 may be requested by using the 
    parameter "limit"; pages using the page size are requested with "page". For GET requests,
    - "next" and "previous" values will be uris
    - "limit" and "page" passed in as query parameters
    For POST requests, 
    - "next" and "previous" values will be integers
    - "limit" and "page" passed in as part of the JSON-formatted payload (BODY)
    """ % geometry_example

    list_response = """
    All responses are currently returned in GeoJSON format, as Features or FeatureCollections. Below is a template 
    response, with annotations (not valid json).
    - "protocols" - This is a list of all protocols surveyed at this site; if a particular protocol was not 
    employed, it will not be in the list. If however a protocol was employed but returned no observations, 
    the protocol will be listed with a summary metric (e.g. "biomass_avg" for "beltfish") of 0.
    
    {
        "type": "FeatureCollection",
        "count": 123,
        "next": https://summary-api.datamermaid.org/v1/sites/?page=2,
        "previous": null,
        "features": [%s,
            ...
        ]
    }
    """ % template_response_feature

    retrieve_description = """
    Endpoint for single site-level data summary, specified by site uuid in the path.
    """

    retrieve_response = """
    Single-site response version of /sites/ endpoint; see response documentation of those endpoints for details. 
    Template response:%s
    """ % template_response_feature

    @swagger_auto_schema(operation_description=retrieve_description,
                         operation_summary='Retrieve single site-level summary data',
                         responses={200: retrieve_response})
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=list_description,
                         operation_summary='Query all MERMAID sites via query string parameters',
                         responses={200: list_response},
                         filter_inspectors=[SummarySiteFilterInspector]
                         )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    coords = Schema(type='array',
                    items=Items(type='array',
                                items=Items(type='array',
                                            items=Items(type='number', format='float')))
                    )

    body_param = Schema(
        title='Available POST filters',
        description='JSON object with any combination of parameters accepted by GET method above',
        type='object',
        properties={
            'site_id': Schema(type='string', format='uuid'),
            'site_name': Schema(type='string'),
            'project_id': Schema(type='string', format='uuid'),
            'project_name': Schema(type='string'),
            'country_name': Schema(type='string'),
            'date_min': Schema(type='string', format='date'),
            'date_max': Schema(type='string', format='date'),
            'data_policy_beltfish': Schema(type='string', enum=['private', 'public summary', 'public']),
            'data_policy_benthiclit': Schema(type='string', enum=['private', 'public summary', 'public']),
            'data_policy_benthicpit': Schema(type='string', enum=['private', 'public summary', 'public']),
            'data_policy_habitatcomplexity': Schema(type='string', enum=['private', 'public summary', 'public']),
            'data_policy_bleachingqc': Schema(type='string', enum=['private', 'public summary', 'public']),
            'management_regime_id': Schema(type='string', format='uuid',
                                           description='query for any site associated with a sample unit '
                                                       'associated with this management regime'),
            'management_regime_name': Schema(type='string',
                                             description='query for any site associated with a sample unit '
                                                         'associated with this management regime'),
            'tag_id': Schema(type='string', format='uuid',
                             description='query for any site associated with a project associated with this tag'),
            'tag_name': Schema(type='string',
                               description='query for any site associated with a project associated with this tag'),
            'geometry': Schema(type='object',
                               properties={
                                   'type': Schema(type='string', enum=['Polygon', 'MultiPolygon']),
                                   'coordinates': coords,
                                   'example': Schema(type='string',
                                                     pattern=geometry_example)
                               },
                               description='For details on geojson polygon and multipolygon geometry formatting: '
                                           'https://tools.ietf.org/html/rfc7946#section-3.1.6 and http://geojson.io/'),
            'limit': Schema(type='integer'),
            'page': Schema(type='integer'),
        },
    )

    # Not actually 'create': POST view handles large queries and returns list()
    @swagger_auto_schema(operation_description=list_description,
                         operation_summary='Query all MERMAID sites via POST payload',
                         operation_id='sites_post_list',
                         request_body=body_param,
                         responses={200: list_response})
    def create(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        filter_params = request.data
        serializer = self.get_serializer(data=filter_params)
        serializer.is_valid(raise_exception=True)
        if filter_params:
            queryfilter = self.filterset_class(filter_params, queryset=queryset)
            queryset = queryfilter.qs
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SummaryAPIGenerator(OpenAPISchemaGenerator):

    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request=None, public=False)
        schema.definitions = {}
        return schema


schema_view = get_schema_view(
    Info(
        title="MERMAID Summary API",
        default_version='v1',
        description="""
This summary API provides public endpoints that provide access to MERMAID (https://datamermaid.org) data 
aggregated to different levels, for rapid consumption by third-party applications. For access to granular data 
restricted by authenticated user account, use the contact email below for more information about 
https://api.datamermaid.org.

All MERMAID projects elect a data sharing policy for each sample unit type (currently: belt fish transect, 
benthic LIT transect, benthic PIT transect, habitat complexity transect), currently one of: 
- "private": Summary information, including location and date, are available, but aggregated results and 
observations are not
- "public summary" (*default*): Like private, but with aggregated results
- "public": full observation-level data are available
So far this summary API provides only endpoints offering "private" and "public summary" data aggregated at 
the site level, but other levels and policies will be supported in the future. 

All api requests are throttled at the rate of 10000/second overall.
        """,
        terms_of_service="https://datamermaid.org/terms-of-service/",
        contact=Contact(email="contact@datamermaid.org"),
        license=License(name="BSD License", url="https://datamermaid.org/terms-of-service/"),
    ),
    # url='https://summary-api.datamermaid.org',
    public=True,
    generator_class=SummaryAPIGenerator
)
