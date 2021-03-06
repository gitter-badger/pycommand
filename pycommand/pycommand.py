'''Library / toolkit for creating command line programs with minimal effort.'''

# Copyright (c) 2013-2016, 2018  Benjamin Althues <benjamin@babab.nl>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from __future__ import absolute_import

__docformat__ = 'restructuredtext'
__author__ = "Benjamin Althues"
__copyright__ = "Copyright (C) 2013-2016, 2018  Benjamin Althues"
__version_info__ = (0, 4, 0, 'final', 0)
__version__ = '0.4.0'


from collections import OrderedDict
import getopt
import sys


class CommandExit(Exception):
    def __init__(self, val):
        self.err = val

    def __str__(self):
        return repr(self.err)


class OptionError(AttributeError):
    '''Options/Flags AttributeError exception'''


class dictobject(dict):
    '''A dictionary with getters by attribute, used for flags '''
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise OptionError("Option '{}' is not defined".format(name))


class CommandBase(object):
    '''Base class for (sub)commands'''

    usagestr = 'usage: command [options]'
    '''String. Usage synopsis'''

    description = ''
    '''String. Small description of subcommand'''

    optionList = {}
    '''Dictionary of options (as a tuple of 2-tuples).
    This will be transformed to an OrderedDict when initializing the object.

    Example::

        optionList = (
            ('help', ('h', False, 'show this help information')),
            ('dry-run', ('n', False,
                         'only print output without actually running')),

            # To specify that an option requires an argument
            # just add a string that describes it
            ('file', ('f', '<filename>', 'use specified file')),

            # Use an empty string to ommit short option
            ('debug', ('', False, 'show debug information')),
        )

    '''

    usageTextExtra = ''
    '''String. Optional extra usage information'''

    commands = {}
    '''Dictionary of commands and the callables they invoke.'''

    def __init__(self, argv=sys.argv[1:]):
        '''Initialize (sub)command object

        :Parameters:
            - `argv`: List of arguments. E.g. `sys.argv[1:]`
        '''

        # Instance vars
        self.error = None
        '''Thrown by GetoptError when parsing illegal arguments.'''

        self.flags = {}
        '''Dict of parsed options and corresponding arguments, if any.'''

        self.args = []
        '''List of parsed postional arguments'''

        self.parentFlags = {}
        '''Dict of registered `flags` of parent Command object.'''

        self.usage = ''
        '''String with usage information

        The string is compiled using the values found for
        `usagestr`, `description`, `optionList` and `usageTextExtra`.
        '''

        self.optionList = OrderedDict(self.optionList)

        # Local vars
        longopts = []
        padding = 0
        shortopts = ''

        # Calculate padding needed for option arguments in usage info
        for flag, val in self.optionList.items():
            optlen = len(flag) + 2
            optlen += 4 if val[0] else 0
            optlen += len(val[1]) + 1 if val[0] and val[1] else 0
            optlen += len(val[1]) + 1 if val[1] else 0
            padding = optlen if optlen > padding else padding

        # Create usage information and build dict of possible flags
        opthelp = ''
        for flag, val in self.optionList.items():
            spec = flag + '=' if val[1] else flag
            longopts.append(spec)
            self.flags.update({flag: None})

            if val[1]:
                flagstring_long = ('{flag}={argument}'
                                   .format(flag=flag, argument=val[1]))
                if val[0]:
                    flagstring_short = ('{flag} {argument}'
                                        .format(flag=val[0], argument=val[1]))
            else:
                flagstring_long = flag
                flagstring_short = val[0]

            if val[0]:
                shortopts += val[0] + ':' if val[1] else val[0]
                optline = ('-{short}, --{flag}'
                           .format(short=flagstring_short,
                                   flag=flagstring_long))
            else:
                optline = '--{flag}'.format(flag=flagstring_long)

            opthelp += ('{options:{padding}}  {desc}\n'
                        .format(options=optline, padding=padding, desc=val[2]))

        self.usage = self.usagestr
        if self.description:
            self.usage += '\n\n{desc}'.format(desc=self.description)
        if self.optionList:
            self.usage += '\n\nOptions:\n{opts}'.format(opts=opthelp)
        if self.usageTextExtra:
            self.usage += '\n{help}'.format(help=self.usageTextExtra)

        # Parse arguments and options
        try:
            opts, self.args = getopt.getopt(argv, shortopts, longopts)
        except getopt.GetoptError as err:
            self.error = err
            return  # Stop when an invalid option is parsed

        for opt in opts:
            # Compare each option with optionList and set values for flags
            for flag, val in self.optionList.items():
                if opt[0][1] != '-':
                    # Short tags
                    if opt[0][1] == val[0]:
                        if val[1]:
                            self.flags[flag] = opt[1]
                        else:
                            self.flags[flag] = True
                else:
                    # Long tags
                    if opt[0][2:] == flag:
                        if val[1]:
                            self.flags[flag] = opt[1]
                        else:
                            self.flags[flag] = True

        # Convert to dictobject to allow getting flags by attribute name
        self.flags = dictobject(self.flags)

    def run(self):
        if not self.args:
            print(self.usage)
            raise CommandExit(2)
        elif self.args[0] in self.commands:
            return self.commands[self.args[0]](argv=self.args[1:])
        else:
            print('error: command {cmd} does not exist'
                  .format(cmd=self.args[0]))
            raise CommandExit(1)

    def registerParentFlag(self, optionName, value):
        '''Register a flag of a parent command

        :Parameters:
            - `optionName`: String. Name of option
            - `value`: Mixed. Value of parsed flag`
        '''
        self.parentFlags.update({optionName: value})
        return self


def run_and_exit(command_class):
    '''A shortcut for reading from sys.argv and exiting the interpreter'''
    cmd = command_class(sys.argv[1:])
    if cmd.error:
        print('error: {0}'.format(cmd.error))
        sys.exit(1)
    else:
        sys.exit(cmd.run())
