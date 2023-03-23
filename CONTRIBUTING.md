---
title: Contributing
---

ConfigUpdater is an open-source project and needs your help to improve.
If you experience bugs or in general issues, please file an issue report
on our [issue
tracker](https://github.com/pyscaffold/configupdater/issues). If you
also want to contribute code or improve the documentation it\'s best to
create a Pull Request (PR) on Github. Here is a short introduction how
it works.

# Code Contributions

## Submit an issue

Before you work on any non-trivial code contribution it\'s best to first
create an issue report to start a discussion on the subject. This often
provides additional considerations and avoids unnecessary work.

## Create an environment

Before you start coding we recommend to install
[Miniconda](https://docs.conda.io/en/latest/miniconda.html) which allows
to setup a dedicated development environment named `configupdater` with:

    conda create -n configupdater python=3 virtualenv pytest pytest-cov

Then activate the environment `configupdater` with:

    source activate configupdater

## Clone the repository

1.  [Create a Gitub account](https://github.com/join) if you do not
    already have one.

2.  Fork the [project
    repository](https://github.com/pyscaffold/configupdater/): click on
    the *Fork* button near the top of the page. This creates a copy of
    the code under your account on the GitHub server.

3.  Clone this copy to your local disk:

        git clone git@github.com:YourLogin/configupdater.git

4.  Run `python setup.py develop` to install `configupdater` into your
    environment.

5.  Install `pre-commit`:

        pip install pre-commit
        pre-commit install

    PyScaffold project comes with a lot of hooks configured to
    automatically help the developer to check the code being written.

6.  Create a branch to hold your changes:

        git checkout -b my-feature

    and start making changes. Never work on the main branch!

7.  Start your work on this branch. When you're done editing, do:

        git add modified_files
        git commit

    to record your changes in Git, then push them to GitHub with:

        git push -u origin my-feature

8.  Please check that your changes don\'t break any unit tests with:

        python setup.py test

    Don\'t forget to also add unit tests in case your contribution adds
    an additional feature and is not just a bugfix.

9.  Use [flake8](https://flake8.pycqa.org/) to check your code style.

10. Add yourself to the list of contributors in `AUTHORS.rst`.

11. Go to the web page of your ConfigUpdater fork, and click \"Create
    pull request\" to send your changes to the maintainers for review.
    Find more detailed information [creating a
    PR](https://help.github.com/articles/creating-a-pull-request/).
