##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2018 Université catholique de Louvain (http://www.uclouvain.be)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    A copy of this license - GNU General Public License - is available
#    at the root of the source code of this program.  If not,
#    see http://www.gnu.org/licenses/.
#
##############################################################################
from django import template
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils import six
from django.utils.encoding import force_text
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from backoffice.settings import base
from base.business.education_groups.perms import is_eligible_to_delete_education_group, \
    is_eligible_to_change_education_group, is_eligible_to_add_education_group, is_eligible_to_add_training, \
    is_eligible_to_add_mini_training, is_eligible_to_add_group

OPTIONAL_PNG = base.STATIC_URL + 'img/education_group_year/optional.png'
MANDATORY_PNG = base.STATIC_URL + 'img/education_group_year/mandatory.png'
CASE_JPG = base.STATIC_URL + 'img/education_group_year/case.jpg'

CHILD_BRANCH = """\
<tr>
    <td style="padding-left:{padding}em;width:{width_main};float:left;">
        <img src="{icon_list_2}" height="10" width="10">
        {value}{sublist}
    </td>
</tr>
"""

CHILD_LEAF = """\
<tr>
    <td style="padding-left:{padding}em;width:{width_main};float:left;">
        <img src="{icon_list_1}" height="14" width="17">
        <img src="{icon_list_2}" height="10" width="10">
        {value}{sublist}
    </td>
    <td style="width:{width_an};text-align: center;">{an_1}</td>
    <td style="width:{width_an};text-align: center;">{an_2}</td>
    <td style="width:{width_an};text-align: center;">{an_3}</td>
</tr>
"""

NO_GIVEN_ROOT = "INVALID TREE : no given root"
ICON_JSTREE_FILE = "data-jstree='{\"icon\":\"jstree-icon jstree-file\"}'"

# TODO use inclusion tag
LI_TEMPLATE = """
<li class="{}" id="{}">
    <a href="{}" data-toggle="tooltip" title="{}">{}</a>
</li>
"""

BUTTON_TEMPLATE = """
<button title="{}" class="btn btn-default btn-sm" id="{}" data-toggle="tooltip-wrapper" name="action" {}>
    <i class="fa {}"></i>
</button>
"""

BUTTON_ORDER_TEMPLATE = """
<button type="submit" title="{}" class="btn btn-default btn-sm" 
    id="{}" data-toggle="tooltip-wrapper" name="action" value="{}" {}>
    <i class="fa {}"></i>
</button>
"""

ICONS = {
    "up": "fa-arrow-up",
    "down": "fa-arrow-down",
    "detach": "fa-close",
    "edit": "fa-edit",
}

BRANCH_TEMPLATE = """
<ul>
    <li {data_jstree} id="node_{gey}_{egy}">
        <a href="{url}" class="{a_class}">
            {text}
        </a>
        {children}
    </li>
</ul>
"""

register = template.Library()


@register.simple_tag(takes_context=True)
def li_with_deletion_perm(context, url, message, url_id="link_delete"):
    return li_with_permission(context, is_eligible_to_delete_education_group, url, message, url_id)


@register.simple_tag(takes_context=True)
def li_with_update_perm(context, url, message, url_id="link_update"):
    return li_with_permission(context, is_eligible_to_change_education_group, url, message, url_id)


@register.simple_tag(takes_context=True)
def li_with_create_perm(context, url, message, url_id="link_create"):
    return li_with_permission(context, is_eligible_to_add_education_group, url, message, url_id)


@register.simple_tag(takes_context=True)
def li_with_create_perm_training(context, url, message, url_id="link_create"):
    return li_with_permission(context, is_eligible_to_add_training, url, message, url_id)


@register.simple_tag(takes_context=True)
def li_with_create_perm_mini_training(context, url, message, url_id="link_create"):
    return li_with_permission(context, is_eligible_to_add_mini_training, url, message, url_id)


@register.simple_tag(takes_context=True)
def li_with_create_perm_group(context, url, message, url_id="link_create"):
    return li_with_permission(context, is_eligible_to_add_group, url, message, url_id)


def li_with_permission(context, permission, url, message, url_id):
    permission_denied_message, disabled, root = _get_permission(context, permission)

    if not disabled:
        href = url
    else:
        href = "#"

    return mark_safe(LI_TEMPLATE.format(disabled, url_id, href, permission_denied_message, message))


def _get_permission(context, permission):
    permission_denied_message = ""

    education_group_year = context.get('education_group_year')
    person = context.get('person')
    root = context["request"].GET.get("root", "")

    try:
        result = permission(person, education_group_year, raise_exception=True)

    except PermissionDenied as e:
        result = False
        permission_denied_message = str(e)

    return permission_denied_message, "" if result else "disabled", root


@register.simple_tag(takes_context=True)
def button_order_with_permission(context, title, id_button, value):
    permission_denied_message, disabled, root = _get_permission(context, is_eligible_to_change_education_group)

    if disabled:
        title = permission_denied_message

    if value == "up" and context["forloop"]["first"]:
        disabled = "disabled"

    if value == "down" and context["forloop"]["last"]:
        disabled = "disabled"

    return mark_safe(BUTTON_ORDER_TEMPLATE.format(title, id_button, value, disabled, ICONS[value]))


@register.simple_tag(takes_context=True)
def button_with_permission(context, title, id_a, value):
    permission_denied_message, disabled, root = _get_permission(context, is_eligible_to_change_education_group)

    if disabled:
        title = permission_denied_message

    return mark_safe(BUTTON_TEMPLATE.format(title, id_a, disabled, ICONS[value]))


@register.filter(is_safe=True, needs_autoescape=True)
def pdf_tree_list(value, autoescape=True):
    if autoescape:
        escaper = conditional_escape
    else:
        def escaper(x):
            return x
    return mark_safe(list_formatter(value))


def walk_items(item_list):
    if item_list:
        item_iterator = iter(item_list)
        try:
            item = next(item_iterator)
            while True:
                try:
                    next_item = next(item_iterator)
                except StopIteration:
                    yield item, None
                    break
                if not isinstance(next_item, six.string_types):
                    try:
                        iter(next_item)
                    except TypeError:
                        pass
                    else:
                        yield item, next_item
                        item = next(item_iterator)
                        continue
                yield item, None
                item = next_item
        except StopIteration:
            pass
    else:
        return ""


def list_formatter(item_list, tabs=1, depth=None):
    output = []
    depth = depth if depth else 1
    for item, children in walk_items(item_list):
        sublist = ''
        padding = 2 * depth
        if children:
            sublist = '%s' % (
                list_formatter(children, tabs + 1, depth + 1))
        append_output(item, output, padding, sublist)
    return '\n'.join(output)


def append_output(item, output, padding, sublist):
    if item.child_leaf:
        if item.is_mandatory:
            output.append(
                CHILD_LEAF.format(padding=padding,
                                  width_main="80%",
                                  icon_list_1=CASE_JPG,
                                  icon_list_2=MANDATORY_PNG,
                                  value=escaper(force_text(item.verbose)),
                                  sublist=sublist,
                                  width_an="15px",
                                  an_1=check_block(item, "1"),
                                  an_2=check_block(item, "2"),
                                  an_3=check_block(item, "3")))
        else:
            output.append(
                CHILD_LEAF.format(padding=padding,
                                  width_main="80%",
                                  icon_list_1=CASE_JPG,
                                  icon_list_2=OPTIONAL_PNG,
                                  value=escaper(force_text(item.verbose)),
                                  sublist=sublist,
                                  width_an="15px",
                                  an_1=check_block(item, "1"),
                                  an_2=check_block(item, "2"),
                                  an_3=check_block(item, "3")))
    else:
        if item.is_mandatory:
            output.append(
                CHILD_BRANCH.format(padding=padding, width_main="80%",
                                    icon_list_2=MANDATORY_PNG,
                                    value=escaper(force_text(item.verbose)),
                                    sublist=sublist))
        else:
            output.append(
                CHILD_BRANCH.format(padding=padding, width_main="80%",
                                    icon_list_2=OPTIONAL_PNG,
                                    value=escaper(force_text(item.verbose)),
                                    sublist=sublist))


def check_block(item, value):
    return "X" if item.block and value in item.block else ""


def escaper(x):
    return x


@register.simple_tag(takes_context=True)
def build_tree(context, current_group_element_year, selected_education_group_year):
    request = context["request"]
    root = context["root"]

    # If it is the root, the group_element_year is not yet available.
    if not current_group_element_year:
        education_group_year = root
    else:
        education_group_year = current_group_element_year.child_branch

    if not selected_education_group_year:
        selected_education_group_year = education_group_year

    data_jstree = _get_icon_jstree(education_group_year)
    a_class = _get_a_class(education_group_year, selected_education_group_year)

    chidren_template = ""
    for child in education_group_year.group_element_year_branches:
        chidren_template += build_tree(context, child, selected_education_group_year)

    return mark_safe(BRANCH_TEMPLATE.format(
        data_jstree=data_jstree,
        gey=_get_group_element_year_id(current_group_element_year),
        egy=education_group_year.pk,
        url=_get_url(request, education_group_year, root, current_group_element_year),
        text=education_group_year.verbose,
        a_class=a_class,
        children=chidren_template
    ))


def _get_group_element_year_id(current_group_element_year):
    return current_group_element_year.pk if current_group_element_year else "-"


def _get_url(request, egy, root, current_group_element_year):
    url_name = request.resolver_match.url_name if request.resolver_match else "education_group_read"
    return reverse(url_name, args=[root.pk, egy.pk]) + "?group_to_parent=" + (
        str(current_group_element_year.id) if current_group_element_year else '0')


def _get_icon_jstree(education_group_year):
    if not education_group_year.group_element_year_branches:
        data_jstree = ICON_JSTREE_FILE
    else:
        data_jstree = ""
    return data_jstree


def _get_a_class(education_group_year, selected_education_group_year):
    return "jstree-wholerow-clicked" if education_group_year.pk == selected_education_group_year.pk else ""


@register.simple_tag(takes_context=True)
def url_resolver_match(context):
    return context.request.resolver_match.url_name
