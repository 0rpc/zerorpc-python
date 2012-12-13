from hashlib import sha256
import hmac

from .events import Event


class AuthenticationFailedError(Exception):
    pass


class SignedEvent(Event):
    def __init__(self, name, args, context, header=None, create=False):
        key = header.pop('key', None) if header else None
        super(SignedEvent, self).__init__(name, args, context, header, create)
        if key and not 'signature' in self._header:
            self._header['signature'] = self.build_signature(key)
        if not key and 'signature' in self._header:
            self._header['event'] = self

    @property
    def internal(self):
        return self._name in ['_zpc_hb', 'ERR', 'OK']

    def string_to_sign(self):
        string = self._name
        if self._args:
            string += '\n%s' % ' '.join(self._args)
        return string

    def build_signature(self, key):
        return hmac.new(str(key), self.string_to_sign(), sha256).digest()


class SharedSecretMiddleware(object):
    def __init__(self, key):
        self.key = key

    def load_task_context(self, event_header):
        if 'signature' in event_header and 'event' in event_header:
            event = event_header.pop('event')
            if event_header['signature'] == event.build_signature(self.key):
                return
        raise AuthenticationFailedError

    def get_task_context(self):
        return {'key': self.key}


class ClientAuthMiddleware(object):
    def __init__(self, client_id, client_key):
        self.client_id = client_id
        self.client_key = client_key

    def get_task_context(self):
        return {'client_id': self.client_id, 'key': self.client_key}


class BaseServerAuthMiddleware(object):
    def load_task_context(self, event_header):
        if all([key in event_header
               for key in ('signature', 'event', 'client_id')]):
            client_id = event_header.pop('client_id')
            client_key = self.get_client_key(client_id)
            event = event_header.pop('event')
            if event_header['signature'] == event.build_signature(client_key):
                return
        raise AuthenticationFailedError

    def get_client_key(self, client_id):
        raise NotImplementedError
