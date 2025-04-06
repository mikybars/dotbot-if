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
        cond = data.get('cond')

        if not cond:
            raise ValueError('Missing "cond" parameter for "if" directive')
        if not isinstance(cond, str):
            raise ValueError('"cond" parameter must be a string')

        stdout, stderr = self._get_streams()
        ret = subprocess.run(['bash', '-c', cond], stdout=stdout, stderr=stderr)
        is_met = ret.returncode == 0

        met_branch = data.get('met') or data.get('then') or None
        unmet_branch = data.get('unmet') or data.get('else') or None
        if (is_met and not met_branch) or (not is_met and not unmet_branch):
            return True

        return self._run_internal(met_branch if is_met else unmet_branch)

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
        return dispatcher.dispatch(data)

    def _get_streams(self):
        defaults = self._context.defaults().get('if', {})
        echo_stdout = defaults.get('stdout', self._default_stdout)
        echo_stderr = defaults.get('stderr', self._default_stderr)

        stdout = None if echo_stdout else subprocess.DEVNULL
        stderr = None if echo_stderr else subprocess.DEVNULL

        return stdout, stderr
