""" This is a modified version of ``notebook_sphinext.py``

The original was from: https://github.com/ngoldbaum/RunNotebook as of commit
a3097f50d5

Thanks for sharing.

This is the license for RunNotebook

Copyright (c) 2013 Nathan Goldbaum. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

   * Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.
   * Redistributions in binary form must reproduce the above
copyright notice, this list of conditions and the following disclaimer
in the documentation and/or other materials provided with the
distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import os
from os.path import basename
import glob
import io
import shutil

from sphinx.util.compat import Directive
from docutils import nodes
from docutils.parsers.rst import directives
from IPython.nbconvert import html, python
from runipy.notebook_runner import NotebookRunner

from IPython.nbformat import current

# Tell notebook runner how to handle SVG
NotebookRunner.MIME_MAP['image/svg+xml'] = 'svg'


MATHJAX_REFRESH = """\
<script type="text/javascript">
   init_mathjax = function() {
     if (window.MathJax) {
       // MathJax loaded
       MathJax.Hub.Config({
         tex2jax: {
           inlineMath: [ ['$','$'], ["\\(","\\)"] ],
           displayMath: [ ['$$','$$'], ["\\[","\\]"] ],
           processEscapes: true,
           processEnvironments: true
         },
         displayAlign: 'center',
         "HTML-CSS": {
           styles: {'.MathJax_Display': {"margin": 0}},
           linebreaks: { automatic: true }
         }
       });
       MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
     }
   }
   init_mathjax();
</script>
"""

def cellgen(nb, type=None):
    for ws in nb.worksheets:
        for cell in ws.cells:
            if type is None:
                yield cell
            elif cell.cell_type == type:
                yield cell


def clear_output(nb):
    for cell in cellgen(nb, 'code'):
        if hasattr(cell, 'prompt_number'):
            del cell['prompt_number']
        cell.outputs = []


class NotebookDirective(Directive):
    """Insert an evaluated notebook into a document

    This uses runipy and nbconvert to transform a path to an unevaluated notebook
    into html suitable for embedding in a Sphinx document.
    """
    required_arguments = 1
    optional_arguments = 0
    option_spec = {'otherfiles': directives.unchanged}
    final_argument_whitespace = True

    def run(self):
        # check if there are spaces in the notebook name
        nb_path = self.arguments[0]
        if ' ' in nb_path:
            raise ValueError(
                "Cannot have spaces in notebook file name '{0}'".format(
                    nb_path))
        # Get other files to copy to build directory
        otherfiles = self.options.get('otherfiles', '')
        if otherfiles == '':
            otherfiles = []
        else:
            otherfiles = [fn.strip() for fn in otherfiles.split(',')]
        # check if raw html is supported
        if not self.state.document.settings.raw_enabled:
            raise self.warning('"%s" directive disabled.' % self.name)

        # get path to notebook
        nb_basename = os.path.basename(nb_path)
        rst_file = self.state_machine.document.attributes['source']
        rst_dir = os.path.abspath(os.path.dirname(rst_file))
        nb_abs_path = os.path.join(rst_dir, nb_basename)

        # Move files around.
        rel_dir = os.path.relpath(rst_dir, setup.confdir)
        dest_dir = os.path.join(setup.app.builder.outdir, rel_dir)
        dest_path = os.path.join(dest_dir, nb_basename)

        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        # Make unevaluated version
        with io.open(nb_abs_path, 'r') as f:
            nb = current.read(f, 'json')
        clear_output(nb)
        with io.open(dest_path, 'w') as f:
            current.write(nb, f, 'ipynb')
        # Copy any other needed files
        for fn in otherfiles:
            shutil.copy2(fn, dest_dir)

        dest_path_eval = dest_path.replace('.ipynb', '_evaluated.ipynb')
        dest_path_script = dest_path.replace('.ipynb', '.py')

        # Create python script version
        script_text = nb_to_python(nb_abs_path)
        f = open(dest_path_script, 'w')
        f.write(script_text.encode('utf8'))
        f.close()

        try:
            evaluated_text = evaluate_notebook(nb_abs_path, dest_path_eval)
        except Exception as err:
            raise RuntimeError("{0} in notebook {1}".format(err, nb_path))

        # create notebook node
        attributes = {'format': 'html', 'source': 'nb_path'}
        nb_node = notebook_node('', evaluated_text, **attributes)
        (nb_node.source, nb_node.line) = \
            self.state_machine.get_source_and_line(self.lineno)

        # add dependency
        self.state.document.settings.record_dependencies.add(nb_abs_path)

        # clean up png files left behind by notebooks.
        png_files = glob.glob("*.png")
        fits_files = glob.glob("*.fits")
        h5_files = glob.glob("*.h5")
        for file in png_files:
            os.remove(file)

        # Put links underneath notebook
        para = nodes.paragraph('', '')
        new_nodes = []
        for fname in (dest_path, dest_path_eval, dest_path_script):
            fn = basename(fname)
            new_nodes.append(nodes.reference('', fn, refuri = fn))
        # Separate with separator
        para.extend(list_join(nodes.Text('; '), new_nodes))
        return [nb_node] + [para]


def list_join(spacer, in_list):
    new_list = []
    last_i = len(in_list) - 1
    for i, val in enumerate(in_list):
        new_list.append(val)
        if i != last_i:
            new_list.append(spacer)
    return new_list


class notebook_node(nodes.raw):
    pass

def nb_to_python(nb_path):
    """convert notebook to python script"""
    exporter = python.PythonExporter()
    output, resources = exporter.from_filename(nb_path)
    return output


def nb_to_html(nb_path):
    """convert notebook to html

    This html will get embedded in another html page, so we need to strip out
    stuff that would interfere with the parent page's formatting.
    """
    exporter = html.HTMLExporter(template_file='full')
    output, resources = exporter.from_filename(nb_path)
    header = output.split('<head>', 1)[1].split('</head>',1)[0]
    body = output.split('<body>', 1)[1].split('</body>',1)[0]

    # http://imgur.com/eR9bMRH
    header = header.replace('<style', '<style scoped="scoped"')
    header = header.replace('body{background-color:#ffffff;}\n', '')
    header = header.replace('body{background-color:white;position:absolute;'
                            'left:0px;right:0px;top:0px;bottom:0px;'
                            'overflow:visible;}\n', '')
    header = header.replace('body{margin:0;'
                            'font-family:"Helvetica Neue",Helvetica,Arial,'
                            'sans-serif;font-size:13px;line-height:20px;'
                            'color:#000000;background-color:#ffffff;}', '')
    header = header.replace('\na{color:#0088cc;text-decoration:none;}', '')
    header = header.replace(
        'a:focus{color:#005580;text-decoration:underline;}', '')
    header = header.replace(
        '\nh1,h2,h3,h4,h5,h6{margin:10px 0;font-family:inherit;font-weight:bold;'
        'line-height:20px;color:inherit;text-rendering:optimizelegibility;}'
        'h1 small,h2 small,h3 small,h4 small,h5 small,'
        'h6 small{font-weight:normal;line-height:1;color:#999999;}'
        '\nh1,h2,h3{line-height:40px;}\nh1{font-size:35.75px;}'
        '\nh2{font-size:29.25px;}\nh3{font-size:22.75px;}'
        '\nh4{font-size:16.25px;}\nh5{font-size:13px;}'
        '\nh6{font-size:11.049999999999999px;}\nh1 small{font-size:22.75px;}'
        '\nh2 small{font-size:16.25px;}\nh3 small{font-size:13px;}'
        '\nh4 small{font-size:13px;}', '')
    header = header.replace('background-color:#ffffff;', '', 1)
    # Script to force mathjax refresh - from nbviewer output
    header += MATHJAX_REFRESH
    # concatenate raw html lines
    lines = ['<div class="ipynotebook">']
    lines.append(header)
    lines.append(body)
    lines.append('</div>')
    return '\n'.join(lines)


def evaluate_notebook(nb_path, dest_path=None):
    # Create evaluated version and save it to the dest path.
    nb_runner = NotebookRunner(nb_in=nb_path)
    nb_runner.run_notebook()
    if dest_path is None:
        dest_path = 'temp_evaluated.ipynb'
    nb_runner.save_notebook(dest_path)
    ret = nb_to_html(dest_path)
    if dest_path is 'temp_evaluated.ipynb':
        os.remove(dest_path)
    return ret


def formatted_link(path):
    base = os.path.basename(path)
    return ":download:`%s`" % (base,)


def visit_notebook_node(self, node):
    self.visit_raw(node)


def depart_notebook_node(self, node):
    self.depart_raw(node)


def setup(app):
    setup.app = app
    setup.config = app.config
    setup.confdir = app.confdir

    app.add_node(notebook_node,
                 html=(visit_notebook_node, depart_notebook_node))

    app.add_directive('notebook', NotebookDirective)
