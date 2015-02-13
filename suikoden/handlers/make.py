from contextlib import contextmanager
from subprocess import check_output
from sys import stdout
import os

from tabulate import tabulate

from ..handler import Handler


run = lambda cmd: stdout.write(str(check_output(cmd, shell=True), encoding='utf-8'))


class MakefileHandler(Handler):
    """Ha ha. Now due to your exacting demands you must specify the port format!"""
    whitelist = ['app']

    filename = "Makefile.appconfig"
    template = "BIND = {}".format

    def __init__(self, *args, **kwargs):
        super(MakefileHandler, self).__init__(*args, **kwargs)
        # Always redeploy them.
        self.apps = []
        self.names = []

    def add(self, app):
        self.names.append(app.get("name"))
        self.apps.append(app)

    def flush(self):
        for app in self.apps:
            self.log("Writing Makefile for {}".format(app.get("name")))
            content = self.template(app.get("port-format").format(app.get("port")))
            path = os.path.join(os.path.expanduser(app.get("path")), self.filename)
            with open(path, 'w') as file:
                file.write(content)

    def list_apps(self):
        print("Registered applications:")

        display_rows = [
            (app.get("name"),
             app.get("external-name") if app.get("external-name") else app.get("dns-name") if app.get("dns-name") else "[internal]",
             app.get("port"),
             app.get("path")
            ) for app in self.apps
        ]

        print(tabulate(display_rows, headers=('Name', 'Server Name', 'Port', 'Path')))

    def start_apps(self):
        @contextmanager
        def indir(dir):
            old = os.getcwd()
            os.chdir(dir)
            yield
            os.chdir(old)

        for app in self.apps:
            with indir(app.get("path")):
                print("Starting {}".format(app.get("name")))
                run("make")
