"""Provides classes to access the comments route"""

from osc2.core import Osc
from osc2.util.xml import OscElement, fromstring
from lxml import etree


class CommentsElement(OscElement):
    def __iter__(self):
        return self.iterfind('comment')


class Status(OscElement):
    def __iter__(self):
        return self.iterfind('summary')


class Comments(object):
    def __init__(self, *args):
        self._path = self._get_path(*args)

    def _get_path(self, *args):
        """Build the path for the api"""
        path_base = 'comments/'
        return path_base + '/'.join(args)

    def list(self, gbg1, gbg2, **kwargs):
        """Returns the comments as xml"""
        request = Osc.get_osc().get_reqobj()
        f = request.get(self._path, **kwargs)
        comments = fromstring(f.read(), comments=CommentsElement)
        return comments

    def create(self, comment, parent, **kwargs):
        """Creates the comment and returns the status"""
        if parent is not None:
            kwargs['parent_id'] = parent
        request = Osc.get_osc().get_reqobj()
        f = request.post(self._path, data=str(comment), **kwargs)
        result = fromstring(f.read(), status=Status)
        return result

    def delete(self, comment_id, **kwargs):
        """Deletes the comment and returns the status"""
        request = Osc.get_osc().get_reqobj()
        path = 'comment/' + str(comment_id)
        f = request.delete(path, **kwargs)
        result = fromstring(f.read(), status=Status)
        return result


class PackageComment(Comments):
    """Represents a package comment"""
    def __init__(self, project, package):
        super(PackageComment, self).__init__('package', project, package)


class ProjectComment(Comments):
    """Represents a project comment"""
    def __init__(self, project):
        super(ProjectComment, self).__init__('project', project)


class RequestComment(Comments):
    """Represents a request comment"""
    def __init__(self, request):
        super(RequestComment, self).__init__('request', request)


class DeleteComment(Comments):
    def __init__(self):
        """Represents a delete comment"""
