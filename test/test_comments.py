import unittest

from osc2.comments import PackageComment, ProjectComment, RequestComment
from test.osctest import OscTest
from test.httptest import GET, POST


def suite():
    return unittest.makeSuite(TestComments)


class TestComments(OscTest):
    def __init__(self, *args, **kwargs):
        kwargs['fixtures_dir'] = 'test_comments_fixtures'
        super(TestComments, self).__init__(*args, **kwargs)

    @POST('http://localhost/comments/package/openSUSE%3AFactory/osc',
          exp='This is a test', text='<OK/>')
    def test_create_package_comment(self):
        """test create package comment"""
        pkg_comment_ctrl = PackageComment('openSUSE:Factory', 'osc')
        pcmt = pkg_comment_ctrl.create('This is a test', None)

    @POST('http://localhost/comments/project/openSUSE%3AFactory',
          exp='This is a test', text='<OK/>')
    def test_create_project_comment(self):
        """test create project comment"""
        proj_comment_ctrl = ProjectComment('openSUSE:Factory')
        projcmt = proj_comment_ctrl.create('This is a test', None)

    @POST('http://localhost/comments/request/1', exp='This is a test',
          text='<OK/>')
    def test_create_request_comment(self):
        """test create request comment"""
        req_comment_ctrl = RequestComment('1')
        rcmt = req_comment_ctrl.create('This is a test', None)

    @GET('http://localhost/comments/package/openSUSE%3AFactory/osc',
         file='pkg_comments.xml')
    def test_list_package_comments(self):
        """test list package comments"""
        PackageComment.SCHEMA = self.fixture_file('pkg_comment.xsd')
        pkg_comment_ctrl = PackageComment('openSUSE:Factory', 'osc')
        pcmt = pkg_comment_ctrl.list(None, None)
        self.assertEqual(pcmt.get('package'), 'osc')
        self.assertEqual(pcmt.comment[0], 'P_Comment_1')
        self.assertEqual(pcmt.comment[1], 'P_Comment_2')

    @GET('http://localhost/comments/project/openSUSE%3AFactory',
         file='proj_comments.xml')
    def test_list_project_comments(self):
        """test list package comments"""
        ProjectComment.SCHEMA = self.fixture_file('proj_comment.xsd')
        proj_comment_ctrl = ProjectComment('openSUSE:Factory')
        projcmt = proj_comment_ctrl.list(None, None)
        self.assertEqual(projcmt.get('project'), 'openSUSE:Factory')
        self.assertEqual(projcmt.comment[0], 'Proj_Comment_1')
        self.assertEqual(projcmt.comment[1], 'Proj_Comment_2')

    @GET('http://localhost/comments/request/1', file='req_comments.xml')
    def test_list_request_comments(self):
        """test list request comments"""
        RequestComment.SCHEMA = self.fixture_file('req_comment.xsd')
        req_comment_ctrl = RequestComment('1')
        rcmt = req_comment_ctrl.list(None, None)
        self.assertEqual(rcmt.get('request'), '1')
        self.assertEqual(rcmt.comment[0], 'R_Comment_1')
        self.assertEqual(rcmt.comment[1], 'R_Comment_2')

if __name__ == '__main__':
    unittest.main()
