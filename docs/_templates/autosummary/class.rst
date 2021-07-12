{{ fullname | escape | underline}}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
    :no-members:
    :no-inherited-members:
    :no-special-members:
    :no-undoc-members:

{% block methods %}

.. rst-class:: imitate-nested-in-previous-deflist

.. rst-class:: hide-header

``__init__``
------------

.. rst-class:: autosummary-child-object

.. automethod:: {{ objname }}.__init__

{% if methods %}

.. rst-class:: imitate-nested-in-previous-deflist

Methods
-------

.. autosummary::
{% for item in methods %}
    ~{{ name }}.{{ item }}
{%- endfor %}

{% for item in methods %}
{% if not item.startswith('_') %}

.. rst-class:: hide-header

{{ ('``' ~ item ~ '``') | underline(line='*') }}

.. rst-class:: autosummary-child-object

.. automethod:: {{ objname }}.{{ item }}

{% endif %}
{% endfor %}

{% endif %}
{% endblock %}

{% block attributes %}
{% if attributes %}

.. rst-class:: imitate-nested-in-previous-deflist

Attributes
----------

.. autosummary::
{% for item in attributes %}
    ~{{ name }}.{{ item }}
{%- endfor %}

{% for item in attributes %}
{% if not item.startswith('_') %}

.. rst-class:: hide-header

{{ ('``' ~ item ~ '``') | underline(line='*') }}

.. rst-class:: autosummary-child-object

.. autoattribute:: {{ objname }}.{{ item }}

{% endif %}
{% endfor %}

{% endif %}
{% endblock %}
