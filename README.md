<div align="center">
<img src="https://raw.githubusercontent.com/pyscaffold/configupdater/master/docs/gfx/banner-640x323.png" alt="Configupdater logo" width="500" role="img">
</div>
<br/>

|         |                                    |
|---------|------------------------------------|
| CI/CD   | [![Tests][Tests-image]][Tests-link] [![Coverage][Coverage-image]][Coverage-link] [![Publish Package][Publish-image]][Publish-link] [![GitHub Sponsors][sponsor-image]][sponsor-link]  |
| Package | [![PyPI - Version][PyPI_ver-image]][PyPI_ver-link] [![Conda - Version][Conda-image]][Conda-link] [![PyPI - Downloads][PyPI_down-image]][PyPI_down-link] [![PyPI - Python Version][PyPI_py-image]][PyPI_py-link] |
| Details | [![Setuptools project][setuptools-image]][setuptools-link] [![Linting - Ruff][ruff-image]][ruff-link] [![test - pytest][pytest-image]][pytest-link] [![Pre-Commit][precommit-image]][precommit-link] [![Types - Mypy][mypy-image]][mypy-link] [![License - MIT][MIT-image]][MIT-link] [![Docs - RTD][rtd-image]][rtd-link] |

The sole purpose of [ConfigUpdater] is to easily
update an INI config file with no changes to the original file except
the intended ones. This means comments, the ordering of sections and
key/value-pairs as wells as their cases are kept as in the original
file. Thus ConfigUpdater provides complementary functionality to
Python\'s [ConfigParser], which is primarily meant for reading config
files and writing *new* ones.

# Features

The key differences to [ConfigParser] are:

- minimal invasive changes in the update configuration file,
- proper handling of comments,
- only a single config file can be updated at a time,
- the original case of sections and keys are kept,
- control over the position of a new section/key

Following features are **deliberately not** implemented:

- interpolation of values,
- propagation of parameters from the default section,
- conversions of values,
- passing key/value-pairs with `default` argument,
- non-strict mode allowing duplicate sections and keys.

# Usage

First install the package with either:

```console
pip install configupdater
```

or:

```console
conda install -c conda-forge configupdater
```

Now we can simply do:

```python
from configupdater import ConfigUpdater

updater = ConfigUpdater()
updater.read("setup.cfg")
```

which would read the file `setup.cfg` that is found in many projects.

To change the value of an existing key we can simply do:

```python
updater["metadata"]["author"].value = "Alan Turing"
```

At any point we can print the current state of the configuration file
with:

```python
print(updater)
```

To update the read-in file just call `updater.update_file()` or
`updater.write(open('filename','w'))` to write the changed configuration
file to another destination. Before actually writing, ConfigUpdater will
automatically check that the updated configuration file is still valid
by parsing it with the help of ConfigParser.

Many of ConfigParser\'s methods still exists and it\'s best to look them
up in the [module reference]. Let\'s look at some examples.

## Adding and removing options

Let\'s say we have the following configuration in a string:

```python
cfg = """
[metadata]
author = Ada Lovelace
summary = The Analytical Engine
"""
```

We can add an *license* option, i.e. a key/value pair, in the same way
we would do with ConfigParser:

```python
updater = ConfigUpdater()
updater.read_string(cfg)
updater["metadata"]["license"] = "MIT"
```

A simple `print(updater)` will give show you that the new option was
appended to the end:

```ini
[metadata]
author = Ada Lovelace
summary = The Analytical Engine
license = MIT
```

Since the license is really important to us let\'s say we want to add it
before the `summary` and even add a short comment before it:

```python
updater = ConfigUpdater()
updater.read_string(cfg)
(
    updater["metadata"]["summary"]
    .add_before.comment("Ada would have loved MIT")
    .option("license", "MIT")
)
```

which would result in:

```ini
[metadata]
author = Ada Lovelace
# Ada would have loved MIT
license = MIT
summary = Analytical Engine calculating the Bernoulli numbers
```

Using `add_after` would give the same result and looks like:

```python
updater = ConfigUpdater()
updater.read_string(cfg)
(
    updater["metadata"]["author"]
    .add_after.comment("Ada would have loved MIT")
    .option("license", "MIT")
)
```

Let\'s say we want to rename [summary]{.title-ref} to the more common
\`description\`:

```python
updater = ConfigUpdater()
updater.read_string(cfg)
updater["metadata"]["summary"].key = "description"
```

If we wanted no summary at all, we could just do
`del updater["metadata"]["summary"]`.

## Adding and removing sections

Adding and remove sections just works like adding and removing options
but on a higher level. Sticking to our *Ada Lovelace* example, let\'s
say we want to add a section `options` just before `metadata` with a
comment and two new lines to separate it from `metadata`:

```python
updater = ConfigUpdater()
updater.read_string(cfg)
(
    updater["metadata"]
    .add_before.section("options")
    .comment("Some specific project options")
    .space(2)
)
```

As expected, this results in:

```ini
[options]
# Some specific project options


[metadata]
author = Ada Lovelace
summary = The Analytical Engine
```

We could now fill the new section with options like we learnt before. If
we wanted to rename an existing section we could do this with the help
of the `name` attribute:

```python
updater["metadata"].name = "MetaData"
```

Sometimes it might be useful to inject a new section not in a
programmatic way but more declarative. Let\'s assume we have thus
defined our new section in a multi-line string:

```python
sphinx_sect_str = """
[build_sphinx]
source_dir = docs
build_dir = docs/_build
"""
```

With the help of two ConfigUpdater objects we can easily inject this
section into our example:

```python
sphinx = ConfigUpdater()
sphinx.read_string(sphinx_sect_str)
sphinx_sect = sphinx["build_sphinx"]

updater = ConfigUpdater()
updater.read_string(cfg)

(updater["metadata"].add_after.space().section(sphinx_sect.detach()))
```

The `detach` method will remove the `build_sphinx` section from the
first object and add it to the second object. This results in:

```ini
[metadata]
author = Ada Lovelace
summary = The Analytical Engine

[build_sphinx]
source_dir = docs
build_dir = docs/_build
```

Alternatively, if you want to preserve `build_sphinx` in both
`ConfigUpdater` objects (i.e., prevent it from being removed from the
first while still adding a copy to the second), you call also rely on
stdlib\'s `copy.deepcopy` function instead of `detach`:

```python
from copy import deepcopy

(updater["metadata"].add_after.space().section(deepcopy(sphinx_sect)))
```

This technique can be used for all objects inside ConfigUpdater:
sections, options, comments and blank spaces.

Shallow copies are discouraged in the context of ConfigUpdater because
each configuration block keeps a reference to its container to allow
easy document editing. When doing editions (such as adding or changing
options and comments) based on a shallow copy, the results can be
unreliable and unexpected.

For more examples on how the API of ConfigUpdater works it\'s best to
take a look into the [unit tests] and read the references.

# Notes

ConfigUpdater was mainly developed for [PyScaffold].

[ConfigUpdater]: https://configupdater.readthedocs.io/
[ConfigParser]: https://docs.python.org/3/library/configparser.html
[PyScaffold]: https://pyscaffold.org/
[module reference]: https://configupdater.readthedocs.io/en/latest/api.html#configupdater.configupdater.ConfigUpdater
[unit tests]: https://github.com/pyscaffold/configupdater/blob/main/tests/test_configupdater.py

[Tests-image]: https://api.cirrus-ci.com/github/pyscaffold/configupdater.svg?branch=main
[Tests-link]: https://cirrus-ci.com/github/pyscaffold/configupdater
[Coverage-image]: https://img.shields.io/coveralls/github/pyscaffold/configupdater/main.svg
[Coverage-link]: https://coveralls.io/r/pyscaffold/configupdater
[Publish-image]: https://github.com/pyscaffold/configupdater/actions/workflows/publish-package.yml/badge.svg
[Publish-link]: https://github.com/pyscaffold/configupdater/actions/workflows/publish-package.yml
[PyPI_ver-image]:https://img.shields.io/pypi/v/configupdater.svg?logo=pypi&label=PyPI&logoColor=gold
[PyPI_ver-link]: https://pypi.org/project/configupdater/
[Conda-image]: https://img.shields.io/conda/vn/conda-forge/configupdater.svg?logo=Anaconda&label=Conda-Forge&logoColor=44A833
[Conda-link]: https://anaconda.org/conda-forge/configupdater/
[PyPI_down-image]: https://img.shields.io/pypi/dm/configupdater.svg?color=blue&label=Downloads&logo=pypi&logoColor=gold
[PyPI_down-link]: https://pepy.tech/project/configupdater
[PyPI_py-image]: https://img.shields.io/pypi/pyversions/configupdater.svg?logo=python&label=Python&logoColor=gold
[PyPI_py-link]: https://pypi.org/project/configupdater/
[setuptools-image]: https://img.shields.io/badge/-setuptools-E5B62F?logo=python
[setuptools-link]: https://github.com/pypa/setuptools
[ruff-image]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
[ruff-link]: https://github.com/charliermarsh/ruff
[mypy-image]: https://img.shields.io/badge/Types-mypy-blue.svg
[mypy-link]: https://mypy-lang.org/
[pytest-image]: https://img.shields.io/static/v1?label=‎&message=Pytest&logo=Pytest&color=0A9EDC&logoColor=white
[pytest-link]:  https://docs.pytest.org/
[rtd-image]: https://readthedocs.org/projects/pyscaffold/badge/?version=latest
[rtd-link]: https://configupdater.readthedocs.io/
[precommit-image]: https://img.shields.io/static/v1?label=‎&message=pre-commit&logo=pre-commit&color=76877c
[precommit-link]: https://pre-commit.com/
[MIT-image]: https://img.shields.io/badge/License-MIT-9400d3.svg
[MIT-link]: LICENSE.txt
[sponsor-image]: https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=ff69b4
[sponsor-link]: https://github.com/sponsors/FlorianWilhelm
