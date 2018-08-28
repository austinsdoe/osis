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
from django import forms
from django.forms import ModelChoiceField
from django.utils.functional import lazy
from django.utils.translation import ugettext_lazy as _

from base.business.entity import get_entities_ids
from base.forms.bootstrap import BootstrapForm
from base.models import academic_year, education_group_year
from base.models.education_group_type import EducationGroupType
from base.models.enums import education_group_categories


class EntityManagementModelChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.acronym


class SelectWithData(forms.Select):
    data_attrs = None

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option_dict = super(forms.Select, self).create_option(name, value, label, selected, index,
                                                              subindex=subindex, attrs=attrs)
        group_type = self.data_attrs().get(value)
        if group_type:
            option_dict['attrs']['data-category'] = group_type.category
        return option_dict


class ModelChoiceFieldWithData(forms.ModelChoiceField):
    widget = SelectWithData

    def __init__(self, queryset, **kwargs):
        super(ModelChoiceFieldWithData, self).__init__(queryset, **kwargs)
        self.widget.data_attrs = lazy(queryset.in_bulk, dict)


class EducationGroupFilter(BootstrapForm):

    academic_year = forms.ModelChoiceField(
        queryset=academic_year.find_academic_years(),
        required=False,
        empty_label=_('all_label'),
        label=_('academic_year_small')
    )

    category = forms.ChoiceField(
        choices=[("", _('all_label'))] + list(education_group_categories.CATEGORIES),
        required=False,
        label=_('category')
    )

    education_group_type = ModelChoiceFieldWithData(
        queryset=EducationGroupType.objects.all(),
        required=False,
        empty_label=_('all_label'),
        label=_('type')
    )

    acronym = forms.CharField(max_length=40, required=False, label=_('acronym'))
    title = forms.CharField(max_length=255, required=False, label=_('title'))
    requirement_entity_acronym = forms.CharField(max_length=20, required=False, label=_('entity'))
    partial_acronym = forms.CharField(max_length=15, required=False, label=_('code'))
    with_entity_subordinated = forms.BooleanField(required=False)

    def clean_category(self):
        data_cleaned = self.cleaned_data.get('category')
        if data_cleaned:
            return data_cleaned

    def get_object_list(self):
        clean_data = {key: value for key, value in self.cleaned_data.items() if value is not None}

        result = education_group_year.search(**clean_data)

        if clean_data.get('requirement_entity_acronym'):
            result = _get_filter_entity_management(
                result,
                clean_data['requirement_entity_acronym'],
                clean_data.get('with_entity_subordinated',False)
            )

        # TODO User should choice the order
        return result.order_by('acronym')


def _get_filter_entity_management(qs, requirement_entity_acronym, with_entity_subordinated):
    entity_ids = get_entities_ids(requirement_entity_acronym, with_entity_subordinated)
    return qs.filter(management_entity__in=entity_ids)
