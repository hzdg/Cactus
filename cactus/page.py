import os
import codecs
import logging

from .utils import parseValues
from cactus.config import Config

from django.template import Template, Context, loader  # needs to be imported
                                                       # even if not used


class Page(object):

    def __init__(self, site, path):
        self.site = site
        self.path = path

        self.config = Config(self.site.paths['config'])

        self.paths = {
            'full': os.path.join(self.site.path, 'pages', self.path),
            'build': os.path.join('build', self.path),
            'full-build': os.path.join(site.path, 'build', self.path),
        }

    @property
    def data(self):
        f = codecs.open(self.paths['full'], 'r', 'utf-8')
        data = f.read()
        f.close()
        return data

    @property
    def context(self):
        """
        The page context.
        """
        context = {}

        # Site context
        context = self.site._contextCache

        # Page context (parse header)
        context.update(parseValues(self.data)[0])

        context.update(self.config.get('extra_context'))
        return Context(context)

    def render(self):
        """
        Takes the template data with context and renders it to the final output file.
        """

        data = parseValues(self.data)[1]
        context = self.context

        # Run the prebuild plugins, we can't use the standard method here because
        # plugins can chain-modify the context and data.
        for plugin in self.site._plugins:
            if hasattr(plugin, 'preBuildPage'):
                context, data = plugin.preBuildPage(self.site, self, context, data)

        return Template(data).render(context)

    def build(self):
        """
        Save the rendered output to the output file.
        """
        logging.info("Building %s", self.path)

        data = self.render()

        # Make sure a folder for the output path exists
        try: os.makedirs(os.path.dirname(self.paths['full-build']))
        except OSError: pass

        # Write the data to the output file
        f = codecs.open(self.paths['full-build'], 'w', 'utf-8')
        f.write(data)
        f.close()

        # Run all plugins
        self.site.pluginMethod('postBuildPage', self.site, self.paths['full-build'])
