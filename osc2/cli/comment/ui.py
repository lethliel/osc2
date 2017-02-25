"""Defines the comment command."""

from osc2.cli.cli import OscCommand, call
from osc2.cli.description import CommandDescription, Option
from osc2.cli.comment.comment import CommentController
from osc2.cli.comment.shell import CommentShell


class Comment(CommandDescription, OscCommand):
    """Show, create and delete comments."""
    cmd = 'comment'


class CommentList(CommandDescription, Comment):
    """List comments."""
    cmd = 'list'


class PackageCommentList(CommandDescription, CommentList):
    """List package comments.

    List all comments available for the package

    Example:
    osc2 comment list package api://project/package
    """
    cmd = 'package'
    args = 'api://project/package'
    func = call(CommentController.package_comment)
    func_defaults = {'method': 'list', 'shell_cls': CommentShell}
    opt_interactive = Option('i', 'interactive',
                             'start an interactive comment shell',
                             action='store_true')


class ProjectCommentList(CommandDescription, CommentList):
    """"List project comments.

    List all comments available for the project

    Example:
    osc2 comment list project api://project
    """
    cmd = 'project'
    args = 'api://project'
    func = call(CommentController.project_comment)
    func_defaults = {'method': 'list', 'shell_cls': CommentShell}
    opt_interactive = Option('i', 'interactive',
                             'start an interactive comment shell',
                             action='store_true')


class RequestCommentList(CommandDescription, CommentList):
    """"List request comments.

    List all comments available for the request

    Example:
    osc2 comment list request api://reqid
    """
    cmd = 'request'
    args = 'api://request'
    func = call(CommentController.request_comment)
    func_defaults = {'method': 'list'}
    func_defaults = {'method': 'list', 'shell_cls': CommentShell}
    opt_interactive = Option('i', 'interactive',
                             'start an interactive comment shell',
                             action='store_true')


class CommentCreate(CommandDescription, Comment):
    """Create comment."""
    cmd = 'create'


class CreateOptions(object):
    """Options valid for all subclasses"""
    opt_comment = Option('c', 'comment', 'specify a comment', required=True)
    opt_parent = Option('p', 'parent', 'specify a comment to reply to')
    func_defaults = {'method': 'create'}


class PackageCommentCreate(CreateOptions, CommandDescription, CommentCreate):
    """Create comment for the package

    If no parent is given it is a top level comment.

    Example:
    osc2 comment create package api://project/package -c comment
              -p parent_id
    """
    cmd = 'package'
    args = 'api://project/package'
    func = call(CommentController.package_comment)


class ProjectCommentCreate(CreateOptions, CommandDescription, CommentCreate):
    """Create comment for the project

    If no parent is given it is a top level comment.

    Example:
    osc2 comment create project api://project -c comment
              -p parent_id
    """
    cmd = 'project'
    args = 'api://project'
    func = call(CommentController.project_comment)


class RequestCommentCreate(CreateOptions, CommandDescription, CommentCreate):
    """Create comment for the request

    If no parent is given it is a top level comment.

    Example:
    osc2 comment create request api://reqid -c comment
              -p parent_id
    """
    cmd = 'request'
    args = 'api://request'
    func = call(CommentController.request_comment)


class RequestCommentDelete(CommandDescription, Comment):
    """Delete comment.

    Deletes comment with the given comment id.

    Example:
    osc2 comment delete api://comment

    """
    cmd = 'delete'
    args = 'api://comment_id'
    func = call(CommentController.delete_comment)
