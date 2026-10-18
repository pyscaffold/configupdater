============
Contributing
============

ConfigUpdater is an open-source project and needs your help to improve.
If you experience bugs or in general issues, please file an
issue report on our `issue tracker`_. If you also want to contribute code
or improve the documentation it's best to create a Pull Request (PR) on
Github. Here is a short introduction how it works.


Code Contributions
==================

Submit an issue
---------------

Before you work on any non-trivial code contribution it's best to first create
an issue report to start a discussion on the subject. This often provides
additional considerations and avoids unnecessary work.

Create an environment
---------------------

ConfigUpdater requires Python 3.11 or newer. The development environment is
managed with uv_, so install it first. uv also downloads a suitable Python
version if you don't have one.

Clone the repository
--------------------

#. `Create a Github account`_  if you do not already have one.
#. Fork the `project repository`_: click on the *Fork* button near the top of the
   page. This creates a copy of the code under your account on the GitHub server.
#. Clone this copy to your local disk::

    git clone git@github.com:YourLogin/configupdater.git

#. Create a virtual environment in ``.venv`` with ``configupdater`` and all
   development tools (pytest, mypy, tox, pre-commit)::

    uv sync

#. Install the ``pre-commit`` hooks::

    uv run pre-commit install

   The hooks automatically check the code you are writing on every commit.

#. Create a branch to hold your changes::

    git checkout -b my-feature

   and start making changes. Never work on the main branch!

#. Start your work on this branch. When you’re done editing, do::

    git add modified_files
    git commit

   to record your changes in Git, then push them to GitHub with::

    git push -u origin my-feature

#. Please check that your changes don't break any unit tests with::

    uv run tox

   or, for a quick run without coverage, ``uv run pytest``.

   Don't forget to also add unit tests in case your contribution
   adds an additional feature and is not just a bugfix.

#. The ``pre-commit`` hooks check your code style with `ruff`_ on every commit.
   You can also run them on all files with ``uv run tox -e lint``, and check the
   type hints with ``uv run tox -e typecheck``.
#. Add yourself to the list of contributors in ``AUTHORS.rst``.
#. Go to the web page of your ConfigUpdater fork, and click
   "Create pull request" to send your changes to the maintainers for review.
   Find more detailed information `creating a PR`_.


.. _PyPI: https://pypi.python.org/
.. _project repository: https://github.com/pyscaffold/configupdater/
.. _Git: https://git-scm.com/
.. _uv: https://docs.astral.sh/uv/getting-started/installation/
.. _issue tracker: https://github.com/pyscaffold/configupdater/issues
.. _Create a Github account: https://github.com/join
.. _creating a PR: https://help.github.com/articles/creating-a-pull-request/
.. _ruff: https://docs.astral.sh/ruff/
