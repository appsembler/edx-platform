from analytics import Client
from eventtracking.backends.segment import SegmentBackend as BaseSegmentBackend

import logging

from track.backends import BaseBackend

log = logging.getLogger('track.backends.logger')


class SegmentBackend(BaseSegmentBackend, BaseBackend):
    def __init__(self, **kwargs):
        self.blacklist = kwargs.get('blacklist', [])

    def send(self, event):
        event_name = event.get('name')
        if event_name and event_name in self.blacklist:
            return

        super(SegmentBackend, self).send(event)


class SiteSegmentBackend(BaseSegmentBackend, BaseBackend):
    def __init__(self, **kwargs):
        """Event tracker backend that uses a python logger.

        :Parameters:
          - `name`: identifier of the logger, which should have
            been configured using the default python mechanisms.

        """
        super(SiteSegmentBackend, self).__init__()
        self.event_logger = logging.getLogger('segment_override')

    def get_site_segment_key(self, event):
        """
        Get the current site configuration to see if there is a custom key
        configured
        :return: Segment IO write key
        """
        site_configuration = event.get('context').get('site_configuration')
        if site_configuration:
            return site_configuration.get('SEGMENT_KEY')

        return None

    def get_site_google_analytics_key(self, event):
        """
        Get the current site configuration to see if there is a custom key
        configured
        :return: Segment IO write key
        """
        site_configuration = event.get('context').get('site_configuration')
        if site_configuration:
            return site_configuration.get('GOOGLE_ANALYTICS_TRACKING_ID')

        return None

    def send(self, event):
        """
        Process the event using all registered processors and send it to all registered backends.
        Logs and swallows all `Exception`.
        """
        site_segment_key = self.get_site_segment_key(event)
        if not site_segment_key:
            return

        del event['context']['site_configuration']

        context = event.get('context', {})
        user_id = context.get('user_id')
        event_source = context.get('event_source')

        event_data = event.get('data')

        info = event_data.get('info')
        name = event.get('name')
        if name is None or user_id is None:
            return

        segment_context = {}

        ga_client_id = self.get_site_google_analytics_key(event)
        if ga_client_id is not None:
            segment_context['Google Analytics'] = {
                'clientId': ga_client_id
            }

        site_segment_client = Client(
            write_key=site_segment_key,
            debug=False, on_error=None, send=True
        )

        if event_source == 'browser.identify':
            site_segment_client.identify(
                user_id=user_id,
                traits=info
            )
        elif event_source == 'browser.page':
            site_segment_client.page(
                user_id=user_id,
                properties=info
            )
        elif event_source == 'browser.track':
            print('received info')
            site_segment_client.track(
                user_id,
                event_data.get('name'),
                properties=info,
                context=segment_context
            )
        else:
            site_segment_client.track(
                user_id,
                name,
                event,
                context=segment_context
            )
