from hashlib import sha256
import hmac


class AuthenticationFailedError(Exception):
    pass


def build_signature(event, key):
    string = event.name
    if event.args:
        string += '\n%s' % ' '.join([str(arg) for arg in event.args])
    return hmac.new(str(key), string, sha256).digest()


class SharedSecretMiddleware(object):
    def __init__(self, key):
        self.key = key

    def server_before_exec(self, event):
        signature = event.header.get('signature', None)
        if signature and signature == build_signature(event, self.key):
                return
        raise AuthenticationFailedError

    def client_before_request(self, event):
        if not 'signature' in event.header:
            event.header['signature'] = build_signature(event, self.key)


class ClientAuthMiddleware(object):
    def __init__(self, client_id, client_key):
        self.client_id = client_id
        self.client_key = client_key

    def client_before_request(self, event):
        if not 'signature' in event.header:
            event.header['signature'] = build_signature(event, self.client_key)
        if not 'client_id' in event.header:
            event.header['client_id'] = self.client_id


class BaseServerAuthMiddleware(object):
    def server_before_exec(self, event):
        signature = event.header.get('signature', None)
        client_id = event.header.get('client_id', None)
        if signature and client_id:
            client_key = self.get_client_key(client_id)
            if signature == build_signature(event, client_key):
                return
        raise AuthenticationFailedError

    def get_client_key(self, client_id):
        raise NotImplementedError
