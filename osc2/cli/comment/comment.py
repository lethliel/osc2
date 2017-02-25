"""Provides controller functions for the "comment" command."""

import logging
import collections

from osc2.httprequest import HTTPError
from osc2.util.xpath import XPathBuilder
from osc2.comments import PackageComment, ProjectComment, RequestComment
from osc2.comments import DeleteComment
from osc2.cli.util.env import run_pager, edit_message
from osc2.cli.util.shell import AbstractShell, ShellSyntaxError

LIST_TEMPLATE = 'comment/comment_list.jinja2'
SHELL_TEMPLATE = 'comment/comment_shell.jinja2'
CREATE_TEMPLATE = 'comment/comment_create.jinja2'


def logger():
    """Returns a logging.Logger object."""
    return logging.getLogger(__name__)


class CommentController(object):
    """ Main class for the comment handling. Includes
    methods for package, project and request comments

    """

    @classmethod
    def package_comment(cls, renderer, project, package, method, info,
                        comment=None, parent=None):
        """Method for package command handling"""
        global LIST_TEMPLATE
        query = {'apiurl': info.apiurl}
        pkg_comment_ctrl = PackageComment(project, package)
        result = getattr(pkg_comment_ctrl, method)(comment, parent, **query)
        if method == 'list':
            formated_comments = _format_for_output(result)
            if info.interactive:
                cls.shell(renderer, info.shell_cls, formated_comments,
                          pkg_comment_ctrl, info)
            renderer.render(LIST_TEMPLATE, comments=formated_comments)
        else:
            renderer.render(CREATE_TEMPLATE, status=result)

    @classmethod
    def project_comment(cls, renderer, project, method, info, comment=None,
                        parent=None):
        """Method for project command handling"""
        global LIST_TEMPLATE
        query = {'apiurl': info.apiurl}
        proj_comment_ctrl = ProjectComment(project)
        result = getattr(proj_comment_ctrl, method)(comment, parent,  **query)
        if method == 'list':
            formated_comments = _format_for_output(result)
            if info.interactive:
                cls.shell(renderer, info.shell_cls, formated_comments,
                          proj_comment_ctrl, info)
            renderer.render(LIST_TEMPLATE, comments=formated_comments)
        else:
            renderer.render(CREATE_TEMPLATE, status=result)

    @classmethod
    def request_comment(cls, renderer, request, method, info, comment=None,
                        parent=None):
        """Method for request command handling"""
        global LIST_TEMPLATE
        query = {'apiurl': info.apiurl}
        req_comment_ctrl = RequestComment(request)
        result = getattr(req_comment_ctrl, method)(comment, parent, **query)
        if method == 'list':
            formated_comments = _format_for_output(result)
            if info.interactive:
                cls.shell(renderer, info.shell_cls, formated_comments,
                          req_comment_ctrl, info)
            renderer.render(LIST_TEMPLATE, comments=formated_comments)
        else:
            renderer.render(CREATE_TEMPLATE, status=result)

    @classmethod
    def delete_comment(cls, renderer, comment_id, info):
        """Method for comment deletion"""
        query = {'apiurl': info.apiurl}
        del_comment_ctrl = DeleteComment(comment_id)
        result = del_comment_ctrl.delete(comment_id, **query)
        renderer.render(CREATE_TEMPLATE, status=result)

    @classmethod
    def shell(cls, renderer, shell_cls, comments, cmt_controller, info):
        """Interactive shell method"""
        sh = shell_cls(renderer)
        sh.run(comments, cmt_controller, info.apiurl)


class AbstractCommentShell(AbstractShell):
    """Represents an abstract comment shell."""

    def __init__(self, *args, **kwargs):
        """Constructs a new AbstractCommentShell object.

        *args and **kwargs are passed to the base class'
        __init__ method.

        """
        super(AbstractCommentShell, self).__init__(*args, **kwargs)
        self._comment = None

    def _augment_info(self, info):
        super(AbstractCommentShell, self)._augment_info(info)
        info.set('comment', self._comment)
        info.set('cid', self._cid)
        info.set('cmt_controller', self._cmt_controller)
        info.set('apiurl', self._apiurl)

    def run(self, comments, cmt_controller, apiurl):
        """Run the shell.

        comments is the ordered comments dict

        """
        self._cmt_controller = cmt_controller
        self._apiurl = apiurl
        self.clear()
        for cid, comment in comments.items():
            self._comment = comment
            self._cid = cid
            self.render(SHELL_TEMPLATE, cid=self._cid, com=self._comment)
            next_req = False
            while not next_req:
                try:
                    inp = self.prompt()
                    next_req = self._execute(inp)
                except SystemExit:
                    # argparse automatically exits when the
                    # help is requested
                    pass
                except ShellSyntaxError as e:
                    self._renderer.render_text(str(e))
                except KeyboardInterrupt as e:
                    msg = "Press to ctrl-D to exit"
                    self._renderer.render_text(msg)
                except HTTPError as e:
                    msg = "Error %s: %s" % (e.code, e.url)
                    self._renderer.render_text(msg)
            self.clear()


class CommentShellController(CommentController):

    def __init__(self):
        self.stats = {}

    def reply(self, shell, comment, cid, info, reply_text):
        """Reply to a comment"""
        query = {'apiurl': info.apiurl}
        cmt_controller = info.cmt_controller
        results = cmt_controller.create(reply_text, cid, **query)
        for result in results:
            print result

    def create(self, shell, comment, info, create_text):
        """Create a new comment"""
        query = {'apiurl': info.apiurl}
        cmt_controller = info.cmt_controller
        results = cmt_controller.create(create_text, None, **query)
        for result in results:
            print result

    def delete(self, shell, cid, info):
        """Delete comment"""
        query = {'apiurl': info.apiurl}
        cmt_controller = info.cmt_controller
        results = cmt_controller.delete(cid, **query)
        for result in results:
            print result

    def next(self):
        """Skips the current request."""
        return True


def _format_for_output(result):
    f_comments = collections.OrderedDict()
    level = 0
    """Order comments and write to an ordered dict"""
    comments = [(c, 0) for c in result.xpath('./comment[not(@parent)]')]
    while comments:
        comment, level = comments.pop(0)
        xpb = XPathBuilder(context_item=True)
        xp = xpb.comment[xpb.attr('parent') == comment.get('id')]
        children = result.xpath(xp.tostring())
        f_comments[comment.get('id')] = {'who': comment.get('who'),
                                         'when': comment.get('when'),
                                         'comment': comment,
                                         'level': level
                                         }
        for child in children:
            comments[:0] = [(child, level + 1)]
    return f_comments
