import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.postgres.fields import JSONField


class SummarySiteView(models.Model):
    OPEN = 90
    TEST = 80
    LOCKED = 10
    PROJECT_STATUSES = (
        (OPEN, _(u'open')),
        (TEST, _(u'test')),
        (LOCKED, _(u'locked')),
    )

    site_id = models.UUIDField(primary_key=True)
    site_name = models.CharField(max_length=255)
    lat = models.DecimalField(max_digits=16, decimal_places=14)
    lon = models.DecimalField(max_digits=17, decimal_places=14)
    site_notes = models.TextField(blank=True)
    project_id = models.UUIDField()
    project_status = models.PositiveSmallIntegerField(choices=PROJECT_STATUSES, default=OPEN)
    project_name = models.CharField(max_length=255)
    project_notes = models.TextField(blank=True)
    data_policy_beltfish = models.CharField(max_length=50)
    data_policy_benthiclit = models.CharField(max_length=50)
    data_policy_benthicpit = models.CharField(max_length=50)
    data_policy_habitatcomplexity = models.CharField(max_length=50)
    data_policy_bleachingqc = models.CharField(max_length=50)
    contact_link = models.CharField(max_length=255)
    country_id = models.UUIDField()
    country_name = models.CharField(max_length=50)
    reef_type = models.CharField(max_length=50)
    reef_zone = models.CharField(max_length=50)
    exposure = models.CharField(max_length=50)
    tags = JSONField(null=True, blank=True)
    project_admins = JSONField(null=True, blank=True)
    date_min = models.DateField(null=True, blank=True)
    date_max = models.DateField(null=True, blank=True)
    depth = JSONField(null=True, blank=True)
    management_regimes = JSONField(null=True, blank=True)
    protocols = JSONField(null=True, blank=True)

    class Meta:
        db_table = 'vw_summary_site'
        managed = False
