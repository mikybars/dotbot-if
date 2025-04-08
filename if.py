import glob
import os
import subprocess

import dotbot
from dotbot.dispatcher import Dispatcher
from dotbot.util import module


class If(dotbot.Plugin):
    _directive = 'if'

    _default_stdout = True
    _default_stderr = True

    def can_handle(self, directive):
        return directive == self._directive

    def handle(self, directive, data):
        if directive != self._directive:
            raise ValueError(f'Cannot handle this directive {directive}')

        if isinstance(data, list):
            return all(self._handle_single_if(d) for d in data)

        return self._handle_single_if(data)

    def _handle_single_if(self, data):
        cond = self._get_cond_arg(**{'cond': data.get('cond')})
        not_cond = self._get_cond_arg(**{'not': data.get('not')})

        if not cond and not not_cond:
            raise ValueError('Missing "cond" or "not" parameter for "if" directive')

        stdout, stderr = self._get_streams()
        ret = subprocess.run(['bash', '-c', cond or not_cond], stdout=stdout, stderr=stderr)
        is_met = ret.returncode == 0 if cond else ret.returncode != 0

        met_branch = data.get('met') or data.get('then') or None
        unmet_branch = data.get('unmet') or data.get('else') or None
        if is_met and met_branch:
            return self._run_internal(met_branch)
        if not is_met and unmet_branch:
            return self._run_internal(unmet_branch)

        return True

    def _get_cond_arg(self, **kwargs):
        [(param, value)] = kwargs.items()

        if value is None:
            return None

        if isinstance(value, list) and len(value) != 2:
            raise ValueError(f'"{param}" must be of the form [description, command]')
        if not isinstance(value, list) and not isinstance(value, str):
            raise ValueError(f'"{param}" parameter must be a string or a list')

        if isinstance(value, list):
            return value[1]
        return value

    def _load_plugins(self):
        plugin_paths = self._context.options().plugins
        plugins = []
        for dir in self._context.options().plugin_dirs:
            for path in glob.glob(os.path.join(dir, '*.py')):
                plugin_paths.append(path)
        for path in plugin_paths:
            abspath = os.path.abspath(path)
            plugins.extend(module.load(abspath))
        if not self._context.options().disable_built_in_plugins:
            from dotbot.plugins import Clean, Create, Link, Shell
            plugins.extend([Clean, Create, Link, Shell])
        return plugins

    def _run_internal(self, data):
        dispatcher = Dispatcher(
            self._context.base_directory(),
            only=self._context.options().only,
            skip=self._context.options().skip,
            options=self._context.options(),
            plugins=self._load_plugins(),
        )
        return dispatcher.dispatch([{'defaults': self._context.defaults()}] + data)

    def _get_streams(self):
        defaults = self._context.defaults().get('if', {})
        echo_stdout = defaults.get('stdout', self._default_stdout)
        echo_stderr = defaults.get('stderr', self._default_stderr)

        stdout = None if echo_stdout else subprocess.DEVNULL
        stderr = None if echo_stderr else subprocess.DEVNULL

        return stdout, stderr
