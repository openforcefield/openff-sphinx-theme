"""OpenFF Sphinx theme."""

import hashlib
import inspect
import os
import sys
from multiprocessing import Manager
from pathlib import Path
from typing import List, Optional
from xml.etree import ElementTree

import bs4
import sass
import slugify
from bs4 import BeautifulSoup
from css_html_js_minify.html_minifier import html_minify
from sass import SassColor
from sphinx.util import console, logging
import sphinx

from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions

ROOT_SUFFIX = "--page-root"


def setup(app):
    """Setup connects events to the sitemap builder"""
    app.connect("builder-inited", register_template_functions)
    app.connect("config-inited", set_default_settings)
    app.connect("env-get-outdated", register_outdated)
    app.connect("build-finished", postproc_html)
    app.connect("build-finished", compile_css)
    app.site_pages = []
    app.add_html_theme(
        "openff_sphinx_theme", os.path.join(html_theme_path()[0], "openff_sphinx_theme")
    )
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }


def set_default_settings(app, config):
    if not config.html_sidebars:
        config.html_sidebars["**"] = [
            "globaltoc.html",
            "localtoc.html",
            "searchbox.html",
        ]
    if config.html_permalinks_icon == "¶":
        config.html_permalinks_icon = "<i class='fas fa-link'></i>"


def compile_css(app, exception):
    """Compile Bulma SASS into CSS"""
    if exception is not None:
        return

    theme_path = Path(html_theme_path()[0]) / "openff_sphinx_theme"
    src = theme_path / "sass/site.sass"
    dest = Path(app.outdir) / "_static/site.css"

    if not dest.parent.exists():
        return

    accent_color = app.config["html_theme_options"].get(
        "color_accent", "openff-toolkit-blue"
    )
    accent_color = {
        "openff-blue": (1, 84, 128),
        "openff-toolkit-blue": (47, 158, 210),
        "openff-dataset-yellow": (240, 133, 33),
        "openff-evaluator-orange": (240, 58, 33),
        "aquamarine": (44, 218, 157),
        "lilac": (228, 183, 229),
        "amaranth": (164, 14, 76),
        "grape": (171, 146, 191),
        "violet": (141, 107, 148),
        "pink": (238, 66, 102),
        "pale-green": (238, 66, 102),
        "green": (4, 231, 98),
        "crimson": (214, 40, 57),
        "eggplant": (117, 79, 91),
        "turquoise": (45, 225, 194),
    }.get(accent_color, accent_color)

    if app.config["html_theme_options"].get("css_minify", False):
        output_style = "compressed"
        source_comments = False
    else:
        output_style = "expanded"
        source_comments = True

    css = sass.compile(
        filename=str(src),
        output_style=output_style,
        custom_functions={"accent_color": lambda: SassColor(*accent_color, 1)},
    )

    print(f"Writing compiled SASS to {console.colorize('blue', str(dest))}")

    with open(dest, "w") as f:
        print(css, file=f)


def register_outdated(app, env, added, changed, removed):
    if isinstance(app.builder, sphinx.builders.html.StandaloneHTMLBuilder):
        env.openff_docs_to_postproc = added | changed
    else:
        env.openff_docs_to_postproc = None
    return ()


def postproc_html(app, exception):
    """Prettify or minify the HTML, as well as wrap tables with .table-container"""
    if exception is not None:
        return

    target_files = app.env.openff_docs_to_postproc

    if target_files is None:
        return

    outdir = Path(app.outdir)

    minify = app.config["html_theme_options"].get("html_minify", False)
    prettify = app.config["html_theme_options"].get("html_prettify", False)
    last = -1
    npages = len(target_files)
    print(f"Post-processing {npages} HTML files")

    # TODO: Consider using parallel execution
    for i, doc in enumerate(target_files):
        try:
            page = outdir / app.builder.get_target_uri(doc)
        except sphinx.errors.NoUri as e:
            print(doc, "has no URI; skipping")
            continue

        if int(100 * (i / npages)) - last >= 25:
            last = int(100 * (i / npages))
            color_page = console.colorize("blue", str(page))
            msg = f"Post-processing files... [{last}%] {color_page}"
            print("\033[K", msg, sep="", end="\r")

        if not page.exists():
            print(page, "does not exist; skipping")
            continue

        with open(page, "r", encoding="utf-8") as content:
            soup = BeautifulSoup(content, "lxml")
            for table in soup.find_all("table"):
                container_attributes = {
                    "class": ["table-container"] + table.get("class", []),
                }
                if "table-container" not in table.parent.get("class", ()):
                    table.wrap(soup.new_tag("div", **container_attributes))

            if minify:
                html = html_minify(str(soup))
            elif prettify:
                html = soup.prettify()
            else:
                html = str(soup)

        with open(page, "w", encoding="utf-8") as content:
            content.write(html)

    msg = f"Post-processing files... [100%]"
    sys.stdout.write("\033[K" + msg + "\r")


def register_template_functions(app):
    config = app.config
    config.html_context = {**get_html_context(), **config.html_context}


def html_theme_path():
    return [os.path.dirname(os.path.abspath(__file__))]


def ul_to_list(node: bs4.element.Tag, fix_root: bool, page_name: str) -> List[dict]:
    out = []
    for child in node.find_all("li", recursive=False):
        if callable(child.isspace) and child.isspace():
            continue
        formatted = {}
        if child.a is not None:
            formatted["href"] = child.a["href"]
            formatted["contents"] = "".join(map(str, child.a.contents))
            if fix_root and formatted["href"] == "#" and child.a.contents:
                slug = slugify.slugify(page_name) + ROOT_SUFFIX
                formatted["href"] = "#" + slug
            formatted["current"] = "current" in child.a.get("class", [])
        if child.ul is not None:
            formatted["children"] = ul_to_list(child.ul, fix_root, page_name)
        else:
            formatted["children"] = []
        out.append(formatted)
    return out


def derender_toc(
    toc_text, fix_root=True, page_name: str = "md-page-root--link"
) -> List[dict]:
    nodes = []
    try:
        toc = BeautifulSoup(toc_text, features="html.parser")
        for child in toc.children:
            if callable(child.isspace) and child.isspace():
                continue
            if child.name == "p":
                nodes.append({"caption": "".join(map(str, child.contents))})
            elif child.name == "ul":
                nodes.extend(ul_to_list(child, fix_root, page_name))
            else:
                raise NotImplementedError
    except Exception as exc:
        logger = logging.getLogger(__name__)
        logger.warning(
            "Failed to process toctree_text\n" + str(exc) + "\n" + str(toc_text)
        )

    return nodes


# These final lines exist to give sphinx a stable str representation of
# this function across runs, and to ensure that the str changes
# if the source does.
derender_toc_src = inspect.getsource(derender_toc)
derender_toc_hash = hashlib.sha512(derender_toc_src.encode()).hexdigest()


class DerenderTocMeta(type):
    def __repr__(self):
        return f"derender_toc, hash: {derender_toc_hash}"

    def __str__(self):
        return f"derender_toc, hash: {derender_toc_hash}"


class DerenderToc(object, metaclass=DerenderTocMeta):
    def __new__(cls, *args, **kwargs):
        return derender_toc(*args, **kwargs)


def get_html_context():
    return {"derender_toc": DerenderToc}
