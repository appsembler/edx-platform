"""
These utils are stolen from https://github.com/appsembler/gestore with the intention to contribute them back there
after making them more generic and stablized.
"""


import beeline


from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db import transaction
import tahoe_sites.api
from django.apps import apps
from opaque_keys.edx.django.models import CourseKeyField

from organizations.models import OrganizationCourse


from common.djangoapps.util.organizations_helpers import get_organization_courses
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

from typing import Any, List, Optional, Tuple, Union

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import (
    ForeignKey,
    ManyToManyField,
    ManyToManyRel,
    ManyToOneRel,
    Model,
    OneToOneField,
)


def has_conflict(model: Model, object_id: Any) -> bool:
    return model.objects.filter(id=object_id).exists()


def get_str_from_model(model: Model, object_id=None) -> str:
    model_path = '.'.join([model._meta.app_label, model.__name__])

    if object_id:
        model_path += '.%s' % object_id

    return model_path


def get_model_name(instance):
    return instance._meta.model.__name__


def instance_representation(instance):
    return get_str_from_model(instance._meta.model, object_id=instance.pk)


### openedx_utis.py

def get_models_using_course_key():
    course_key_field_names = {
        'course_key',
        'course_id',
    }

    models_with_course_key = {
        (CourseOverview, 'id'),  # The CourseKeyField with a `id` name. Hard-coding it for simplicity.
        (OrganizationCourse, 'course_id'),  # course_id is CharField
    }

    model_classes = apps.get_models()
    for model_class in model_classes:
        for field_name in course_key_field_names:
            field_object = getattr(model_class, field_name, None)
            if field_object:
                field_definition = getattr(field_object, 'field', None)
                if field_definition and isinstance(field_definition, CourseKeyField):
                    models_with_course_key.add(
                        (model_class, field_name,)
                    )

    return models_with_course_key


def get_organization_courses_related_objects(organization):
    course_keys = []

    for course in get_organization_courses({'id': organization.id}):
        course_keys.append(course['course_id'])

    for model_class, field_name in get_models_using_course_key():
        print('Found related models of', model_class.__name__, 'with field', field_name)
        objects_to_delete = model_class.objects.filter(**{
            '{field_name}__in'.format(field_name=field_name): course_keys,
        })
        yield from objects_to_delete


def get_site_related_objects(site):
    yield site
    organization = tahoe_sites.api.get_organization_by_site(site)
    yield organization
    # yield from tahoe_sites.api.get_users_of_organization(organization, without_inactive_users=False)
    yield from get_organization_courses_related_objects(organization)


def remove_open_edx_site(domain, commit=False) -> None:
    """
    Remove site.
    """
    print('Inspecting project for potential problems...')
    with transaction.atomic():
        site = Site.objects.get(domain=domain)
        starting_objects = get_site_related_objects(site)

        full_list_of_items = generate_objects(*starting_objects)
        check(full_list_of_items)

        print('Number of objects: ', len(full_list_of_items))
        # TODO: print full list of user emails
        # TODO: print full list of domains
        # TODO: print full list of courses

        for item in full_list_of_items:
            item['instance'].delete()

        if not commit:
            transaction.set_rollback(True)


### gestore/processors.py
def process_foreign_key(
        instance: Model,
        field: ForeignKey
) -> Tuple[Any, Model]:
    """
    What we are looking to achieve here is to get the ID of the object this
    instance is pointing at, and to return that instance for later processing.

    Note: This will process both; ForeignKeys and OneToOneKey. As in
    Django a OneToOneKey is sub class of ForeignKey.
    """
    # Gets the ID of the instance pointed at
    value = field.value_from_object(instance)
    return value, getattr(instance, field.name)


def process_one_to_many_relation(
        instance: Model,
        field: ManyToOneRel
) -> List[Model]:
    """
    In OneToManyRelations, it is this model that other objects are
    pointing at.
    We are collecting these models to make sure that this we are not
    missing any data used in some apps, and to protect the organization
    integrity.

    Unlike ForeignKey, we just need to return the instances pointing at
    this object so we can process it later.
    """
    manager = getattr(instance, field.get_accessor_name())
    to_process = [obj for obj in manager.all()] if manager else []

    return to_process


def process_one_to_one_relation(
        instance: Model,
        field: OneToOneField
) -> Optional[List[Model]]:
    """
    This is a little bit similar to the OneToManyRel, except that we
    attribute returns one instance when called instead of a Model Manager.
    """
    try:
        return [getattr(instance, field.name)]
    except ObjectDoesNotExist:
        # Nothing to do, we didn't find any object related to this
        # in the other model.
        return []


def process_many_to_many_relation(
        instance: Model,
        field: Union[ManyToManyRel, ManyToManyField]
) -> Tuple[Any, List[Model]]:
    """
    Extracts all objects this instance is pointing at for later processing.
    Also returns a list of these objects IDs to be used as a value under
    the field name.
    """
    data = []
    to_process = []

    if isinstance(field, ManyToManyRel):
        # This is a ManyToMany Field in another model
        manager = getattr(instance, field.get_accessor_name())
        return None, [x for x in manager.all()]

    for relation in field.value_from_object(instance):
        data.append(relation.id)
        to_process.append(relation)

    return data, to_process



### gestore/graph_utils.py
def generate_objects(*args: [Model], root_models=None) -> list:
    """
    A Depth First Search implementation to extract the given objects and
    process their children.
    What we are looking to achieve here is simply: For each object; process
    it; and all objects related to it. This will give you all the data
    that object uses in order to operate properly when imported.

    When processing an object, some discovered relations will be added
    to the stack to take part in the processing later. Same goes for any
    discovered relation in that queue.

    The relations that are not going to be processed are objects of what
    we call Root Models. A root model is identified using two ways:
        - Any object in the same model of the object you're trying to
          export. For example; if you're exporting a user object from
          model User, we are not going to process any other user in that
          model except the given one.
        - A set of models the user manually provides.

    To avoid infinite loops caused by processing the same element multiple
    times, we check the discovered space (processing and processed objects)
    before adding new elements.

    :return: Simply all discovered objects' data.
    """
    objects = []
    visited = {}

    processing_stack = list(args)

    print('Starting items:', len(processing_stack))
    for debugging_item in processing_stack:
        print('Starter item:', debugging_item, type(debugging_item))
    print('=====')

    in_processing_stack = {
        instance_representation(instance): True
        for instance in args
    }

    if not root_models:
        root_models = set()

    root_models = set(get_model_name(i) for i in args).union(root_models)

    while processing_stack:
        instance = processing_stack.pop()
        instance_key = instance_representation(instance)

        in_processing_stack[instance_key] = False
        item, data, pending_items = process_instance(instance)

        if item:
            objects.append({
                'instance': item,
                'data': data,
            })

        for pending_item in pending_items:
            pending_item_key = instance_representation(pending_item)

            is_root_object = get_model_name(pending_item) in root_models
            is_processed = visited.get(pending_item_key, False)
            is_processing = in_processing_stack.get(
                pending_item_key, False
            )

            # Equivalent to not is_processed and not is_...
            should_process = not (
                    is_processed or is_processing or is_root_object
            )
            if should_process:
                processing_stack.append(pending_item)
                in_processing_stack[pending_item_key] = True

        visited[instance_key] = True

    print('Total exported objects is %d (%d processed)' % (len(objects), len(visited)))

    return objects


def assert_all(*items, msg, obj, field):
    for item in items:
        assert isinstance(item, Model)
    assert all(items), 'All values should be actual instances (%s) %s --> %s ... %s' % (msg, obj, field, items)


def process_instance(instance: Model):
    """
    Inspired from: django.forms.models.model_to_dict
    Return a dict containing the data in ``instance`` suitable for passing
    as a Model's ``create`` keyword argument with all its discovered
    relations.
    """
    assert instance, 'Should not get empty instance'

    to_process = set()
    content_type = ContentType.objects.get_for_model(instance)
    opts = instance._meta  # pylint: disable=W0212 # noqa

    data = {
        'model': '%s.%s' % (content_type.app_label, content_type.model),
        'fields': {},
    }

    # We are going to iterate over the fields one by one, and depending
    # on the type, we determine how to process them.
    for field in opts.get_fields():
        if isinstance(field, ForeignKey):
            value, item = process_foreign_key(
                instance, field
            )
            data['fields'][field.name] = value
            if item:
                assert_all(item, msg='fk', obj=instance, field=field)
                to_process.add(item)
        elif field.one_to_many:
            items = process_one_to_many_relation(
                instance,
                field
            )
            assert_all(*items, msg='1toM', obj=instance, field=field)
            to_process.update(items)
        elif field.one_to_one:
            items = process_one_to_one_relation(
                instance,
                field
            )
            assert_all(*items, msg='1to1', obj=instance, field=field)
            to_process.update(items)
        elif field.many_to_many:
            value, items = process_many_to_many_relation(
                instance,
                field
            )

            if value is not None:
                data['fields'][field.name] = value

            assert_all(*items, msg='m2m', obj=instance, field=field)
            to_process.update(items)
        elif field in opts.concrete_fields \
                or field in opts.private_fields:
            # Django stores the primary key under `id`
            if field.name == 'id':
                data['pk'] = field.value_from_object(instance)
            else:
                data['fields'][field.name] = field.value_from_object(
                    instance
                )
        else:
            print('SKIPPED %s' % str(field))

    print('Finished processing %s object' % data['model'])
    print('%d new items to process' % len(to_process))
    assert_all(*to_process, msg='all', obj=instance, field='all')

    return instance, data, to_process


def check(objects):
    check_sites_leak(objects)


def check_sites_leak(objects_list):
    """

    """
    # check count and domain of Site object
    # check count and short_name of Organization object
    # check count of users and their Site == site_to_delete
    # check count of CourseOverview and their Organization == org_to_delete
    # check others??
