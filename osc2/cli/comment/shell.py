"""Defines commands for the interactive comments shell."""

from osc2.cli.description import build_description, Option
from osc2.cli.cli import call
from osc2.cli.comment.comment import (CommentShellController,
                                      AbstractCommentShell)

ShellCommand = build_description('ShellCommand', {})


class CommentShellUI(ShellCommand):
    """Interactive comment shell."""
    controller = CommentShellController()


class ReplyComment(ShellCommand, CommentShellUI):
    """Reply to comment.

    Example:
    reply COMMENT

    """
    cmd = 'reply'
    args = 'reply_text'
    func = call(CommentShellUI.controller.reply)


class CreateComment(ShellCommand, CommentShellUI):
    """Create comment.

    Example:
    create COMMENT

    """
    cmd = 'create'
    args = 'create_text'
    func = call(CommentShellUI.controller.create)


class DeleteComment(ShellCommand, CommentShellUI):
    """Delete comment.

    Example:
    delete

    """
    cmd = 'delete'
    func = call(CommentShellUI.controller.delete)


class CommentNext(ShellCommand, CommentShellUI):
    """View next comment.

    Example:
    next

    """
    cmd = 'next'
    func = call(CommentShellUI.controller.next)


class CommentShell(AbstractCommentShell):
    """Represents a comment shell."""
    def _root_cmd_cls(self):
        return CommentShellUI
