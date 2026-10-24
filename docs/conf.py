"""Sphinx configuration, see https://www.sphinx-doc.org/en/master/usage/configuration.html

The package must be installed (``uv run tox -e docs`` and Read the Docs do that), so
autodoc imports the same code that is shipped.
"""

import os
from datetime import date
from importlib.metadata import version as get_version

# -- Project information -----------------------------------------------------

project = "ConfigUpdater"
author = "Florian Wilhelm"
copyright = f"2018-{date.today().year}, {author}"
release = get_version(project)
version = ".".join(release.split(".")[:2])

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinxcontrib.googleanalytics",
]

root_doc = "index"
exclude_patterns = ["_build", "html", "Thumbs.db", ".DS_Store"]

autodoc_default_options = {
    "members": True,
    "inherited-members": True,
    "show-inheritance": True,
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pyscaffold": ("https://pyscaffold.org/en/stable", None),
}

# Don't copy the prompts of interactive examples
copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True

# -- HTML output -------------------------------------------------------------

html_theme = "furo"
html_title = f"ConfigUpdater {version}"
html_logo = "gfx/configupdater_plain.svg"
html_favicon = "gfx/favicon.ico"
html_static_path = ["_static"]
html_theme_options = {
    "sidebar_hide_name": True,  # the logo already shows it
    "source_repository": "https://github.com/pyscaffold/configupdater/",
    "source_branch": "main",
    "source_directory": "docs/",
}

# Google Analytics 4, only on Read the Docs, so local builds don't send any data
googleanalytics_id = "G-P7XJCP7XJ7"
googleanalytics_enabled = os.environ.get("READTHEDOCS") == "True"
