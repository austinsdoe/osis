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
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from waffle.testutils import override_flag

from base.forms.education_group.group import GroupModelForm
from base.forms.education_group.mini_training import MiniTrainingModelForm
from base.forms.education_group.training import TrainingEducationGroupYearForm
from base.models.enums import education_group_categories
from base.tests.factories.education_group_year import EducationGroupYearFactory
from base.tests.factories.person import PersonFactory


@override_flag('education_group_create', active=True)
class TestCreate(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.parent_education_group_year = EducationGroupYearFactory()

        cls.test_categories = [
            education_group_categories.GROUP,
            education_group_categories.TRAINING,
            education_group_categories.MINI_TRAINING,
        ]

        cls.urls_without_parent_by_category = {
            category:
                reverse(
                    "new_education_group",
                    kwargs={
                        "category": category,
                    }
                )
            for category in cls.test_categories
        }
        cls.urls_with_parent_by_category = {
            category:
                reverse(
                    "new_education_group",
                    kwargs={
                        "category": category,
                        "parent_id": cls.parent_education_group_year.id,
                    }
                )
            for category in cls.test_categories
        }
        cls.expected_templates_by_category = {
            education_group_categories.GROUP: "education_group/create_groups.html",
            education_group_categories.TRAINING: "education_group/create_trainings.html",
            education_group_categories.MINI_TRAINING: "education_group/create_mini_trainings.html",
        }
        cls.person = PersonFactory()

    def setUp(self):
        self.client.force_login(self.person.user)
        self.perm_patcher = mock.patch("base.business.education_groups.perms.is_eligible_to_add_education_group",
                                       return_value=True)
        self.mocked_perm = self.perm_patcher.start()

    def tearDown(self):
        self.perm_patcher.stop()

    def test_login_required(self):
        self.client.logout()
        for url in self.urls_without_parent_by_category.values():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, '/login/?next={}'.format(url))

    def test_permission_required(self):
        for url in self.urls_without_parent_by_category.values():
            with self.subTest(url=url):
                self.client.get(url)
                self.mocked_perm.assert_called_with(self.person, None, raise_exception=True)

    def test_template_used(self):
        for category in self.test_categories:
            with self.subTest(category=category):
                response = self.client.get(self.urls_without_parent_by_category.get(category))
                self.assertTemplateUsed(response, self.expected_templates_by_category.get(category))

    def test_with_parent_set(self):
        for category in self.test_categories:
            with self.subTest(category=category):
                response = self.client.get(self.urls_with_parent_by_category.get(category))
                self.assertTemplateUsed(response, self.expected_templates_by_category.get(category))

    def test_response_context(self):
        expected_forms_by_category = {
            education_group_categories.GROUP: GroupModelForm,
            education_group_categories.TRAINING: TrainingEducationGroupYearForm,
            education_group_categories.MINI_TRAINING: MiniTrainingModelForm,
        }
        for category in self.test_categories:
            with self.subTest(category=category):
                response = self.client.get(self.urls_without_parent_by_category.get(category))
                form_education_group_year = response.context["form_education_group_year"]
                self.assertIsInstance(form_education_group_year, expected_forms_by_category.get(category))
