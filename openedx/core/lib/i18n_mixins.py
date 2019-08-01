import six
from xblock.core import XBlockMixin


class TranslatableXBlockMixin(XBlockMixin):

    def __init__(self, runtime, *args, **kwargs):
        from xblock.fields import UNSET, UNIQUE_ID, Field
        from django.utils.translation import ugettext

        def apply(f, prop, func):
            try:
                raw = getattr(f, prop)
                setattr(f, prop, func(raw))
            except AttributeError:
                pass

        def trans(s):
            if s is not None and isinstance(s, basestring) and s is not UNSET and s is not UNIQUE_ID:
                return ugettext(s)
            return s

        def trans_struct(s):
            if isinstance(s, tuple):
                return tuple(trans_struct(i) for i in s)
            if isinstance(s, list):
                return [trans_struct(i) for i in s]
            elif isinstance(s, dict):
                return {k: trans_struct(v) for k, v in six.iteritems(s)}
            else:
                return trans(s)

        super(TranslatableXBlockMixin, self).__init__(runtime, *args, **kwargs)

        if hasattr(self, 'editable_fields'):
            # for field_name in getattr(self, 'editable_fields', []):
            #     field = self.fields[field_name]
            for _field_name, field in self.fields.iteritems():
                # apply(field, '_display_name', trans)
                # apply(field, '_default', trans_struct)
                # apply(field, 'help', trans)
                # apply(field, '_values', trans_struct)
                try:
                    field._display_name = trans(field._display_name)
                except AttributeError as e:
                    print field, e
                    pass

                try:
                    field._default = trans_struct(field._default)
                except AttributeError as e:
                    print field, e
                    pass

                try:
                    field._values = trans_struct(field._values)
                except AttributeError as e:
                    print field, e
                    pass

                try:
                    field.help = trans(field.help)
                except AttributeError as e:
                    print field, e
                    pass
                # field._display_name = trans(field._display_name)
                # # field._default = trans_struct(field._default)
                # # field._default = trans(field._default)
                # # field.help = trans(field.help)
                # # field._values = trans_struct(field._values)
