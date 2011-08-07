import os
import unittest
import stat
from cStringIO import StringIO, OutputType

from lxml import etree

from osc.remote import (RemoteProject, RemotePackage, Request,
                        RORemoteFile, RWRemoteFile, RWLocalFile)
from test.osctest import OscTest
from test.httptest import GET, PUT, POST, DELETE


def suite():
    return unittest.makeSuite(TestRemoteModel)


class TestRemoteModel(OscTest):
    def __init__(self, *args, **kwargs):
        kwargs['fixtures_dir'] = 'test_remote_fixtures'
        super(TestRemoteModel, self).__init__(*args, **kwargs)

    @GET('http://localhost/source/foo/_meta', file='project.xml')
    def test_project1(self):
        """get a remote project"""
        prj = RemoteProject.find('foo')
        self.assertEqual(prj.title, 'just a dummy title')
        self.assertEqual(prj.description, 'This is a detailed and more' \
                                          ' lengthy\ndescription of the foo' \
                                          '\nproject.')
        self.assertEqual(prj.repository.get('name'), 'openSUSE_Factory')
        self.assertEqual(prj.repository.path.get('project'),
                         'openSUSE:Factory')
        self.assertEqual(prj.repository.path.get('repository'), 'standard')
        self.assertEqual(prj.repository.arch[:], ['x86_64', 'i586'])
        self.assertEqual(prj.person[0].get('userid'), 'testuser')
        self.assertEqual(prj.person[0].get('role'), 'maintainer')
        self.assertEqual(prj.person[1].get('userid'), 'foobar')
        self.assertEqual(prj.person[1].get('role'), 'bugowner')

    @PUT('http://localhost/source/foo/_meta', text='OK', expfile='project.xml')
    def test_project2(self):
        """create a remote project"""
        prj = RemoteProject(name='foo')
        prj.title = 'just a dummy title'
        prj.description = 'This is a detailed and more lengthy\ndescription' \
                          ' of the foo\nproject.'
        prj.add_person(userid='testuser', role='maintainer')
        prj.add_person(userid='foobar', role='bugowner')
        repo = prj.add_repository(name='openSUSE_Factory')
        repo.add_path(project='openSUSE:Factory', repository='standard')
        repo.add_arch('x86_64')
        repo.add_arch('i586')
        prj.store()

    @GET('http://localhost/source/foo/_meta', file='project.xml')
    @PUT('http://localhost/source/foo/_meta', text='OK',
         expfile='project_modified.xml')
    def test_project3(self):
        """get, modify, store remote project"""
        prj = RemoteProject.find('foo')
        # delete maintainer
        del prj.person[0]
        # delete arch i586
        del prj.repository.arch[1]
        # add additional repo (this time <arch /> first then <path />)
        repo = prj.add_repository(name='openSUSE_11.4')
        repo.add_arch('i586')
        repo.add_path(project='openSUSE:11.4', repository='standard')
        # modify title
        prj.title = 'new title'
        # add + remove illegal tag
        prj.something = 'oops'
        del prj.something
        prj.store()

    @GET('http://localhost/source/test/_meta', file='project_simple.xml')
    @PUT('http://localhost/source/test/_meta', text='OK',
         expfile='project_simple_modified.xml')
    def test_project4(self):
        """test project validation"""
        RemoteProject.SCHEMA = self.fixture_file('project_simple.xsd')
        prj = RemoteProject.find('test')
        prj.person.set('userid', 'bar')
        prj.store()
        RemoteProject.SCHEMA = ''

    @PUT('http://localhost/source/test/_meta', text='<OK />',
         expfile='project_simple_modified.xml')
    def test_project5(self):
        """test project validation"""
        RemoteProject.SCHEMA = self.fixture_file('project_simple.xsd')
        RemoteProject.PUT_RESPONSE_SCHEMA = self.fixture_file('ok_simple.xsd')
        prj = RemoteProject('test')
        prj.add_person(userid='bar', role='maintainer')
        prj.store()
        RemoteProject.SCHEMA = ''
        RemoteProject.PUT_RESPONSE_SCHEMA = ''

    def test_project6(self):
        """test project validation (invalid model)"""
        RemoteProject.SCHEMA = self.fixture_file('project_simple.xsd')
        prj = RemoteProject('test')
        prj.add_unknown('foo')
        self.assertRaises(etree.DocumentInvalid, prj.validate)
        self.assertRaises(etree.DocumentInvalid, prj.store)
        RemoteProject.SCHEMA = ''

    @GET('http://localhost/source/test/_meta', text='<invalid />')
    def test_project7(self):
        """test project validation (invalid xml response)"""
        RemoteProject.SCHEMA = self.fixture_file('project_simple.xsd')
        self.assertRaises(etree.DocumentInvalid, RemoteProject.find, 'test')
        RemoteProject.SCHEMA = ''

    @PUT('http://localhost/source/test/_meta', text='<INVALID />',
         exp='<project name="test"/>\n')
    def test_project8(self):
        """test project validation 3 (invalid xml response after store)"""
        RemoteProject.SCHEMA = self.fixture_file('project_simple.xsd')
        RemoteProject.PUT_RESPONSE_SCHEMA = self.fixture_file('ok_simple.xsd')
        prj = RemoteProject('test')
        # check that validation is ok
        prj.validate()
        self.assertRaises(etree.DocumentInvalid, prj.store)
        RemoteProject.SCHEMA = ''
        RemoteProject.PUT_RESPONSE_SCHEMA = ''

    @GET('http://localhost/source/foo/_meta', file='project.xml')
    def test_project9(self):
        """test exists method"""
        self.assertTrue(RemoteProject.exists('foo'))

    @GET('http://localhost/source/bar/_meta', text='<nonexistent />', code=404)
    def test_project10(self):
        """test exists method"""
        self.assertFalse(RemoteProject.exists('bar'))

    @DELETE('http://localhost/source/foo', text='<OK/>')
    def test_project11(self):
        """test delete method"""
        self.assertTrue(RemoteProject.delete('foo'))

    @DELETE('http://localhost/source/foo', text='<OK/>', code=404)
    def test_project11(self):
        """test delete method"""
        self.assertFalse(RemoteProject.delete('foo'))

    @GET('http://localhost/source/openSUSE%3ATools/osc/_meta',
         file='package.xml')
    def test_package1(self):
        """get a remote package"""
        pkg = RemotePackage.find('openSUSE:Tools', 'osc')
        self.assertEqual(pkg.get('project'), 'openSUSE:Tools')
        self.assertEqual(pkg.get('name'), 'osc')
        self.assertEqual(pkg.title, 'tiny title')
        self.assertEqual(pkg.description, 'some useless\ndescription...')
        self.assertIsNotNone(pkg.debuginfo.disable)
        self.assertIsNotNone(pkg.debuginfo.disable[0])
        self.assertEqual(pkg.debuginfo.enable[0].get('repository'),
                         'openSUSE_Factory')
        self.assertEqual(pkg.debuginfo.enable[1].get('repository'),
                         'some_repo')
        self.assertEqual(pkg.debuginfo.enable[1].get('arch'), 'i586')
        self.assertEqual(pkg.person.get('userid'), 'foobar')
        self.assertEqual(pkg.person.get('role'), 'maintainer')

    @PUT('http://localhost/source/openSUSE%3ATools/osc/_meta', text='OK',
         expfile='package.xml')
    def test_package2(self):
        """create a remote package"""
        pkg = RemotePackage('openSUSE:Tools', 'osc')
        debug = pkg.add_debuginfo()
        debug.add_disable()
        debug.add_enable(repository='openSUSE_Factory')
        debug.add_enable(repository='some_repo', arch='i586')
        pkg.title = 'tiny title'
        pkg.description = 'some useless\ndescription...'
        # modify person afterwards
        person = pkg.add_person(userid='wrongid', role='maintainer')
        person.set('userid', 'foobar')
        pkg.store()

    @GET('http://localhost/source/openSUSE%3ATools/osc/_meta',
         file='package.xml')
    @PUT('http://localhost/source/openSUSE%3ATools/osc/_meta', text='OK',
         expfile='package_modified.xml')
    def test_package3(self):
        """get, modify, store remote package"""
        pkg = RemotePackage.find('openSUSE:Tools', 'osc')
        # remove debuginfo element
        del pkg.debuginfo
        # add build element
        build = pkg.add_build()
        build.add_enable(arch='x86_64')
        build.add_disable(arch='i586')
        # add devel element
        pkg.add_devel(project='openSUSE:Factory', package='osc')
        pkg.store()

    @GET('http://localhost/source/foo/bar/_meta', file='package_simple.xml')
    @PUT('http://localhost/source/newprj/bar/_meta', text='OK',
         expfile='package_simple_modified.xml')
    def test_package4(self):
        """test package validation"""
        RemotePackage.SCHEMA = self.fixture_file('package_simple.xsd')
        pkg = RemotePackage.find('foo', 'bar')
        pkg.set('project', 'newprj')
        pkg.store()
        RemotePackage.SCHEMA = ''

    @PUT('http://localhost/source/newprj/bar/_meta', text='<OK />',
         expfile='package_simple_modified.xml')
    def test_package5(self):
        """test package validation"""
        RemotePackage.SCHEMA = self.fixture_file('package_simple.xsd')
        RemotePackage.PUT_RESPONSE_SCHEMA = self.fixture_file('ok_simple.xsd')
        pkg = RemotePackage('newprj', 'bar')
        pkg.store()
        RemotePackage.SCHEMA = ''
        RemotePackage.PUT_RESPONSE_VALIDATION = ''

    def test_package6(self):
        """test package validation (invalid model)"""
        RemotePackage.SCHEMA = self.fixture_file('package_simple.xsd')
        pkg = RemotePackage('foo', 'bar')
        pkg.set('invalidattr', 'yes')
        self.assertRaises(etree.DocumentInvalid, pkg.validate)
        self.assertRaises(etree.DocumentInvalid, pkg.store)
        RemotePackage.SCHEMA = ''

    @GET('http://localhost/source/foo/bar/_meta', text='<invalid />')
    def test_package7(self):
        """test package validation (invalid xml response)"""
        RemotePackage.SCHEMA = self.fixture_file('package_simple.xsd')
        self.assertRaises(etree.DocumentInvalid, RemotePackage.find,
                          'foo', 'bar')
        RemotePackage.SCHEMA = ''

    @PUT('http://localhost/source/foo/bar/_meta', text='<INVALID />',
         exp='<package project="foo" name="bar"/>\n')
    def test_package8(self):
        """test package validation (invalid xml response after store)"""
        RemotePackage.SCHEMA = self.fixture_file('package_simple.xsd')
        RemotePackage.PUT_RESPONSE_SCHEMA = self.fixture_file('ok_simple.xsd')
        pkg = RemotePackage('foo', 'bar')
        # check that validation is ok
        pkg.validate()
        self.assertRaises(etree.DocumentInvalid, pkg.store)
        RemotePackage.SCHEMA = ''
        RemotePackage.PUT_RESPONSE_VALIDATION = ''

    @GET('http://localhost/source/newprj/bar/_meta', file='package.xml')
    def test_package9(self):
        """test exists method"""
        self.assertTrue(RemotePackage.exists('newprj', 'bar'))

    @GET('http://localhost/source/newprj/foo/_meta', file='package.xml',
         code=404)
    def test_package10(self):
        """test exists method"""
        self.assertFalse(RemotePackage.exists('newprj', 'foo'))

    @DELETE('http://localhost/source/foo/bar', text='<OK/>')
    def test_package11(self):
        """test delete method"""
        self.assertTrue(RemotePackage.delete('foo', 'bar'))

    @DELETE('http://localhost/source/foo/bar', text='<OK/>', code=404)
    def test_package11(self):
        """test delete method"""
        self.assertFalse(RemotePackage.delete('foo', 'bar'))

    @GET('http://localhost/request/123', file='request.xml')
    def test_request1(self):
        """get a request"""
        req = Request.find('123')
        self.assertTrue(len(req.action[:]) == 2)
        self.assertEqual(req.action[0].get('type'), 'submit')
        self.assertEqual(req.action[0].source.get('package'), 'abc')
        self.assertEqual(req.action[0].source.get('project'), 'xyz')
        self.assertEqual(req.action[0].options.sourceupdate, 'cleanup')
        self.assertEqual(req.action[0].options.updatelink, '1')
        self.assertEqual(req.action[1].get('type'), 'add_role')
        self.assertEqual(req.action[1].target.get('project'), 'home:foo')
        self.assertEqual(req.action[1].person.get('name'), 'bar')
        self.assertEqual(req.action[1].person.get('role'), 'maintainer')
        self.assertEqual(req.action[1].group.get('name'), 'groupxyz')
        self.assertEqual(req.action[1].group.get('role'), 'reader')
        self.assertEqual(req.state.get('name'), 'review')
        self.assertEqual(req.state.get('when'), '2010-12-27T01:36:29')
        self.assertEqual(req.state.get('who'), 'abc')
        self.assertEqual(req.review.get('by_group'), 'group1')
        self.assertEqual(req.review.get('state'), 'new')
        self.assertEqual(req.review.get('when'), '2010-12-28T00:11:22')
        self.assertEqual(req.review.get('who'), 'abc')
        self.assertTrue(len(req.history[:]) == 1)
        self.assertEqual(req.review.comment, 'review start')
        self.assertEqual(req.history[0].get('name'), 'new')
        self.assertEqual(req.history[0].get('when'), '2010-12-11T00:00:00')
        self.assertEqual(req.history[0].get('who'), 'creator')

    @POST('http://localhost/request?cmd=create', file='request_created.xml',
          expfile='request_create.xml')
    def test_request2(self):
        """create a request"""
        req = Request()
        action = req.add_action(type='submit')
        action.add_source(project='foo', package='bar', rev='12345')
        action.add_target(project='foobar')
        options = action.add_options()
        options.add_sourceupdate('cleanup')
        req.description = 'some description'
        req.store()
        self.assertEqual(req.get('id'), '42')
        self.assertTrue(len(req.action) == 1)
        self.assertEqual(req.action[0].get('type'), 'submit')
        self.assertEqual(req.action[0].source.get('project'), 'foo')
        self.assertEqual(req.action[0].source.get('package'), 'bar')
        self.assertEqual(req.action[0].source.get('rev'), '12345')
        self.assertEqual(req.action[0].target.get('project'), 'foobar')
        self.assertEqual(req.action[0].options.sourceupdate, 'cleanup')
        self.assertEqual(req.state.get('name'), 'new')
        self.assertEqual(req.state.get('who'), 'username')
        self.assertEqual(req.state.get('when'), '2011-06-10T14:33:55')
        self.assertEqual(req.description, 'some description')

    @GET('http://localhost/request/456', file='request_simple_created.xml')
    @POST('http://localhost/request?cmd=create',
          file='request_simple_created.xml',
          expfile='request_simple_create.xml')
    def test_request3(self):
        """test request validation (incoming + outgoing)"""
        Request.SCHEMA = self.fixture_file('request_simple.xsd')
        req = Request.find('456')
        req = Request()
        req.add_action(type='submit')
        req.store()
        Request.SCHEMA = ''

    @GET('http://localhost/request/456', text='<invalid />')
    @POST('http://localhost/request?cmd=create',
          text='<invalid />',
          expfile='request_simple_create.xml')
    def test_request4(self):
        """test request validation (incoming + outgoing)"""
        Request.SCHEMA = self.fixture_file('request_simple.xsd')
        self.assertRaises(etree.DocumentInvalid, Request.find, '456')
        req = Request()
        req.add_action(type='submit')
        req.add_invalid(attr='inv')
        # no http request is made because validation fails
        self.assertRaises(etree.DocumentInvalid, req.store)
        req = Request()
        req.add_action(type='submit')
        # check that validation is ok
        req.validate()
        # we get an invalid response
        self.assertRaises(etree.DocumentInvalid, req.store)
        Request.SCHEMA = ''

    @GET('http://localhost/request/123', file='request.xml')
    def test_request5(self):
        """test exists method"""
        self.assertTrue(Request.exists('123'))

    @GET('http://localhost/request/123', file='request.xml', code=404)
    def test_request6(self):
        """test exists method"""
        self.assertFalse(Request.exists('123'))

    @DELETE('http://localhost/request/123', text='<OK/>')
    def test_request7(self):
        """test delete method"""
        self.assertTrue(Request.delete('123'))

    @DELETE('http://localhost/request/123', text='<OK/>', code=404)
    def test_request8(self):
        """test delete method"""
        self.assertFalse(Request.delete('123'))

    @GET('http://localhost/source/project/package/fname', file='remotefile1')
    def test_remotefile1(self):
        """get a simple file1"""
        f = RORemoteFile('/source/project/package/fname')
        self.assertEqual(f.read(5), 'This ')
        self.assertEqual(f.read(), 'is a simple file\nwith some newlines\n\n' \
                                   'and\ntext.\n')

    @GET('http://localhost/source/project/package/fname', file='remotefile1')
    @GET('http://localhost/source/project/package/fname2', file='remotefile2')
    def test_remotefile2(self):
        """iterate over the file"""
        f = RORemoteFile('/source/project/package/fname')
        i = iter(f)
        self.assertEqualFile(i.next(), 'remotefile1')
        f = RORemoteFile('/source/project/package/fname2', stream_bufsize=6)
        i = iter(f)
        self.assertEqual(i.next(), 'yet an')
        self.assertEqual(i.next(), 'other\n')
        self.assertEqual(i.next(), 'simple')
        self.assertEqual(i.next(), '\nfile\n')

    @GET('http://localhost/source/project/package/fname2', file='remotefile2')
    def test_remotefile3(self):
        """store file"""
        f = RORemoteFile('/source/project/package/fname2')
        sio = StringIO()
        f.write_to(sio, size=12)
        self.assertEqual(sio.getvalue(), 'yet another\n')
        sio = StringIO()
        f.write_to(sio)
        self.assertEqual(sio.getvalue(), 'simple\nfile\n')

    def test_remotefile4(self):
        """test exception (we don't try to overwrite existing files)"""
        f = RORemoteFile('/foo/bar')
        # do not run this as privileged user
        assert not os.access('/', os.W_OK)
        self.assertRaises(ValueError, f.write_to, '/foo')

    @GET('http://localhost/source/project/package/fname2', file='remotefile2')
    def test_remotefile5(self):
        """store file"""
        f = RORemoteFile('/source/project/package/fname2', mtime=1311512569)
        path = self.fixture_file('write_me')
        f.write_to(path)
        self.assertEqualFile('yet another\nsimple\nfile\n', 'remotefile2')
        st = os.stat(path)
        self.assertEqual(st.st_mtime, 1311512569)
        # default mode is 0644
        self.assertEqual(stat.S_IMODE(st.st_mode), 420)

    @GET('http://localhost/source/project/package/fname?rev=123',
         file='remotefile1', Content_Length='52')
    def test_rwremotefile1(self):
        """read and seek through a file"""
        f = RWRemoteFile('/source/project/package/fname', rev='123')
        f.seek(1, os.SEEK_SET)
        self.assertEqual(f.read(7), 'his is ')
        f.seek(0, os.SEEK_SET)
        self.assertEqual(f.read(7), 'This is')
        f.seek(0, os.SEEK_SET)
        self.assertTrue(len(f.readlines()) == 5)
        f.seek(0, os.SEEK_SET)
        self.assertEqual(f.readline(), 'This is a simple file\n')
        self.assertEqual(f.readline(), 'with some newlines\n')
        self.assertEqual(f.read(), '\nand\ntext.\n')
        f.close()

    @PUT('http://localhost/source/project/package/fname2', text='ok',
         expfile='remotefile2')
    def test_rwremotefile2(self):
        """write to file"""
        f = RWRemoteFile('/source/project/package/fname2')
        f.write('yet another\nsim')
        f.write('ple\nfile\n')
        f.close()

    @PUT('http://localhost/source/project/package/fname2?foo=bar', text='ok',
         exp='yet another\nsim')
    def test_rwremotefile3(self):
        """write and seek"""
        f = RWRemoteFile('/source/project/package/fname2')
        f.write('ple\nfile\n')
        f.seek(0, os.SEEK_SET)
        f.write('yet another\nsim')
        f.close(foo='bar')

    @GET('http://localhost/source/project/package/fname2', file='remotefile2',
         Content_Length='24')
    @PUT('http://localhost/source/project/package/fname2', text='ok',
         expfile='remotefile2_modified')
    def test_rwremotefile4(self):
        """append to existing file"""
        f = RWRemoteFile('/source/project/package/fname2', append=True)
        # read first line
        self.assertEqual(f.readline(), 'yet another\n')
        # append/overwrite text
        f.write('more complex\n')
        f.write('testcase\n')
        # check that it is a StringIO
        self.assertTrue(isinstance(f._fobj, OutputType))
        f.close()

    @GET('http://localhost/source/project/package/fname?rev=123',
         file='remotefile1', Content_Length='52')
    def test_rwremotefile5(self):
        """read and seek through a file (tmpfile)"""
        f = RWRemoteFile('/source/project/package/fname',
                         tmp_size=20, rev='123')
        f.seek(1, os.SEEK_SET)
        self.assertTrue(os.path.exists(f._fobj.name))
        self.assertEqual(f.read(7), 'his is ')
        f.seek(0, os.SEEK_SET)
        self.assertEqual(f.read(7), 'This is')
        f.seek(0, os.SEEK_SET)
        self.assertTrue(len(f.readlines()) == 5)
        f.seek(0, os.SEEK_SET)
        self.assertEqual(f.readline(), 'This is a simple file\n')
        self.assertEqual(f.readline(), 'with some newlines\n')
        self.assertEqual(f.read(), '\nand\ntext.\n')
        f.close()
        self.assertFalse(os.path.exists(f._fobj.name))

    @PUT('http://localhost/source/project/package/fname2', text='ok',
         expfile='remotefile2')
    def test_rwremotefile6(self):
        """write to file (tmpfile)"""
        f = RWRemoteFile('/source/project/package/fname2', use_tmp=True)
        f.write('yet another\nsim')
        self.assertTrue(os.path.exists(f._fobj.name))
        f.write('ple\nfile\n')
        f.close()
        self.assertFalse(os.path.exists(f._fobj.name))

    @PUT('http://localhost/source/project/package/fname2?foo=bar', text='ok',
         exp='yet another\nsim')
    def test_rwremotefile7(self):
        """write and seek (tmpfile)"""
        f = RWRemoteFile('/source/project/package/fname2', use_tmp=True)
        f.write('ple\nfile\n')
        self.assertTrue(os.path.exists(f._fobj.name))
        f.seek(0, os.SEEK_SET)
        f.write('yet another\nsim')
        f.close(foo='bar')
        self.assertFalse(os.path.exists(f._fobj.name))

    @GET('http://localhost/source/project/package/fname2', file='remotefile2',
         Content_Length='24')
    @PUT('http://localhost/source/project/package/fname2', text='ok',
         expfile='remotefile2_modified')
    def test_rwremotefile8(self):
        """append to existing file"""
        f = RWRemoteFile('/source/project/package/fname2',
                         tmp_size=15, append=True)
        # read first line
        self.assertEqual(f.readline(), 'yet another\n')
        self.assertTrue(os.path.exists(f._fobj.name))
        # append/overwrite text
        f.write('more complex\n')
        f.write('testcase\n')
        f.close()
        self.assertFalse(os.path.exists(f._fobj.name))

    @GET('http://localhost/source/project/package/fname', file='remotefile1')
    @GET('http://localhost/source/project/package/fname2', file='remotefile2')
    @GET('http://localhost/source/project/package/fname2', file='remotefile2')
    def test_rwremotefile9(self):
        """iterate over the file (but read only 8 bytes)"""
        f = RORemoteFile('/source/project/package/fname')
        i = iter(f)
        self.assertEqualFile(i.next(), 'remotefile1')
        f = RORemoteFile('/source/project/package/fname2', stream_bufsize=6)
        i = f.__iter__(size=8)
        self.assertEqual(i.next(), 'yet an')
        self.assertEqual(i.next(), 'ot')
        f = RWRemoteFile('/source/project/package/fname2', stream_bufsize=6)
        i = f.__iter__(size=8)
        self.assertEqual(i.next(), 'yet an')
        self.assertEqual(i.next(), 'ot')

    @GET('http://localhost/source/project/package/fname2', file='remotefile2')
    def test_rwremotefile10(self):
        """read some bytes, write some bytes and call write_to"""
        f = RWRemoteFile('/source/project/package/fname2', append=True)
        self.assertEqual(f.read(3), 'yet')
        self.assertTrue(isinstance(f._fobj, OutputType))
        f.write('01234567')
        sio = StringIO()
        f.write_to(sio, 7)
        self.assertEqual(sio.getvalue(), '\nsimple')

    @PUT('http://localhost/other/path?foo=bar', text='ok',
         exp='yet another\nsim')
    @PUT('http://localhost/other/path', text='ok',
         exp='yet another\nsim')
    def test_rwremotefile11(self):
        """write, seek and multiple write backs"""
        f = RWRemoteFile('/source/project/package/fname2',
                         wb_path='/other/path')
        f.write('ple\nfile\n')
        f.seek(0, os.SEEK_SET)
        f.write('yet another\nsim')
        f.write_back(foo='bar')
        # no request is issued because file isn't modified
        f.write_back()
        # force write back
        f.write_back(force=True)
        # no write back is issued
        f.close(foo='bar')

    @PUT('http://localhost/foo/bar?foo=bar', text='ok',
         exp='some data')
    def test_rwlocalfile1(self):
        """test simple read write (file does not exist)"""
        path = self.fixture_file('doesnotexist')
        self.assertFalse(os.path.exists(path))
        f = RWLocalFile(path, wb_path='/foo/bar')
        f.write('some data')
        f.flush()
        self.assertTrue(os.path.isfile(path))
        with open(path, 'r') as fobj:
            self.assertEqual(fobj.read(), 'some data')
        f.seek(0, os.SEEK_SET)
        self.assertEqual(f.read(), 'some data')
        f.write_back(foo='bar')
        f.close()

    def test_rwlocalfile2(self):
        """no wb_path is specified"""
        path = self.fixture_file('doesnotexist')
        self.assertRaises(ValueError, RWLocalFile, path)

    @PUT('http://localhost/source/prj/pkg/remotefile2', text='ok',
         exp = 'yet another\nsimple\nfile\n testcase\n')
    def test_rwlocalfile3(self):
        """use existing file"""
        path = self.fixture_file('remotefile2')
        self.assertTrue(os.path.exists(path))
        f = RWLocalFile(path, wb_path='/source/prj/pkg/remotefile2',
                        append=True)
        f.write(' testcase\n')
        f.flush()
        with open(path, 'r') as fobj:
            exp = 'yet another\nsimple\nfile\n testcase\n'
            self.assertEqual(fobj.read(), exp)
        f.write_back()
        f.close()

    @PUT('http://localhost/source/prj/pkg/remotefile2', text='ok',
         exp = 'yet another\nsimple\nfile\n')
    def test_rwlocalfile4(self):
        """test direct write_back (no previous read, write etc.)"""
        path = self.fixture_file('remotefile2')
        f = RWLocalFile(path, wb_path='/source/prj/pkg/remotefile2',
                        append=True)
        f.write_back(force=True)
        f.close()

if __name__ == '__main__':
    unittest.main()
