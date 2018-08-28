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
from django.utils.translation import ugettext_lazy as _

from base.models import entity_version
from base.models.entity_container_year import EntityContainerYear
from base.models.entity_version import find_main_entities_version, get_last_version
from base.models.enums.entity_container_year_link_type import REQUIREMENT_ENTITY, ALLOCATION_ENTITY, \
    ADDITIONAL_REQUIREMENT_ENTITY_1, ADDITIONAL_REQUIREMENT_ENTITY_2, ENTITY_TYPE_LIST
from base.models.enums.learning_container_year_types import LEARNING_CONTAINER_YEAR_TYPES_MUST_HAVE_SAME_ENTITIES


class EntitiesVersionChoiceField(forms.ModelChoiceField):
    entity_version = None

    def label_from_instance(self, obj):
        return obj.acronym

    def clean(self, value):
        ev_data = super().clean(value)
        self.entity_version = ev_data
        return ev_data.entity if ev_data else None


class EntityContainerYearModelForm(forms.ModelForm):
    entity = EntitiesVersionChoiceField(find_main_entities_version())
    entity_type = ''

    def __init__(self, *args, **kwargs):
        self.person = kwargs.pop('person')

        super().__init__(*args, prefix=self.entity_type.lower(), **kwargs)

        self.fields['entity'].label = _(self.entity_type.lower())
        self.instance.type = self.entity_type

        if hasattr(self.instance, 'entity'):
            self.initial['entity'] = get_last_version(self.instance.entity).pk

    class Meta:
        model = EntityContainerYear
        fields = ['entity']

    def pre_save(self, learning_container_year):
        self.instance.learning_container_year = learning_container_year

    def save(self, commit=True):
        if hasattr(self.instance, 'entity'):
            return super().save(commit)
        elif self.instance.pk:
            # if the instance has no entity, it must be deleted
            self.instance.delete()

    @property
    def entity_version(self):
        return self.fields["entity"].entity_version

    def post_clean(self, start_date):
        entity = self.cleaned_data.get('entity')
        if not entity:
            return


class RequirementEntityContainerYearModelForm(EntityContainerYearModelForm):
    entity_type = REQUIREMENT_ENTITY

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields['entity']
        field.queryset = self.person.find_main_entities_version
        field.widget.attrs = {
            'onchange': (
                'updateAdditionalEntityEditability(this.value, "id_additional_requirement_entity_1", false);'
                'updateAdditionalEntityEditability(this.value, "id_additional_requirement_entity_2", true);'
            ), 'id': 'id_requirement_entity'}


class AllocationEntityContainerYearModelForm(EntityContainerYearModelForm):
    entity_type = ALLOCATION_ENTITY

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields['entity']
        field.widget.attrs = {'id': 'allocation_entity'}


class Additional1EntityContainerYearModelForm(EntityContainerYearModelForm):
    entity_type = ADDITIONAL_REQUIREMENT_ENTITY_1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields['entity']
        field.required = False
        field.widget.attrs = {
            'onchange':
                'updateAdditionalEntityEditability(this.value, "id_additional_requirement_entity_2", false)',
                'disable': 'disable',
                'id': 'id_additional_requirement_entity_1'
            }


class Additional2EntityContainerYearModelForm(EntityContainerYearModelForm):
    entity_type = ADDITIONAL_REQUIREMENT_ENTITY_2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields['entity']
        field.required = False
        field.widget.attrs = {'disable': 'disable', 'id': 'id_additional_requirement_entity_2'}


class EntityContainerBaseForm:
    form_classes = [
        RequirementEntityContainerYearModelForm,
        AllocationEntityContainerYearModelForm,
        Additional1EntityContainerYearModelForm,
        Additional2EntityContainerYearModelForm
    ]

    def __init__(self, data=None, person=None, learning_container_year=None):
        self.forms = []
        self.instance = learning_container_year
        for form in self.form_classes:
            qs = EntityContainerYear.objects.filter(learning_container_year=self.instance,
                                                    type=form.entity_type)

            instance = qs.get() if qs.exists() else None
            self.forms.append(form(data, person=person, instance=instance))

    @property
    def changed_data(self):
        return [form.changed_data for form in self.forms]

    @property
    def errors(self):
        return {form.prefix: form.errors for form in self.forms if form.errors}

    def get_clean_data_entity(self, key):
        try:
            form = self.forms[ENTITY_TYPE_LIST.index(key.upper())]
            return form.instance.entity
        except(AttributeError, IndexError):
            return None

    @property
    def fields(self):
        return OrderedDict(
            (ENTITY_TYPE_LIST[index].lower(), form.fields['entity']) for index, form in enumerate(self.forms)
        )

    @property
    def instances_data(self):
        return OrderedDict(
            (ENTITY_TYPE_LIST[index].lower(), getattr(form.instance, 'entity', None))
            for index, form in enumerate(self.forms)
        )

    def post_clean(self, container_type, academic_year):
        for form in self.forms:
            form.post_clean(academic_year.start_date)

        requirement_entity_version = self.forms[0].entity_version
        allocation_entity_version = self.forms[1].entity_version
        requirement_faculty = requirement_entity_version.find_faculty_version(academic_year)
        allocation_faculty = allocation_entity_version.find_faculty_version(academic_year)

        if container_type in LEARNING_CONTAINER_YEAR_TYPES_MUST_HAVE_SAME_ENTITIES:
            if requirement_faculty != allocation_faculty:
                self.forms[1].add_error(
                    "entity", _("Requirement and allocation entities must be linked to the same "
                                "faculty for this learning unit type.")
                )

        return not any(form.errors for form in self.forms)

    def is_valid(self):
        """ Trigger the forms validation"""
        return not self.errors

    def __iter__(self):
        """Yields the forms in the order they should be rendered"""
        return iter(self.forms)

    def __getitem__(self, index):
        """Returns the form at the given index, based on the rendering order"""
        return self.forms[index]

    def save(self, commit=True, learning_container_year=None):
        if learning_container_year:
            for form in self.forms:
                form.pre_save(learning_container_year)
        return [form.save(commit) for form in self.forms]

    def get_linked_entities_forms(self):
        return {key: self.get_clean_data_entity(key) for key in ENTITY_TYPE_LIST}
