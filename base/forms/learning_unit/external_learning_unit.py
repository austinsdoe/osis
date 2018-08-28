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
from collections.__init__ import OrderedDict

from django import forms
from django.db import transaction
from django.db.models import BLANK_CHOICE_DASH
from django.forms import ModelChoiceField
from django.utils.translation import ugettext_lazy as _

from base.forms.learning_unit.entity_form import EntitiesVersionChoiceField
from base.forms.learning_unit.learning_unit_create import LearningUnitModelForm, LearningUnitYearModelForm, \
    LearningContainerModelForm, LearningContainerYearModelForm
from base.forms.learning_unit.learning_unit_create_2 import LearningUnitBaseForm
from base.forms.learning_unit.learning_unit_partim import merge_data
from base.forms.utils.acronym_field import ExternalAcronymField
from base.forms.utils.dynamic_field import DynamicChoiceField
from base.models import entity_version
from base.models.campus import Campus
from base.models.entity_version import get_last_version, EntityVersion
from base.models.enums import learning_unit_year_subtypes
from base.models.enums.learning_container_year_types import EXTERNAL
from base.models.external_learning_unit_year import ExternalLearningUnitYear
from reference.models import language
from reference.models.country import Country


class CampusChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return "{}".format(obj.organization.name)


class LearningContainerYearExternalModelForm(LearningContainerYearModelForm):
    country = ModelChoiceField(
        queryset=Country.objects.filter(organizationaddress__isnull=False).distinct().order_by('name'),
        required=False,
        label=_("country")
    )
    city = DynamicChoiceField(required=False, label=_('city'), choices=BLANK_CHOICE_DASH)

    def prepare_fields(self):
        self.fields["container_type"].choices = ((EXTERNAL, _(EXTERNAL)),)
        self.fields['container_type'].disabled = True
        self.fields['container_type'].required = False

    @staticmethod
    def clean_container_type():
        return EXTERNAL


class ExternalLearningUnitModelForm(forms.ModelForm):
    requesting_entity = EntitiesVersionChoiceField(queryset=EntityVersion.objects.none(), label=_('requesting_entity'))
    entity_version = None

    def __init__(self, data, person, *args, **kwargs):
        self.person = person

        super().__init__(data, *args, **kwargs)
        self.instance.author = person
        self.fields['requesting_entity'].queryset = self.person.find_main_entities_version

        if hasattr(self.instance, 'requesting_entity'):
            self.initial['requesting_entity'] = get_last_version(self.instance.requesting_entity)

    class Meta:
        model = ExternalLearningUnitYear
        fields = ('external_acronym', 'external_credits', 'url', 'requesting_entity')

    def post_clean(self, start_date):
        entity = self.cleaned_data.get('requesting_entity')
        if not entity:
            return True

        entity_v = entity_version.get_by_entity_and_date(entity, start_date)
        if not entity_v:
            self.add_error('requesting_entity', _("The linked entity does not exist at the start date of the "
                                                  "academic year linked to this learning unit"))
        else:
            self.entity_version = entity_v

        return not self.errors


class ExternalLearningUnitBaseForm(LearningUnitBaseForm):
    forms = OrderedDict()
    academic_year = None
    subtype = learning_unit_year_subtypes.FULL

    entity_version = None

    form_cls = form_cls_to_validate = [
        LearningUnitModelForm,
        LearningUnitYearModelForm,
        LearningContainerModelForm,
        LearningContainerYearExternalModelForm,
        ExternalLearningUnitModelForm
    ]

    def __init__(self, person, academic_year, data=None, *args, **kwargs):
        self.academic_year = academic_year
        self.person = person
        instances_data = self._build_instance_data(data, academic_year)
        super().__init__(instances_data, *args, **kwargs)
        self.learning_unit_year_form.fields['acronym'] = ExternalAcronymField()
        self.learning_unit_year_form.fields['campus'] = CampusChoiceField(
            queryset=Campus.objects.order_by('organization__name').distinct('organization__name')
        )

    @property
    def learning_unit_external_form(self):
        return self.forms[ExternalLearningUnitModelForm]

    @property
    def learning_container_year_form(self):
        return self.forms[LearningContainerYearExternalModelForm]

    def _build_instance_data(self, data, default_ac_year):
        return {
            LearningUnitModelForm: {
                'data': merge_data(data, {'periodicity': 'ANNUAL'}),
                'instance': self.instance.learning_unit if self.instance else None,
            },
            LearningContainerModelForm: {
                'data': data,
                'instance': self.instance.learning_container_year.learning_container if self.instance else None,
            },
            LearningUnitYearModelForm: self._build_instance_data_learning_unit_year(data, default_ac_year),
            LearningContainerYearExternalModelForm: self._build_instance_data_learning_container_year(data),
            ExternalLearningUnitModelForm: self._build_instance_data_external_learning_unit(data)
        }

    def _build_instance_data_external_learning_unit(self, data):
        return {
            'data': data,
            'instance': None,
            'person': self.person
        }

    def _build_instance_data_learning_unit_year(self, data, default_ac_year):
        return {
            'data': data,
            'instance': self.instance,
            'initial': {'status': True,
                        'academic_year': default_ac_year},
            'person': self.person,
            'subtype': self.subtype
        }

    def _build_instance_data_learning_container_year(self, data):
        return {
            'data': data,
            'instance': self.instance.learning_container_year if self.instance else None,
            'initial': {
                # Default language French
                'language': language.find_by_code('FR'),
            },
            'person': self.person
        }

    def get_context(self):
        return {
            'subtype': self.subtype,
            'learning_unit_form': self.learning_unit_form,
            'learning_unit_year_form': self.learning_unit_year_form,
            'learning_container_year_form': self.learning_container_year_form,
            'learning_unit_external_form': self.learning_unit_external_form
        }

    @transaction.atomic()
    def save(self, commit=True):
        academic_year = self.academic_year

        learning_container = self.learning_container_form.save(commit)
        learning_unit = self.learning_unit_form.save(
            start_year=self.learning_unit_year_form.instance.academic_year.year,
            learning_container=learning_container,
            commit=commit
        )
        container_year = self.learning_container_year_form.save(
            academic_year=academic_year,
            learning_container=learning_container,
            acronym=self.learning_unit_year_form.instance.acronym,
            commit=commit
        )

        # Save learning unit year (learning_unit_component +  learning_component_year + entity_component_year)
        learning_unit_year = self.learning_unit_year_form.save(
            learning_container_year=container_year,
            learning_unit=learning_unit,
            commit=commit
        )

        self.learning_unit_external_form.instance.learning_unit_year = learning_unit_year
        self.learning_unit_external_form.save(commit)

        return learning_unit_year

    def is_valid(self):
        return super().is_valid() and self.learning_unit_external_form.post_clean(self.academic_year.start_date)
