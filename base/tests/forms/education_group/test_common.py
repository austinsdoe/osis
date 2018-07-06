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
from unittest.mock import patch

from base.models.entity_version import EntityVersion
from base.tests.factories.authorized_relationship import AuthorizedRelationshipFactory
from django.test import TestCase
from base.models.enums import organization_type
from base.tests.factories.academic_year import AcademicYearFactory, create_current_academic_year
from base.tests.factories.campus import CampusFactory
from base.tests.factories.education_group_type import EducationGroupTypeFactory
from base.tests.factories.education_group_year import EducationGroupYearFactory
from base.tests.factories.entity_version import MainEntityVersionFactory, EntityVersionFactory


class EducationGroupYearMixin(TestCase):
    """Common class used to get common tests on ModelForm instances of Training, MiniTraining and Group"""
    education_group_type = None

    @classmethod
    def setUp(cls, **kwargs):
        cls.education_group_type = kwargs.pop('education_group_type')

        cls.campus = CampusFactory(organization__type=organization_type.MAIN)
        cls.academic_year = AcademicYearFactory()
        new_entity_version = MainEntityVersionFactory()

        cls.form_data = {
            "acronym": "ACRO4569",
            "partial_acronym": "PACR8974",
            "education_group_type": cls.education_group_type.id,
            "title": "Test data",
            "main_teaching_campus": cls.campus.id,
            "academic_year": cls.academic_year.id,
            "administration_entity": new_entity_version.pk,
            "remark": "This is a test!!"
        }

        cls.parent_education_group_year = EducationGroupYearFactory(academic_year=cls.academic_year)
        cls.entity_version = EntityVersionFactory(entity=cls.parent_education_group_year.administration_entity)

    def _test_init_academic_year_field(self, form_class):
        form = form_class(parent=self.parent_education_group_year)

        academic_year_field = form.fields["academic_year"]
        self.assertTrue(academic_year_field.disabled)
        self.assertTrue(academic_year_field.disabled)
        self.assertTrue(academic_year_field.initial, self.academic_year)

    @patch('base.models.education_group_type.find_authorized_types')
    def _test_init_education_group_type_field(self, form_class, expected_category, mock_authorized_types):
        form_class(parent=self.parent_education_group_year)
        self.assertTrue(mock_authorized_types.called)
        expected_kwargs = {
            'category': expected_category,
            'parent_type': self.parent_education_group_year.education_group_type
        }
        mock_authorized_types.assert_called_with(**expected_kwargs)

    def _test_preselect_entity_version_from_entity_value(self, form_class):
        form = form_class(instance=self.parent_education_group_year)
        educ_group_entity = self.parent_education_group_year.administration_entity
        expected_entity_version = EntityVersion.objects.filter(entity=educ_group_entity).latest('start_date')
        self.assertEqual(form.initial['administration_entity'], expected_entity_version.id)


def _get_valid_post_data(category):
    entity_version = MainEntityVersionFactory()
    education_group_type = EducationGroupTypeFactory(category=category)
    campus = CampusFactory(organization__type=organization_type.MAIN)
    fake_education_group_year = EducationGroupYearFactory.build(
        academic_year=create_current_academic_year(),
        administration_entity=entity_version.entity,
        main_teaching_campus=campus,
        education_group_type=education_group_type
    )
    AuthorizedRelationshipFactory(child_type=fake_education_group_year.education_group_type)
    post_data = {
        'main_teaching_campus': str(fake_education_group_year.main_teaching_campus.id),
        'administration_entity': str(entity_version.id),
        'remark_english': str(fake_education_group_year.remark_english),
        'title_english': str(fake_education_group_year.title_english),
        'education_group_type': str(fake_education_group_year.education_group_type.id),
        'partial_acronym': str(fake_education_group_year.partial_acronym),
        'end_year': str(fake_education_group_year.education_group.end_year),
        'start_year': str(fake_education_group_year.education_group.start_year),
        'title': str(fake_education_group_year.title),
        'credits': str(fake_education_group_year.credits),
        'academic_year': str(fake_education_group_year.academic_year.id),
        'max_credits': str(fake_education_group_year.max_credits),
        'min_credits': str(fake_education_group_year.min_credits),
        'remark': str(fake_education_group_year.remark),
        'acronym': str(fake_education_group_year.acronym),
    }
    return fake_education_group_year, post_data
