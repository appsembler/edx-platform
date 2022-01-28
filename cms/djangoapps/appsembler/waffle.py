"""
Tahoe: Waffle flags for Studio.
"""

from openedx.core.djangoapps.waffle_utils import WaffleSwitch, WaffleSwitchNamespace

WAFFLE_SWITCH_NAMESPACE = WaffleSwitchNamespace(name='tahoe_studio', log_prefix=u'Tahoe Studio: ')

GLOBAL_STAFF_HIDE_INACTIVE_SITES_COURSES = WaffleSwitch(
    waffle_namespace=WAFFLE_SWITCH_NAMESPACE,
    switch_name='global_staff_hide_inactive_sites_courses',
)
