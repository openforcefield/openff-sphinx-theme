"""
Run in PyCharm with two additional argument

/path/to/docs /path/to/docs/_build

"""
# -*- coding: utf-8 -*-
import re
import sys

from sphinx.cmd.build import main

if __name__ == "__main__":
    sys.argv[0] = re.sub(r"(-script\.pyw?|\.exe)?$", "", sys.argv[0])
    sys.exit(main())