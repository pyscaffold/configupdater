![ConfigUpdater](gfx/banner-640x323.png){.align-center width="384px"
height="194px"}

|

The sole purpose of
[ConfigUpdater](https://configupdater.readthedocs.io/) is to easily
update an INI config file with no changes to the original file except
the intended ones. This means comments, the ordering of sections and
key/value-pairs as wells as their cases are kept as in the original
file. Thus ConfigUpdater provides complementary functionality to
Python\'s
[ConfigParser](https://docs.python.org/3/library/configparser.html)
which is primarily meant for reading config files and writing *new*
ones. Read more on how to use
[ConfigUpdater](https://configupdater.readthedocs.io/) in the
`usage page <usage>`{.interpreted-text role="ref"}.

# Features

The key differences to
[ConfigParser](https://docs.python.org/3/library/configparser.html) are:

-   minimal invasive changes in the update configuration file,
-   proper handling of comments,
-   only a single config file can be updated at a time,
-   the original case of sections and keys are kept,
-   control over the position of a new section/key

Following features are **deliberately not** implemented:

-   interpolation of values,
-   propagation of parameters from the default section,
-   conversions of values,
-   passing key/value-pairs with `default` argument,
-   non-strict mode allowing duplicate sections and keys.

!!! note
    ConfigUpdater is mainly developed for [PyScaffold](https://pyscaffold.org/).




# Indices and tables

-   `genindex`{.interpreted-text role="ref"}
-   `modindex`{.interpreted-text role="ref"}
-   `search`{.interpreted-text role="ref"}
