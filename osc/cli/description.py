"""Provides classes and methods for defining commands in descriptive way.

The syntax for defining a command is similar to defining models in the django
framework (that's what inspired me).

Note: the CommandDescription classes must have "unique" names. In order to
achieve this chose a naming like this: <Command name><Subcommand name>. If
you specialize a command or subcommand use My<Command name> or
My<Command name><Subcommand name>. It will lead to errors/unexpected behaviour
if 2 classes from different modules have the same name.

"""

import textwrap

import argparse


def commands():
    """Returns a function attribute dict.

    The dict maps a class name to a list of CommandDescription
    classes (that is it maps a command to a list of subcommands).

    """
    if not hasattr(commands, 'subcmds'):
        commands.subcmds = {}
    return commands.subcmds


class SubcommandFilterMeta(type):
    """Determine the "parent" command for a CommandDescription subclass."""

    filter_cls = None

    def __new__(cls, name, bases, attrs):
        if name == 'CommandDescription':
            return super(SubcommandFilterMeta, cls).__new__(cls, name, bases,
                                                            attrs)
        if cls.filter_cls is None:
            raise ValueError('filter_cls must not be None')
        real_bases, parent_cmds, extends_cmd = cls._calculate_bases(bases)
        descr = super(SubcommandFilterMeta, cls).__new__(cls, name,
                                                         tuple(real_bases),
                                                         attrs)
        if extends_cmd:
            # replace with specialized description
            cls._replace_with_specialized(real_bases[0], descr)
        else:
            cls._append_subcommand(parent_cmds, descr)
        return descr

    @classmethod
    def _calculate_bases(cls, bases):
        """Calculates the real base and the parent command classes.

        bases is a list of base classes. A real base class is a base
        class which is used for inheritance and not for building a
        command <-> subcommand hierarchy (such a class is called
        parent command class).
        It returns the a triple: real_bases, parent_cmds, extends_cmd.
        extends_cmd is either True or False. True indicates that this
        command extends/specializes an (existing) command.

        A ValueError is raised if the class to be defined does not
        extends/specializes a command and cls.filter_cls is not part
        of the _direct_ inheritance hierarchy (this represents an
        invalid situation).

        """
        real_bases = []
        parent_cmds = []
        filter_subs = [base for base in bases
                       if issubclass(base, cls.filter_cls)]
        extends_cmd = (len(filter_subs) == 1
                       and not cls.filter_cls in filter_subs)
        # just a small sanity check: it makes no sense to extend multiple
        # commands
        if len(filter_subs) != 1 and not cls.filter_cls in filter_subs:
            raise ValueError('exactly one cmd can be extended')
        for base in bases:
            if (base.__name__ == cls.filter_cls.__name__
                or extends_cmd
                or not issubclass(base, cls.filter_cls)):
                real_bases.append(base)
            else:
                parent_cmds.append(base)
        return real_bases, parent_cmds, extends_cmd

    @classmethod
    def _replace_with_specialized(cls, base_cls, specialized_cls):
        """Replaces base_cls with specialized_cls in the commands mapping.

        base_cls is the base class of the specialized class
        specialized_cls.

        """
        name = base_cls.__name__
        for v in commands().itervalues():
            names = [base.__name__ for base in v]
            if name in names:
                i = names.index(name)
                v.pop(i)
                v.insert(i, specialized_cls)

    @classmethod
    def _append_subcommand(cls, parent_cmds, descr):
        """Appends descr to the subcommand list for each parent.

        parent_cmds is the list of parent classes. descr is
        the newly defined subcommand class. If descr.__name__
        is already present in a subcommand list no append is
        done.

        """
        for parent_cmd in parent_cmds:
            name = parent_cmd.__name__
            names = [s.__name__ for s in commands().setdefault(name, [])]
            if not descr.__name__ in names:
                commands()[name].append(descr)


class CommandDescription(object):
    # cannot use docstr here
    # Describe a command in a descriptive manner

    __metaclass__ = SubcommandFilterMeta

    args = None
    use_wc = False  # set to True if command is context sensitive
    cmd = None
    help_str = None
    func = None  # function/callable which should be executed
    func_defaults = None  # kwargs mapping for default params

    @classmethod
    def add_arguments(cls, parser):
        """Add arguments to the parser.

        The parser is an argparse.ArgumentParser (or subparser)
        instance.
        Additionally options and subcommands are added to the
        parser parser.

        """
        defaults = {'oargs': [], 'oargs_use_wc': cls.use_wc,
                    'func': cls.func, 'func_defaults': cls.func_defaults}
        if cls.args is not None:
            oargs = cls.args.split()
            defaults['oargs'] = oargs
            parser.set_defaults(**defaults)
            for arg in oargs:
                parser.add_argument(arg)
        elif cls.func is not None:
            # TODO: investigate why it does not work with a simple
            #       else
            parser.set_defaults(**defaults)
        cls._add_options(parser)
        cls._add_subcommands(parser)

    def _add_options(cls, parser):
        """Adds options to the parser parser."""
        for key in cls.__dict__.keys():
            if key.startswith('opt_'):
                opt = getattr(cls, key)
                parser.set_defaults(**opt.parse_info())
                parser.add_argument(*opt.options(), **opt.kwargs)

    def _add_subcommands(cls, parser):
        """Adds subcommands to the parser parser."""
        # add subcommands
        subcmds = commands().get(cls.__name__, [])
        if subcmds:
            subparsers = parser.add_subparsers()
            for sub_cls in subcmds:
                descr = sub_cls.description()
                kw = {'description': sub_cls.description(),
                      # keep indention and newlines in docstr
                      'formatter_class': argparse.RawDescriptionHelpFormatter}
                if sub_cls.help() is not None:
                    kw['help'] = sub_cls.help()
                subparser = subparsers.add_parser(sub_cls.cmd, **kw)
                sub_cls.add_arguments(subparser)

    @classmethod
    def description(cls):
        """Returns a description str or None."""
        if cls.__doc__ is None:
            return None
        return textwrap.dedent(cls.__doc__)

    @classmethod
    def help(cls):
        """Returns a help str or None.

        If cls.help_str is None it is tried to
        extract the first line from cls.description().

        """
        if cls.help_str is not None:
            return cls.help_str
        descr = cls.description()
        if descr is None:
            return None
        l = descr.splitlines()
        if l:
            return l[0]
        return None


SubcommandFilterMeta.filter_cls = CommandDescription


class Option(object):
    """Encapsulates data for an option."""

    def __init__(self, shortname, fullname, help='', oargs=None, **kwargs):
        """Creates a new Option object.

        shortname is the shortname and fullname the fullname of an
        option. The leading dash has to be ommitted.

        Keyword arguments:
        help -- an optional description for the option (default: '')
        **kwargs -- optional arguments argparse's add_argument method

        """
        self.name = fullname
        self.shortname = ''
        if shortname:
            self.shortname = '-' + shortname
        self.fullname = '--' + fullname
        kwargs['help'] = help
        self.kwargs = kwargs
        self.oargs = oargs
        if self.oargs is not None:
            self.kwargs.setdefault('metavar', oargs)

    def parse_info(self):
        """Returns a dict.

        The dict maps an option name to an oargs str.

        """
        if self.oargs is None:
            return {}
        oargs = self.oargs.split()
        k = "opt_oargs_%s" % self.name
        return {k: oargs}

    def options(self):
        """Returns tuple.

        Either the tuple just contains the fullname or
        shortname and fullname.

        """
        if self.shortname:
            return (self.shortname, self.fullname)
        return (self.fullname, )
