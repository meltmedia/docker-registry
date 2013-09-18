
import cStringIO as StringIO
import hashlib
import json
import os
import random
import string
import sys
import unittest

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_path)
sys.path.append(os.path.join(root_path, 'lib'))

import registry


class TestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        registry.app.testing = True
        self.http_client = registry.app.test_client()

    def gen_random_string(self, length=16):
        return ''.join([random.choice(string.ascii_uppercase + string.digits)
                        for x in range(length)]).lower()

    def upload_image(self, image_id, parent_id, layer,
                     set_checksum_callback=None):
        json_obj = {
            'id': image_id
        }
        if parent_id:
            json_obj['parent'] = parent_id
        json_data = json.dumps(json_obj)
        h = hashlib.sha256(json_data + '\n')
        h.update(layer)
        layer_checksum = 'sha256:{0}'.format(h.hexdigest())
        headers = {'X-Docker-Checksum': layer_checksum}
        if set_checksum_callback:
            headers = {}
        resp = self.http_client.put('/v1/images/{0}/json'.format(image_id),
                                    headers=headers,
                                    data=json_data)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Make sure I cannot download the image before push is complete
        resp = self.http_client.get('/v1/images/{0}/json'.format(image_id))
        self.assertEqual(resp.status_code, 400, resp.data)
        layer_file = StringIO.StringIO(layer)
        resp = self.http_client.put('/v1/images/{0}/layer'.format(image_id),
                                    input_stream=layer_file)
        layer_file.close()
        self.assertEqual(resp.status_code, 200, resp.data)
        if set_checksum_callback:
            set_checksum_callback(image_id, layer_checksum)
        # Push done, test reading the image
        resp = self.http_client.get('/v1/images/{0}/json'.format(image_id))
        self.assertEqual(resp.headers.get('x-docker-size'), str(len(layer)))
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.headers['x-docker-checksum'], layer_checksum)

    def test_cors(self):
        resp = self.http_client.get('/v1/_ping')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.headers.get('Access-Control-Allow-Origin'), '*', resp.headers)
