"""Provides a base class for doing http requests and a sample implementation
based on urllib2.

Example usage:
 logger = logging.StreamHandler()
 logger.setLevel(logging.DEBUG)
 logging.getLogger('httprequest').addHandler(ch)
 logging.getLogger('httprequest').setLevel(logging.DEBUG)
 r = Urllib2HTTPRequest('https://host', username='user', password='pass')
 f = r.get('/source/home:Marcus_H/_meta', schema='/path/to/schema.(rng|xsd)')
 print f.read()
"""

import os
import urllib2
import urllib
import cookielib
import urlparse
import cStringIO
import mmap
import logging

from lxml import etree

__all__ = ['AbstractHTTPRequest', 'Urllib2HTTPRequest']

class AbstractHTTPRequest(object):
    """Base class which provides methods for doing http requests.

    All parameters passed to the methods which make up the url will be quoted
    before issuing the request.

    """

    def __init__(self, apiurl, validate=False):
        """Constructs a new object.

        apiurl is the target location for each request. It is a str which
        consists of a scheme and host and an optional port, for example
        http://example.com.
        Keyword arguments:
        validate -- if True xml response will be validated (if a schema was
                    specifed) (default False)

        """
        self.apiurl = apiurl
        self.validate = validate

    def get(self, path, schema='', **query):
        """Issues a http request to apiurl/path.

        The path parameter specified the path of the url.
        Keyword arguments:
        schema -- path to schema file (default '')
        query -- optional query parameters

        """
        raise NotImplementedError()

    def put(self, path, data=None, filename='', schema='', **query):
        """Issues a http PUT request to apiurl/path.

        Either data or file mustn't be None.
        Keyword arguments:
        data -- a str or file-like object which should be PUTed (default None)
        filename -- path to a file which should be PUTed (default None)
        schema -- path to schema file (default '')
        query -- optional query parameters

        """
        raise NotImplementedError()

    def post(self, path, data=None, filename='', urlencoded=False,
             schema='', **query):
        """Issues a http POST request to apiurl/path.

        Either data or file mustn't be None.
        Keyword arguments:
        data -- a str or file-like object which should be POSTed (default None)
        filename -- path to a file which should be POSTed (default None)
        schema -- path to schema file (default '')
        urlencoded -- used to indicate if the data has to be urlencoded or not;
                      if set to True the requests's Content-Type is
                      'application/x-www-form-urlencoded' (default: False,
                      default Content-Type: 'application/octet-stream')
        query -- optional query parameters

        """
        raise NotImplementedError()

    def delete(self, path, schema='', **query):
        """Issues a http DELETE request to apiurl/path.

        Keyword arguments:
        schema -- path to schema file (default '')
        query -- optional query parameters

        """
        raise NotImplementedError()

class Urllib2HTTPRequest(AbstractHTTPRequest):
    """Do http requests with urllib2.

    Basically this class just delegates the requests to urllib2. It also
    supports basic auth authentification.

    """

    def __init__(self, apiurl, validate=False, username='', password='',
                 cookie_filename='', debug=False, mmap=True,
                 mmap_fsize=1024*512):
        """constructs a new Urllib2HTTPRequest object.

        apiurl is the url which is used for every request.
        Keyword arguments:
        validate -- global flag to control validation (if set to False no
                    response validation is done - even if a schema file
                    was specified) (default False)
        username -- username which is used for basic authentification
                    (default '')
        password -- password which is used for basic authentification
                    (default '')
        debug -- log debug messages
        mmap -- use mmap when POSTing or PUTing a file (default True)
        mmap_fsize -- specifies the minimum filesize for using mmap
                      (default 1024*512)

        """

        AbstractHTTPRequest.__init__(self, apiurl, validate)
        self.debug = debug
        self._use_mmap = mmap
        self._mmap_fsize = mmap_fsize
        self._logger = logging.getLogger(__name__)
        self._install_opener(username, password, cookie_filename)

    def _install_opener(self, username, password, cookie_filename):
        handlers = []
        cookie_processor = self._setup_cookie_processor(cookie_filename)
        if cookie_processor is not None:
            handlers.append(cookie_processor)
        authhandler = self._setup_authhandler(username, password)
        if authhandler is not None:
            handlers.append(authhandler)
        if self.debug:
            urllib2.AbstractHTTPHandler.__init__ = (
                lambda self, debuglevel=0: setattr(self, '_debuglevel', 1))
        opener = urllib2.build_opener(*handlers)
        urllib2.install_opener(opener)

    def _setup_cookie_processor(self, cookie_filename):
        if not cookie_filename:
            return None
        if (os.path.exists(cookie_filename) and not
            os.path.isfile(cookie_filename)):
            raise ValueError("%s exists but is no file" % cookie_filename)
        elif not os.path.exists(cookie_file):
            open(cookie_file, 'w').close()
        cookiejar = cookielib.LWPCookieJar(cookie_filename)
        cookiejar.load(ignore_discard=True)
        return urllib2.HTTPCookieProcessor(cookiejar)

    def _setup_authhandler(self, username, password):
        if username == '':
            return None
        authhandler = urllib2.HTTPBasicAuthHandler(
            urllib2.HTTPPasswordMgrWithDefaultRealm())
        authhandler.add_password(None, self.apiurl, username, password)
        return authhandler

    def _build_request(self, method, path, **query):
        quoted_path = '/'.join([urllib.quote_plus(p) for p in path.split('/')])
        quoted_query = '&'.join([urllib.quote_plus(k) + '=' +
                                 urllib.quote_plus(v)
                                 for k, v in query.iteritems() if v])
        scheme, host = urlparse.urlsplit(self.apiurl)[0:2]
        url = urlparse.urlunsplit((scheme, host, quoted_path, quoted_query,
                                   ''))
        request = urllib2.Request(url)
        request.get_method = lambda: method
        return request

    def _validate_response(self, resp, schema_filename):
        if not schema_filename or not self.validate:
            return False
        self._logger.debug("validate resp against schema: %s", schema_filename)
        root = etree.fromstring(resp.read())
        resp.fp.seek(0, os.SEEK_SET)
        if schema_filename.endswith('.rng'):
            schema = etree.RelaxNG(file=schema_filename)
        elif schema_filename.endswith('.xsd'):
            schema = etree.XMLSchema(file=schema_filename)
        else:
            raise ValueError('unsupported schema file')
        schema.assertValid(root)
        return True

    def _new_response(self, resp):
        # this is needed for validation so that we can seek to the "top" of
        # the file again (after validation)
        sio = cStringIO.StringIO(resp.read())
        new_resp = urllib.addinfourl(sio, resp.headers, resp.url, resp.code)
        resp.close()
        return new_resp

    def _send_request(self, method, path, schema, **query):
        request = self._build_request(method, path, **query)
        self._logger.info(request.get_full_url())
        f = urllib2.urlopen(request)
        f = self._new_response(f)
        self._validate_response(f, schema)
        return f

    def _send_data(self, request, data, filename, schema, urlencoded):
        self._logger.info(request.get_full_url())
        f = None
        request.add_header('Content-type', 'application/octet-stream')
        if urlencoded:
            request.add_header('Content-type',
                               'application/x-www-form-urlencoded')
        if filename:
            f = self._send_file(request, filename, urlencoded)
        else:
            if urlencoded:
                data = urllib.quote_plus(data)
            f = urllib2.urlopen(request, data)
        f = self._new_response(f)
        self._validate_response(f, schema)
        return f
       
    def _send_file(self, request, filename, urlencoded):
        with open(filename, 'rb') as fobj:
            fsize = os.path.getsize(filename)
            if self._use_mmap and fsize >= self._mmap_fsize and not urlencoded:
                self._logger.debug("using mmap for file: %s" % filename)
                data = mmap.mmap(fobj.fileno(), fsize, mmap.MAP_SHARED,
                                 mmap.PROT_READ)
                data = buffer(data)
            else:
                data = fobj.read()
            if urlencoded:
                data = urllib.quote_plus(data)
            return urllib2.urlopen(request, data)

    def _check_put_post_args(self, data, filename):
        if filename and data is not None:
            raise ValueError("either specify file or data but not both")
        elif filename and not os.path.isfile(filename):
            raise ValueError("filename %s does not exist" % filename)

    def get(self, path, schema='', **query):
        return self._send_request('GET', path, schema, **query)

    def delete(self, path, schema='', **query):
        return self._send_request('DELETE', path, schema, **query)

    def put(self, path, data=None, filename='', schema='', **query):
        self._check_put_post_args(data, filename)
        request = self._build_request('PUT', path, **query)
        return self._send_data(request, data, filename, schema, False)

    def post(self, path, data=None, filename='', schema='',
             urlencoded=False, **query):
        self._check_put_post_args(data, filename)
        request = self._build_request('POST', path, **query)
        return self._send_data(request, data, filename, schema, urlencoded)
