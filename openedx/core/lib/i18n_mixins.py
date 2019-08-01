import six


class TranslatableXBlockMixin(object):
    def __init__(self, runtime, *args, **kwargs):
        from xblock.fields import UNSET, UNIQUE_ID, Field
        from django.utils.translation import ugettext
        _self = self

        def trans(s):
            if s == "Are you enjoying the course?":
                raise Exception(s)

            if s is not None and isinstance(s, basestring) and s is not UNSET and s is not UNIQUE_ID:
                return ugettext(s)
                return _self.ugettext(s)
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

        # for field_name in getattr(self, 'editable_fields', []):
        #     field = self.fields[field_name]
        for field in self.fields:
            # apply(field, '_display_name', trans)
            # apply(field, '_default', trans_struct)
            # apply(field, 'help', trans)
            # apply(field, '_values', trans_struct)

            field._display_name = trans(field._display_name)
            field._default = trans_struct(field._default)
            field.help = trans(field.help)
            field._values = trans_struct(field._values)

    @property
    def name(self):
        """Returns the name of this field."""
        # This is set by ModelMetaclass
        from django.utils.translation import ugettext
        return ugettext(self.__name__) or 'unknown'
