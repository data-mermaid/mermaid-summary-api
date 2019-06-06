# Generated by Django 2.1.3 on 2019-03-29 18:53

from django.db import migrations


forward_sql = """
DROP MATERIALIZED VIEW IF EXISTS vw_summary_site;

CREATE MATERIALIZED VIEW IF NOT EXISTS vw_summary_site AS 

SELECT site.id AS site_id, site.name AS site_name, 
ST_Y(site.location) AS lat, ST_X(site.location) AS lon,
site.notes AS site_notes,
project.id AS project_id, project.name AS project_name, 
project.status AS project_status,
project.notes AS project_notes,

(CASE WHEN project.data_policy_beltfish=10 THEN 'private'
    WHEN project.data_policy_beltfish=50 THEN 'public summary'
    WHEN project.data_policy_beltfish=100 THEN 'public'
    ELSE ''
END) AS data_policy_beltfish, 
(CASE WHEN project.data_policy_benthiclit=10 THEN 'private'
    WHEN project.data_policy_benthiclit=50 THEN 'public summary'
    WHEN project.data_policy_benthiclit=100 THEN 'public'
    ELSE ''
END) AS data_policy_benthiclit, 
(CASE WHEN project.data_policy_benthicpit=10 THEN 'private'
    WHEN project.data_policy_benthicpit=50 THEN 'public summary'
    WHEN project.data_policy_benthicpit=100 THEN 'public'
    ELSE ''
END) AS data_policy_benthicpit, 
(CASE WHEN project.data_policy_habitatcomplexity=10 THEN 'private'
    WHEN project.data_policy_habitatcomplexity=50 THEN 'public summary'
    WHEN project.data_policy_habitatcomplexity=100 THEN 'public'
    ELSE ''
END) AS data_policy_habitatcomplexity, 

'https://api.datamermaid.org/contact_project?project_id=' || COALESCE(project.id::text, '') AS contact_link,
country.name AS country_name,
tags.tags,
pa.project_admins,
api_reeftype.name AS reef_type,
api_reefzone.name AS reef_zone,
api_reefexposure.name AS exposure,
sample_events.date_min,
sample_events.date_max,
sample_events.depth,
mrs.management_regimes,
jsonb_strip_nulls(jsonb_build_object(
    'beltfish', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', fb.sample_unit_count,
        'biomass_avg', (CASE WHEN project.data_policy_beltfish < 50 THEN NULL ELSE fb.biomass_avg END)
    )), '{}'),
    'benthiclit', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', bl.sample_unit_count,
        'coral_cover', (CASE WHEN project.data_policy_benthiclit < 50 THEN NULL ELSE bl.percent_avgs END)
    )), '{}'),
    'benthicpit', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', bp.sample_unit_count,
        'coral_cover', (CASE WHEN project.data_policy_benthicpit < 50 THEN NULL ELSE bp.percent_avgs END)
    )), '{}'),
    'habitatcomplexity', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', hc.sample_unit_count,
        'score_avg', (CASE WHEN project.data_policy_habitatcomplexity < 50 THEN NULL ELSE hc.score_avg END)
    )), '{}')
)) AS protocols

FROM site
INNER JOIN project ON (site.project_id = project.id)
INNER JOIN country ON (site.country_id = country.id)
INNER JOIN api_reeftype ON (site.reef_type_id = api_reeftype.id)
INNER JOIN api_reefzone ON (site.reef_zone_id = api_reefzone.id)
INNER JOIN api_reefexposure ON (site.exposure_id = api_reefexposure.id)

INNER JOIN (
    SELECT project.id, 
    jsonb_agg(
        jsonb_build_object('name', COALESCE(profile.first_name, '') || ' ' || COALESCE(profile.last_name, ''))
    ) AS project_admins
    FROM project
    INNER JOIN project_profile ON (project.id = project_profile.project_id)
    INNER JOIN profile ON (project_profile.profile_id = profile.id)
    WHERE project_profile.role >= 90
    GROUP BY project.id
) pa ON (project.id = pa.id)

LEFT JOIN (
    SELECT project.id, 
    jsonb_agg(
        jsonb_build_object('id', t.id, 'name', t.name)
    ) AS tags
    FROM api_uuidtaggeditem ti
    INNER JOIN django_content_type ct ON (ti.content_type_id = ct.id)
    INNER JOIN project ON (ti.object_id = project.id)
    INNER JOIN api_tag t ON (ti.tag_id = t.id)
    WHERE ct.app_label = 'api' AND ct.model = 'project'
    GROUP BY project.id
) tags ON (project.id = tags.id)

LEFT JOIN (
    SELECT site_id, 
    jsonb_build_object(
        'min', MIN(depth),
        'max', MAX(depth)
    ) AS depth,
    MIN(sample_date) AS date_min,
    MAX(sample_date) AS date_max
    FROM sample_event
    GROUP BY site_id
) sample_events ON (site.id = sample_events.site_id)

LEFT JOIN (
    SELECT site_id, 
    jsonb_agg(DISTINCT jsonb_build_object(
        'id', management_id,
        'name', CASE WHEN m.name_secondary = '' THEN m.name ELSE m.name || ' [' || m.name_secondary || ']' END
    )) AS management_regimes
    FROM sample_event s
    INNER JOIN management m ON (s.management_id = m.id)
    GROUP BY site_id
) mrs ON (site.id = mrs.site_id)

LEFT JOIN (
    SELECT site_id, 
    COUNT(se.*) as sample_unit_count, 
    CASE WHEN avg(se.biomass_kgha) IS NULL THEN 0 ELSE AVG(se.biomass_kgha) END AS biomass_avg
    FROM (SELECT 
        sample_event.site_id,
        sample_event.management_id,
        sample_event.sample_date,
        transect_belt_fish.number,
        SUM(
            10000 * -- m2 to ha: * here instead of / in denominator to avoid divide by 0 errors
            -- mass (kg)
            (o.count * f.biomass_constant_a * ((o.size * f.biomass_constant_c) ^ f.biomass_constant_b) / 1000)
            / (transect_belt_fish.len_surveyed * w.val) -- area (m2)
        ) AS biomass_kgha
        FROM obs_transectbeltfish o
        JOIN vw_fish_attributes f ON o.fish_attribute_id = f.id
        INNER JOIN transectmethod_transectbeltfish t ON (o.beltfish_id = t.transectmethod_ptr_id)
        INNER JOIN transect_belt_fish ON (t.transect_id = transect_belt_fish.id)
        INNER JOIN sample_event ON transect_belt_fish.sample_event_id = sample_event.id
        INNER JOIN api_belttransectwidth w ON (transect_belt_fish.width_id = w.id)
        -- field definition of sample event
        GROUP BY sample_event.site_id, sample_event.management_id, sample_event.sample_date, transect_belt_fish.number
    ) se
    GROUP BY se.site_id
) fb ON (site.id = fb.site_id)

LEFT JOIN (
    SELECT su_count.site_id, 
    sample_unit_count, 
    percent_avgs
    FROM (
        SELECT site_id, COUNT(*) AS sample_unit_count
        FROM (
            SELECT site_id
            FROM sample_event
            INNER JOIN transect_benthic ON (sample_event.id = transect_benthic.sample_event_id)
            INNER JOIN transectmethod_benthiclit t ON (transect_benthic.id = t.transect_id)
            GROUP BY sample_event.site_id, sample_event.management_id, sample_event.sample_date, number
        ) AS sc GROUP BY site_id
    ) AS su_count
    INNER JOIN (
        SELECT site_id, 
        json_agg(json_build_object(name, avg)) AS percent_avgs 
        FROM (
            SELECT site_id, name, 
            AVG(cat_percent) as avg
            FROM (
                WITH cps AS (
                    SELECT 
                    sample_event.site_id,
                    sample_event.management_id,
                    sample_event.sample_date,
                    transect_benthic.number,
                    c.id AS cat_id, 
                    c.name, 
                    SUM(o.length) AS category_length
                    FROM obs_benthiclit o
                    INNER JOIN (
                        WITH RECURSIVE tree(child, root) AS (
                            SELECT c.id, c.id
                            FROM benthic_attribute c
                            LEFT JOIN benthic_attribute p ON (c.parent_id = p.id)
                            WHERE p.id IS NULL
                            UNION
                            SELECT id, root
                            FROM tree
                            INNER JOIN benthic_attribute ON (tree.child = benthic_attribute.parent_id)
                        )
                        SELECT * FROM tree
                    ) category ON (o.attribute_id = category.child)
                    INNER JOIN benthic_attribute c ON (category.root = c.id)
                    INNER JOIN transectmethod_benthiclit t ON (o.benthiclit_id = t.transectmethod_ptr_id)
                    INNER JOIN transect_benthic ON (t.transect_id = transect_benthic.id)
                    INNER JOIN sample_event ON (transect_benthic.sample_event_id = sample_event.id)
                    -- field definition of sample event
                    GROUP BY sample_event.site_id, sample_event.management_id, sample_event.sample_date, 
                    transect_benthic.number, c.id
                )
                SELECT cps.site_id, cps.management_id, cps.sample_date, cps.number, cps.name,
                cps.category_length / cat_totals.su_length AS cat_percent
                FROM cps
                INNER JOIN (
                    SELECT site_id, management_id, sample_date, number, SUM(category_length) AS su_length
                    FROM cps
                    GROUP BY site_id, management_id, sample_date, number
                ) cat_totals ON (cps.site_id = cat_totals.site_id AND 
                                cps.management_id = cat_totals.management_id AND 
                                cps.sample_date = cat_totals.sample_date AND 
                                cps.number = cat_totals.number)
            ) AS cat_percents
            GROUP BY site_id, name
        ) AS site_percents
        GROUP BY site_id
    ) AS site_percents ON (su_count.site_id = site_percents.site_id)
) bl ON (site.id = bl.site_id)

LEFT JOIN (
    SELECT su_count.site_id, 
    sample_unit_count, 
    percent_avgs
    FROM (
        SELECT site_id, COUNT(*) AS sample_unit_count
        FROM (
            SELECT site_id
            FROM sample_event
            INNER JOIN transect_benthic ON (sample_event.id = transect_benthic.sample_event_id)
            INNER JOIN transectmethod_benthicpit t ON (transect_benthic.id = t.transect_id)
            GROUP BY sample_event.site_id, sample_event.management_id, sample_event.sample_date, number
        ) AS sc GROUP BY site_id
    ) AS su_count
    INNER JOIN (
        SELECT site_id, 
        json_agg(json_build_object(name, avg)) AS percent_avgs 
        FROM (
            SELECT site_id, name, 
            AVG(cat_percent) as avg
            FROM (
                WITH cps AS (
                    SELECT 
                    sample_event.site_id,
                    sample_event.management_id,
                    sample_event.sample_date,
                    transect_benthic.number,
                    t.interval_size,
                    c.id AS cat_id, 
                    c.name, 
                    SUM(t.interval_size) AS category_length
                    FROM obs_benthicpit o
                    INNER JOIN (
                        WITH RECURSIVE tree(child, root) AS (
                            SELECT c.id, c.id
                            FROM benthic_attribute c
                            LEFT JOIN benthic_attribute p ON (c.parent_id = p.id)
                            WHERE p.id IS NULL
                            UNION
                            SELECT id, root
                            FROM tree
                            INNER JOIN benthic_attribute ON (tree.child = benthic_attribute.parent_id)
                        )
                        SELECT * FROM tree
                    ) category ON (o.attribute_id = category.child)
                    INNER JOIN benthic_attribute c ON (category.root = c.id)
                    INNER JOIN transectmethod_benthicpit t ON (o.benthicpit_id = t.transectmethod_ptr_id)
                    INNER JOIN transect_benthic ON (t.transect_id = transect_benthic.id)
                    INNER JOIN sample_event ON (transect_benthic.sample_event_id = sample_event.id)
                    -- field definition of sample event
                    GROUP BY sample_event.site_id, sample_event.management_id, sample_event.sample_date, 
                    transect_benthic.number, t.interval_size, c.id
                )
                SELECT cps.site_id, cps.management_id, cps.sample_date, cps.number, cps.name,
                cps.category_length / cat_totals.su_length AS cat_percent
                FROM cps
                INNER JOIN (
                    SELECT site_id, management_id, sample_date, number, SUM(category_length) AS su_length
                    FROM cps
                    GROUP BY site_id, management_id, sample_date, number
                ) cat_totals ON (cps.site_id = cat_totals.site_id AND 
                                cps.management_id = cat_totals.management_id AND 
                                cps.sample_date = cat_totals.sample_date AND 
                                cps.number = cat_totals.number)
            ) AS cat_percents
            GROUP BY site_id, name
        ) AS site_percents
        GROUP BY site_id
    ) AS site_percents ON (su_count.site_id = site_percents.site_id)
) bp ON (site.id = bp.site_id)

LEFT JOIN (
    SELECT site_id, 
    COUNT(se.*) as sample_unit_count, 
    AVG(se.score_avg) AS score_avg
    FROM (SELECT 
        sample_event.site_id,
        sample_event.management_id,
        sample_event.sample_date,
        transect_benthic.number,
        AVG(s.val) AS score_avg
        FROM obs_habitatcomplexity o
        INNER JOIN api_habitatcomplexityscore s ON (o.score_id = s.id)
        INNER JOIN transectmethod_habitatcomplexity t ON (o.habitatcomplexity_id = t.transectmethod_ptr_id)
        INNER JOIN transect_benthic ON (t.transect_id = transect_benthic.id)
        INNER JOIN sample_event ON transect_benthic.sample_event_id = sample_event.id
        GROUP BY sample_event.site_id, sample_event.management_id, sample_event.sample_date, transect_benthic.number
    ) se
    GROUP BY se.site_id
) hc ON (site.id = hc.site_id);

CREATE UNIQUE INDEX ON vw_summary_site (site_id);
"""

reverse_sql = """
DROP MATERIALIZED VIEW IF EXISTS vw_summary_site;

CREATE MATERIALIZED VIEW IF NOT EXISTS vw_summary_site AS 

SELECT site.id AS site_id, site.name AS site_name, 
ST_Y(site.location) AS lat, ST_X(site.location) AS lon,
site.notes AS site_notes,
project.id AS project_id, project.name AS project_name, 
project.notes AS project_notes,

(CASE WHEN project.data_policy_beltfish=10 THEN 'private'
    WHEN project.data_policy_beltfish=50 THEN 'public summary'
    WHEN project.data_policy_beltfish=100 THEN 'public'
    ELSE ''
END) AS data_policy_beltfish, 
(CASE WHEN project.data_policy_benthiclit=10 THEN 'private'
    WHEN project.data_policy_benthiclit=50 THEN 'public summary'
    WHEN project.data_policy_benthiclit=100 THEN 'public'
    ELSE ''
END) AS data_policy_benthiclit, 
(CASE WHEN project.data_policy_benthicpit=10 THEN 'private'
    WHEN project.data_policy_benthicpit=50 THEN 'public summary'
    WHEN project.data_policy_benthicpit=100 THEN 'public'
    ELSE ''
END) AS data_policy_benthicpit, 
(CASE WHEN project.data_policy_habitatcomplexity=10 THEN 'private'
    WHEN project.data_policy_habitatcomplexity=50 THEN 'public summary'
    WHEN project.data_policy_habitatcomplexity=100 THEN 'public'
    ELSE ''
END) AS data_policy_habitatcomplexity, 

'https://api.datamermaid.org/contact_project?project_id=' || COALESCE(project.id::text, '') AS contact_link,
country.name AS country_name,
tags.tags,
pa.project_admins,
api_reeftype.name AS reef_type,
api_reefzone.name AS reef_zone,
api_reefexposure.name AS exposure,
sample_events.date_min,
sample_events.date_max,
sample_events.depth,
mrs.management_regimes,
jsonb_strip_nulls(jsonb_build_object(
    'beltfish', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', fb.sample_unit_count,
        'biomass_avg', (CASE WHEN project.data_policy_beltfish < 50 THEN NULL ELSE fb.biomass_avg END)
    )), '{}'),
    'benthiclit', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', bl.sample_unit_count,
        'coral_cover', (CASE WHEN project.data_policy_benthiclit < 50 THEN NULL ELSE bl.percent_avgs END)
    )), '{}'),
    'benthicpit', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', bp.sample_unit_count,
        'coral_cover', (CASE WHEN project.data_policy_benthicpit < 50 THEN NULL ELSE bp.percent_avgs END)
    )), '{}'),
    'habitatcomplexity', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', hc.sample_unit_count,
        'score_avg', (CASE WHEN project.data_policy_habitatcomplexity < 50 THEN NULL ELSE hc.score_avg END)
    )), '{}')
)) AS protocols

FROM site
INNER JOIN project ON (site.project_id = project.id)
INNER JOIN country ON (site.country_id = country.id)
INNER JOIN api_reeftype ON (site.reef_type_id = api_reeftype.id)
INNER JOIN api_reefzone ON (site.reef_zone_id = api_reefzone.id)
INNER JOIN api_reefexposure ON (site.exposure_id = api_reefexposure.id)

INNER JOIN (
    SELECT project.id, 
    jsonb_agg(
        jsonb_build_object('name', COALESCE(profile.first_name, '') || ' ' || COALESCE(profile.last_name, ''))
    ) AS project_admins
    FROM project
    INNER JOIN project_profile ON (project.id = project_profile.project_id)
    INNER JOIN profile ON (project_profile.profile_id = profile.id)
    WHERE project_profile.role >= 90
    GROUP BY project.id
) pa ON (project.id = pa.id)

LEFT JOIN (
    SELECT project.id, 
    jsonb_agg(
        jsonb_build_object('id', t.id, 'name', t.name)
    ) AS tags
    FROM api_uuidtaggeditem ti
    INNER JOIN django_content_type ct ON (ti.content_type_id = ct.id)
    INNER JOIN project ON (ti.object_id = project.id)
    INNER JOIN api_tag t ON (ti.tag_id = t.id)
    WHERE ct.app_label = 'api' AND ct.model = 'project'
    GROUP BY project.id
) tags ON (project.id = tags.id)

LEFT JOIN (
    SELECT site_id, 
    jsonb_build_object(
        'min', MIN(depth),
        'max', MAX(depth)
    ) AS depth,
    MIN(sample_date) AS date_min,
    MAX(sample_date) AS date_max
    FROM sample_event
    GROUP BY site_id
) sample_events ON (site.id = sample_events.site_id)

LEFT JOIN (
    SELECT site_id, 
    jsonb_agg(DISTINCT jsonb_build_object(
        'id', management_id,
        'name', CASE WHEN m.name_secondary = '' THEN m.name ELSE m.name || ' [' || m.name_secondary || ']' END
    )) AS management_regimes
    FROM sample_event s
    INNER JOIN management m ON (s.management_id = m.id)
    GROUP BY site_id
) mrs ON (site.id = mrs.site_id)

LEFT JOIN (
    SELECT site_id, 
    COUNT(sample_event) AS sample_unit_count,
    CASE WHEN AVG(obs.biomass_kgha) IS NULL THEN 0 ELSE AVG(obs.biomass_kgha) END AS biomass_avg
    FROM sample_event
    INNER JOIN transect_belt_fish ON (sample_event.id = transect_belt_fish.sample_event_id)
    INNER JOIN transectmethod_transectbeltfish t ON (transect_belt_fish.id = t.transect_id)
    LEFT JOIN (
        SELECT beltfish_id,
        SUM(
            10000 * -- m2 to ha: * here instead of / in denominator to avoid divide by 0 errors
            -- mass (kg)
            (o.count * f.biomass_constant_a * ((o.size * f.biomass_constant_c) ^ f.biomass_constant_b) / 1000)
            / (transect_belt_fish.len_surveyed * w.val) -- area (m2)
        ) AS biomass_kgha
        FROM obs_transectbeltfish o 
        INNER JOIN vw_fish_attributes f ON (o.fish_attribute_id = f.id)
        INNER JOIN transectmethod_transectbeltfish t ON (o.beltfish_id = t.transectmethod_ptr_id)
        INNER JOIN transect_belt_fish ON (t.transect_id = transect_belt_fish.id)
        INNER JOIN api_belttransectwidth w ON (transect_belt_fish.width_id = w.id)
        GROUP BY o.beltfish_id
    ) obs ON (t.transectmethod_ptr_id = obs.beltfish_id)
    GROUP BY site_id
) fb ON (site.id = fb.site_id)

LEFT JOIN (
    SELECT su_count.site_id, 
    sample_unit_count, 
    percent_avgs
    FROM (
        SELECT site_id, COUNT(sample_event) AS sample_unit_count
        FROM sample_event
        INNER JOIN transect_benthic ON (sample_event.id = transect_benthic.sample_event_id)
        INNER JOIN transectmethod_benthiclit t ON (transect_benthic.id = t.transect_id)
        GROUP BY sample_event.site_id
    ) AS su_count
    INNER JOIN (
        SELECT site_id, json_agg(json_build_object(name, avg)) AS percent_avgs FROM (
            SELECT site_id, name, AVG(cat_percent) / 100 as avg
            FROM (
                SELECT sample_event.site_id, benthiclit_id, c.id, c.name, SUM(o.length) / 
                transect_benthic.len_surveyed AS cat_percent
                FROM obs_benthiclit o
                INNER JOIN (
                    WITH RECURSIVE tree(child, root) AS (
                        SELECT c.id, c.id
                        FROM benthic_attribute c
                        LEFT JOIN benthic_attribute p ON (c.parent_id = p.id)
                        WHERE p.id IS NULL
                        UNION
                        SELECT id, root
                        FROM tree
                        INNER JOIN benthic_attribute ON (tree.child = benthic_attribute.parent_id)
                    )
                    SELECT * FROM tree
                ) category ON (o.attribute_id = category.child)
                INNER JOIN benthic_attribute c ON (category.root = c.id)
                INNER JOIN transectmethod_benthiclit t ON (o.benthiclit_id = t.transectmethod_ptr_id)
                INNER JOIN transect_benthic ON (t.transect_id = transect_benthic.id)
                INNER JOIN sample_event ON (transect_benthic.sample_event_id = sample_event.id)
                GROUP BY sample_event.site_id, o.benthiclit_id, transect_benthic.id, c.id
            ) AS cps
            GROUP BY site_id, name
        ) AS cat_percents
        GROUP BY site_id
    ) AS site_percents ON (su_count.site_id = site_percents.site_id)
) bl ON (site.id = bl.site_id)

LEFT JOIN (
    SELECT su_count.site_id, 
    sample_unit_count, 
    percent_avgs
    FROM (
        SELECT site_id, COUNT(sample_event) AS sample_unit_count
        FROM sample_event
        INNER JOIN transect_benthic ON (sample_event.id = transect_benthic.sample_event_id)
        INNER JOIN transectmethod_benthicpit t ON (transect_benthic.id = t.transect_id)
        GROUP BY sample_event.site_id
    ) AS su_count
    INNER JOIN (
        SELECT site_id, json_agg(json_build_object(name, avg)) AS percent_avgs FROM (
            SELECT site_id, name, AVG(cat_percent)
            FROM (
                SELECT sample_event.site_id, benthicpit_id, c.id, c.name, 
                SUM(1) / (transect_benthic.len_surveyed / t.interval_size) AS cat_percent
                FROM obs_benthicpit o
                INNER JOIN (
                    WITH RECURSIVE tree(child, root) AS (
                        SELECT c.id, c.id
                        FROM benthic_attribute c
                        LEFT JOIN benthic_attribute p ON (c.parent_id = p.id)
                        WHERE p.id IS NULL
                        UNION
                        SELECT id, root
                        FROM tree
                        INNER JOIN benthic_attribute ON (tree.child = benthic_attribute.parent_id)
                    )
                    SELECT * FROM tree
                ) category ON (o.attribute_id = category.child)
                INNER JOIN benthic_attribute c ON (category.root = c.id)
                INNER JOIN transectmethod_benthicpit t ON (o.benthicpit_id = t.transectmethod_ptr_id)
                INNER JOIN transect_benthic ON (t.transect_id = transect_benthic.id)
                INNER JOIN sample_event ON (transect_benthic.sample_event_id = sample_event.id)
                GROUP BY sample_event.site_id, o.benthicpit_id, transect_benthic.id, t.interval_size, c.id
            ) AS cps
            GROUP BY site_id, name
        ) AS cat_percents
        GROUP BY site_id
    ) AS site_percents ON (su_count.site_id = site_percents.site_id)
) bp ON (site.id = bp.site_id)

LEFT JOIN (
    SELECT site_id, 
    COUNT(sample_event) AS sample_unit_count,
    AVG(obs.score_avg) AS score_avg
    FROM sample_event
    INNER JOIN transect_benthic ON (sample_event.id = transect_benthic.sample_event_id)
    INNER JOIN transectmethod_habitatcomplexity t ON (transect_benthic.id = t.transect_id)
    INNER JOIN (
        SELECT habitatcomplexity_id,
        AVG(s.val) AS score_avg
        FROM obs_habitatcomplexity o
        INNER JOIN api_habitatcomplexityscore s ON (o.score_id = s.id)
        GROUP BY o.habitatcomplexity_id
    ) obs ON (t.transectmethod_ptr_id = obs.habitatcomplexity_id)
    GROUP BY site_id
) hc ON (site.id = hc.site_id);

CREATE UNIQUE INDEX ON vw_summary_site (site_id);
"""


class Migration(migrations.Migration):

    dependencies = [
        ('summary_api', '0003_auto_20190319_2109'),
    ]

    operations = [
        migrations.RunSQL(forward_sql, reverse_sql),
    ]
