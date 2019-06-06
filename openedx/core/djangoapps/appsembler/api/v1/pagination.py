"""Paginatiors for Figures

"""

from rest_framework.pagination import LimitOffsetPagination


class TahoeLimitOffsetPagination(LimitOffsetPagination):
    '''Custom Tahoe paginator to make the number of records returned consistent
    '''
    default_limit = 20
