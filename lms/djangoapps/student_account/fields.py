"""
Example AccountSettingsExtensionField subclass:
the below wouldn't be defined here, but in some other module
or add on app


class ExampleExtensionField(AccountSettingsExtensionField):

    field_id = 'example_field'
    js_model = 'js/student_account/models/user_account_model'
    js_field_view_class = 'FieldViews.DropdownFieldView'
    api_url = None
    title = 'Example Test Field'
    helpMessage = 'Helpful help message'
    valueAttribute = 'example_field'
    options= [(1, 'One'), (2, 'Two'), ]
    persistChanges = True

    def __init__(self, request):
        self.api_url = reverse("accounts_api", kwargs={'username': request.user.username})

    def __call__(self):
        return {
            'id': self.field_id,
            'js_model': self.js_model,
            'js_field_view_class': self.js_field_view_class,
            'api_url': self.api_url,
            'title': self.title,
            'helpMessage': self.helpMessage,
            'valueAttribute': self.valueAttribute,
            'options': self.options,
            'persistChanges': self.persistChanges
        }
"""

from abc import ABCMeta, abstractproperty, abstractmethod


class AccountSettingsExtensionField(object):
    """
    Abstract Base Class for Account Settings extension fields.
    Extension field classes must subclass this class and implement
    the properties defined here.
    """

    __metaclass__ = ABCMeta

    @abstractproperty
    def field_id(self):
        """
        set the field id
        """
        raise NotImplementedError

    @abstractproperty
    def js_model(self):
        """
        set the Backbone model associated with the Django model
        for this field
        """
        raise NotImplementedError

    @abstractproperty
    def js_field_view_class(self):
        """
        set the field class for use in the Backbone application
        """
        raise NotImplementedError

    @abstractproperty
    def api_url(self):
        """
        set the API url used to get/set values to/from the Django model
        for this field
        """
        raise NotImplementedError

    @abstractmethod
    def __call__(self):
        """
        an AccountSettingsExtensionField instance should return a
        dictionary-like object with at least the required
        abstract properties when called
        """
        raise NotImplementedError
