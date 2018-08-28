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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    A copy of this license - GNU General Public License - is available
#    at the root of the source code of this program.  If not,
#    see http://www.gnu.org/licenses/.
#
##############################################################################
import datetime
import json
from http import HTTPStatus
from unittest import mock

import bs4
from django.conf import settings
from django.contrib.auth.models import Permission, Group
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden, HttpResponseNotFound, HttpResponse
from django.test import TestCase, RequestFactory
from django.utils.translation import ugettext_lazy as _
from waffle.testutils import override_flag

from base.forms.education_group_general_informations import EducationGroupGeneralInformationsForm
from base.forms.education_groups import EducationGroupFilter
from base.models.admission_condition import AdmissionCondition, AdmissionConditionLine
from base.models.enums import education_group_categories, academic_calendar_type
from base.tests.factories.academic_year import AcademicYearFactory
from base.tests.factories.education_group_language import EducationGroupLanguageFactory
from base.tests.factories.education_group_type import EducationGroupTypeFactory
from base.tests.factories.education_group_year import EducationGroupYearFactory
from base.tests.factories.entity import EntityFactory
from base.tests.factories.entity_version import EntityVersionFactory
from base.tests.factories.group_element_year import GroupElementYearFactory
from base.tests.factories.person import PersonFactory
from base.tests.factories.program_manager import ProgramManagerFactory
from base.tests.factories.user import UserFactory, SuperUserFactory
from cms.enums import entity_name
from cms.models.translated_text import TranslatedText
from cms.tests.factories.text_label import TextLabelFactory
from cms.tests.factories.translated_text import TranslatedTextFactory, TranslatedTextRandomFactory
from cms.tests.factories.translated_text_label import TranslatedTextLabelFactory


class EducationGroupSearch(TestCase):
    @classmethod
    def setUpTestData(cls):
        today = datetime.date.today()
        cls.academic_year = AcademicYearFactory(start_date=today, end_date=today.replace(year=today.year + 1),
                                                year=today.year)
        cls.previous_academic_year = AcademicYearFactory(start_date=today.replace(year=today.year - 1),
                                                         end_date=today - datetime.timedelta(days=1),
                                                         year=today.year - 1)

        cls.type_training = EducationGroupTypeFactory(category=education_group_categories.TRAINING)
        cls.type_minitraining = EducationGroupTypeFactory(category=education_group_categories.MINI_TRAINING)
        cls.type_group = EducationGroupTypeFactory(category=education_group_categories.GROUP)

        oph_entity = EntityFactory()
        envi_entity = EntityFactory()

        cls.education_group_edph2 = EducationGroupYearFactory(
            acronym='EDPH2', academic_year=cls.academic_year,
            partial_acronym='EDPH2_SCS',
            education_group_type=cls.type_group,
            management_entity=envi_entity
        )

        cls.education_group_arke2a = EducationGroupYearFactory(
            acronym='ARKE2A', academic_year=cls.academic_year,
            education_group_type=cls.type_training,
            management_entity=oph_entity
        )

        cls.education_group_hist2a = EducationGroupYearFactory(
            acronym='HIST2A', academic_year=cls.academic_year,
            education_group_type=cls.type_group,
            management_entity=oph_entity
        )

        cls.education_group_arke2a_previous_year = EducationGroupYearFactory(
            acronym='ARKE2A',
            academic_year=cls.previous_academic_year,
            education_group_type=cls.type_training,
            management_entity=oph_entity
        )

        cls.oph_entity_v = EntityVersionFactory(entity=oph_entity, parent=envi_entity, end_date=None)
        cls.envi_entity_v = EntityVersionFactory(entity=envi_entity, end_date=None)

        cls.user = PersonFactory().user
        cls.user.user_permissions.add(Permission.objects.get(codename="can_access_education_group"))
        cls.url = reverse("education_groups")

    def setUp(self):
        self.client.force_login(self.user)

    def test_when_not_logged(self):
        self.client.logout()
        response = self.client.get(self.url)

        self.assertRedirects(response, "/login/?next={}".format(self.url))

    def test_user_without_permission(self):
        an_other_user = UserFactory()
        self.client.force_login(an_other_user)
        response = self.client.get(self.url)

        self.assertTemplateUsed(response, "access_denied.html")
        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)

    def test_post_request(self):
        response = self.client.post(self.url, data={})

        self.assertTemplateUsed(response, "education_groups.html")

        context = response.context
        self.assertIsInstance(context["form"], EducationGroupFilter)
        self.assertEqual(context["object_list_count"], 0)
        self.assertEqual(context["experimental_phase"], True)

    def test_without_get_data(self):
        response = self.client.get(self.url)

        self.assertTemplateUsed(response, "education_groups.html")

        context = response.context
        self.assertIsInstance(context["form"], EducationGroupFilter)
        self.assertEqual(context["object_list_count"], 0)
        self.assertEqual(context["experimental_phase"], True)

    def test_initial_form_data(self):
        response = self.client.get(self.url)

        form = response.context["form"]
        self.assertEqual(form.initial["academic_year"], self.academic_year)
        self.assertEqual(form.initial["category"], education_group_categories.TRAINING)

    def test_with_empty_search_result(self):
        response = self.client.get(self.url, data={"category": education_group_categories.MINI_TRAINING})

        self.assertTemplateUsed(response, "education_groups.html")

        context = response.context
        self.assertIsInstance(context["form"], EducationGroupFilter)
        self.assertEqual(context["experimental_phase"], True)
        self.assertEqual(len(context["object_list"]), 0)
        messages = [str(m) for m in context["messages"]]
        self.assertIn(_('no_result'), messages)

    def test_search_with_acronym_only(self):
        response = self.client.get(self.url, data={"acronym": self.education_group_arke2a.acronym})

        self.assertTemplateUsed(response, "education_groups.html")

        context = response.context
        self.assertIsInstance(context["form"], EducationGroupFilter)
        self.assertEqual(context["experimental_phase"], True)
        self.assertCountEqual(context["object_list"],
                              [self.education_group_arke2a, self.education_group_arke2a_previous_year])

    def test_search_with_academic_year_only(self):
        response = self.client.get(self.url, data={"academic_year": self.academic_year.id})

        self.assertTemplateUsed(response, "education_groups.html")

        context = response.context
        self.assertIsInstance(context["form"], EducationGroupFilter)
        self.assertEqual(context["experimental_phase"], True)
        self.assertCountEqual(context["object_list"],
                              [self.education_group_arke2a, self.education_group_edph2, self.education_group_hist2a])

    def test_search_with_partial_acronym(self):
        response = self.client.get(self.url, data={"partial_acronym": self.education_group_edph2.partial_acronym})

        self.assertTemplateUsed(response, "education_groups.html")

        context = response.context
        self.assertIsInstance(context["form"], EducationGroupFilter)
        self.assertEqual(context["experimental_phase"], True)
        self.assertCountEqual(context["object_list"], [self.education_group_edph2])

    def test_search_with_requirement_entity(self):
        response = self.client.get(self.url,
                                   data={"requirement_entity_acronym": self.oph_entity_v.acronym})

        self.assertTemplateUsed(response, "education_groups.html")

        context = response.context
        self.assertIsInstance(context["form"], EducationGroupFilter)
        self.assertEqual(context["experimental_phase"], True)
        self.assertCountEqual(context["object_list"],
                              [self.education_group_arke2a, self.education_group_arke2a_previous_year,
                               self.education_group_hist2a])

    def test_search_with_entities_subordinated(self):
        response = self.client.get(
            self.url,
            data={
                "requirement_entity_acronym": self.envi_entity_v.acronym,
                "with_entity_subordinated": True
            }
        )

        self.assertTemplateUsed(response, "education_groups.html")

        context = response.context
        self.assertIsInstance(context["form"], EducationGroupFilter)
        self.assertEqual(context["experimental_phase"], True)
        self.assertCountEqual(
            context["object_list"],
            [
                self.education_group_arke2a,
                self.education_group_arke2a_previous_year,
                self.education_group_hist2a,
                self.education_group_edph2
            ]
        )

    def test_search_by_education_group_type(self):
        response = self.client.get(self.url,
                                   data={"education_group_type": self.type_group.id})

        self.assertTemplateUsed(response, "education_groups.html")

        context = response.context
        self.assertIsInstance(context["form"], EducationGroupFilter)
        self.assertEqual(context["experimental_phase"], True)
        self.assertCountEqual(context["object_list"], [self.education_group_hist2a, self.education_group_edph2])

    def test_search_by_education_group_category(self):
        response = self.client.get(self.url,
                                   data={"category": education_group_categories.TRAINING})

        self.assertTemplateUsed(response, "education_groups.html")

        context = response.context
        self.assertIsInstance(context["form"], EducationGroupFilter)
        self.assertEqual(context["experimental_phase"], True)
        self.assertCountEqual(context["object_list"],
                              [self.education_group_arke2a, self.education_group_arke2a_previous_year])

    def test_with_multiple_criteria(self):
        response = self.client.get(
            self.url, data={
                "academic_year": self.academic_year.id,
                "acronym": self.education_group_arke2a.acronym,
                "requirement_entity_acronym": self.envi_entity_v.acronym,
                "with_entity_subordinated": True
            }
        )

        self.assertTemplateUsed(response, "education_groups.html")

        context = response.context
        self.assertIsInstance(context["form"], EducationGroupFilter)
        self.assertEqual(context["experimental_phase"], True)
        self.assertCountEqual(context["object_list"], [self.education_group_arke2a])


class EducationGroupRead(TestCase):
    @classmethod
    def setUpTestData(cls):
        today = datetime.date.today()
        academic_year = AcademicYearFactory(start_date=today, end_date=today.replace(year=today.year + 1),
                                            year=today.year)
        cls.education_group_parent = EducationGroupYearFactory(acronym="Parent", academic_year=academic_year)
        cls.education_group_child_1 = EducationGroupYearFactory(acronym="Child_1", academic_year=academic_year)
        cls.education_group_child_2 = EducationGroupYearFactory(acronym="Child_2", academic_year=academic_year)

        GroupElementYearFactory(parent=cls.education_group_parent, child_branch=cls.education_group_child_1)
        GroupElementYearFactory(parent=cls.education_group_parent, child_branch=cls.education_group_child_2)

        cls.education_group_language_parent = \
            EducationGroupLanguageFactory(education_group_year=cls.education_group_parent)
        cls.education_group_language_child_1 = \
            EducationGroupLanguageFactory(education_group_year=cls.education_group_child_1)

        cls.user = PersonFactory().user
        cls.user.user_permissions.add(Permission.objects.get(codename="can_access_education_group"))
        cls.url = reverse("education_group_read",
                          args=[cls.education_group_parent.id, cls.education_group_child_1.id])

    def setUp(self):
        self.client.force_login(self.user)

    def test_when_not_logged(self):
        self.client.logout()
        response = self.client.get(self.url)

        self.assertRedirects(response, "/login/?next={}".format(self.url))

    def test_user_without_permission(self):
        an_other_user = UserFactory()
        self.client.force_login(an_other_user)
        response = self.client.get(self.url)

        self.assertTemplateUsed(response, "access_denied.html")
        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)

    def test_with_non_existent_education_group_year(self):
        non_existent_id = self.education_group_child_1.id + self.education_group_child_2.id + \
                          self.education_group_parent.id
        url = reverse("education_group_read", args=[self.education_group_parent.pk, non_existent_id])
        response = self.client.get(url)

        self.assertTemplateUsed(response, "page_not_found.html")
        self.assertEqual(response.status_code, HttpResponseNotFound.status_code)

    def test_without_get_data(self):
        response = self.client.get(self.url)

        self.assertTemplateUsed(response, "education_group/tab_identification.html")

        context = response.context
        self.assertEqual(context["education_group_year"], self.education_group_child_1)
        self.assertListEqual(context["education_group_languages"],
                             [self.education_group_language_child_1.language.name])
        self.assertEqual(context["enums"], education_group_categories)
        self.assertEqual(context["parent"], self.education_group_parent)

    def test_with_root_set(self):
        response = self.client.get(self.url, data={"root": self.education_group_parent.id})

        self.assertTemplateUsed(response, "education_group/tab_identification.html")

        context = response.context
        self.assertEqual(context["education_group_year"], self.education_group_child_1)
        self.assertListEqual(context["education_group_languages"],
                             [self.education_group_language_child_1.language.name])
        self.assertEqual(context["enums"], education_group_categories)
        self.assertEqual(context["parent"], self.education_group_parent)

    def test_with_non_existent_root_id(self):
        non_existent_id = self.education_group_child_1.id + self.education_group_child_2.id + \
                         self.education_group_parent.id
        url = reverse("education_group_read",
                      args=[non_existent_id, self.education_group_child_1.id])

        response = self.client.get(url)

        self.assertTemplateUsed(response, "page_not_found.html")
        self.assertEqual(response.status_code, HttpResponseNotFound.status_code)

    def test_with_root_set_as_current_education_group_year(self):
        response = self.client.get(self.url, data={"root": self.education_group_child_1.id})

        self.assertTemplateUsed(response, "education_group/tab_identification.html")

        context = response.context
        self.assertEqual(context["education_group_year"], self.education_group_child_1)
        self.assertListEqual(context["education_group_languages"],
                             [self.education_group_language_child_1.language.name])
        self.assertEqual(context["enums"], education_group_categories)
        self.assertEqual(context["parent"], self.education_group_parent)

    def test_with_without_education_group_language(self):
        url = reverse("education_group_read", args=[self.education_group_parent.pk, self.education_group_child_2.id])
        response = self.client.get(url)

        self.assertTemplateUsed(response, "education_group/tab_identification.html")

        context = response.context
        self.assertEqual(context["education_group_year"], self.education_group_child_2)
        self.assertListEqual(context["education_group_languages"], [])
        self.assertEqual(context["enums"], education_group_categories)
        self.assertEqual(context["parent"], self.education_group_parent)


class EducationGroupDiplomas(TestCase):
    @classmethod
    def setUpTestData(cls):
        academic_year = AcademicYearFactory()
        type_training = EducationGroupTypeFactory(category=education_group_categories.TRAINING)
        cls.education_group_parent = EducationGroupYearFactory(acronym="Parent", academic_year=academic_year,
                                                               education_group_type=type_training)
        cls.education_group_child = EducationGroupYearFactory(acronym="Child_1", academic_year=academic_year,
                                                              education_group_type=type_training)
        GroupElementYearFactory(parent=cls.education_group_parent, child_branch=cls.education_group_child)
        cls.user = UserFactory()
        cls.person = PersonFactory(user=cls.user)
        cls.user.user_permissions.add(Permission.objects.get(codename="can_access_education_group"))
        cls.url = reverse("education_group_diplomas",
                          args=[cls.education_group_parent.pk, cls.education_group_child.id])

    def setUp(self):
        self.client.force_login(self.user)

    def test_when_not_logged(self):
        self.client.logout()
        response = self.client.get(self.url)

        self.assertRedirects(response, "/login/?next={}".format(self.url))

    def test_user_without_permission(self):
        an_other_user = UserFactory()
        self.client.force_login(an_other_user)
        response = self.client.get(self.url)

        self.assertTemplateUsed(response, "access_denied.html")
        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)

    def test_with_non_existent_education_group_year(self):
        non_existent_id = self.education_group_child.id + self.education_group_parent.id
        url = reverse("education_group_diplomas", args=[self.education_group_parent.pk, non_existent_id])
        response = self.client.get(url)

        self.assertTemplateUsed(response, "page_not_found.html")
        self.assertEqual(response.status_code, HttpResponseNotFound.status_code)

    def test_with_education_group_year_of_type_mini_training(self):
        mini_training_education_group_year = EducationGroupYearFactory()
        mini_training_education_group_year.education_group_type.category = education_group_categories.MINI_TRAINING
        mini_training_education_group_year.education_group_type.save()

        url = reverse("education_group_diplomas",
                      args=[mini_training_education_group_year.id, mini_training_education_group_year.id])
        response = self.client.get(url)

        self.assertTemplateUsed(response, "access_denied.html")
        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)

    def test_with_education_group_year_of_type_group(self):
        group_education_group_year = EducationGroupYearFactory()
        group_education_group_year.education_group_type.category = education_group_categories.GROUP
        group_education_group_year.education_group_type.save()

        url = reverse("education_group_diplomas",
                      args=[group_education_group_year.id, group_education_group_year.id]
                      )
        response = self.client.get(url)

        self.assertTemplateUsed(response, "access_denied.html")
        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)

    def test_without_get_data(self):
        response = self.client.get(self.url)

        self.assertTemplateUsed(response, "education_group/tab_diplomas.html")

        context = response.context
        self.assertEqual(context["education_group_year"], self.education_group_child)
        self.assertEqual(context["parent"], self.education_group_parent)

    def test_with_non_existent_root_id(self):
        non_existent_id = self.education_group_child.id + self.education_group_parent.id
        url = reverse("education_group_diplomas", args=[non_existent_id, self.education_group_child.pk])
        response = self.client.get(url)

        self.assertTemplateUsed(response, "page_not_found.html")
        self.assertEqual(response.status_code, HttpResponseNotFound.status_code)

    def test_with_root_set(self):
        response = self.client.get(self.url, data={"root": self.education_group_parent.id})

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "education_group/tab_diplomas.html")

        context = response.context
        self.assertEqual(context["education_group_year"], self.education_group_child)
        self.assertEqual(context["parent"], self.education_group_parent)


class EducationGroupGeneralInformations(TestCase):
    @classmethod
    def setUpTestData(cls):
        academic_year = AcademicYearFactory()
        type_training = EducationGroupTypeFactory(category=education_group_categories.TRAINING)
        cls.education_group_parent = EducationGroupYearFactory(acronym="Parent", academic_year=academic_year,
                                                               education_group_type=type_training)
        cls.education_group_child = EducationGroupYearFactory(acronym="Child_1", academic_year=academic_year,
                                                              education_group_type=type_training)

        GroupElementYearFactory(parent=cls.education_group_parent, child_branch=cls.education_group_child)

        cls.cms_label_for_child = TranslatedTextFactory(text_label=TextLabelFactory(entity=entity_name.OFFER_YEAR),
                                                        reference=cls.education_group_child.id)

        cls.user = UserFactory()
        cls.person = PersonFactory(user=cls.user)
        cls.user.user_permissions.add(Permission.objects.get(codename="can_access_education_group"))
        cls.url = reverse("education_group_general_informations",
                          args=[cls.education_group_parent.pk, cls.education_group_child.id])

    def setUp(self):
        self.client.force_login(self.user)

    def test_when_not_logged(self):
        self.client.logout()
        response = self.client.get(self.url)

        self.assertRedirects(response, "/login/?next={}".format(self.url))

    def test_user_without_permission(self):
        an_other_user = UserFactory()
        self.client.force_login(an_other_user)
        response = self.client.get(self.url)

        self.assertTemplateUsed(response, "access_denied.html")
        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)

    def test_with_non_existent_education_group_year(self):
        non_existent_id = self.education_group_child.id + self.education_group_parent.id
        url = reverse("education_group_diplomas", args=[self.education_group_parent.pk, non_existent_id])
        response = self.client.get(url)

        self.assertTemplateUsed(response, "page_not_found.html")
        self.assertEqual(response.status_code, HttpResponseNotFound.status_code)

    def test_with_education_group_year_of_type_group(self):
        group_education_group_year = EducationGroupYearFactory()
        group_education_group_year.education_group_type.category = education_group_categories.GROUP
        group_education_group_year.education_group_type.save()

        url = reverse("education_group_general_informations",
                      args=[group_education_group_year.id, group_education_group_year.id])
        response = self.client.get(url)

        self.assertTemplateUsed(response, "access_denied.html")
        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)

    def test_without_get_data(self):
        response = self.client.get(self.url)

        self.assertTemplateUsed(response, "education_group/tab_general_informations.html")

        context = response.context
        self.assertEqual(context["parent"], self.education_group_parent)
        self.assertEqual(context["education_group_year"], self.education_group_child)
        self.assertDictEqual(context["cms_labels_translated"], {self.cms_label_for_child.text_label.label: None})
        self.assertIsInstance(context["form_french"], EducationGroupGeneralInformationsForm)
        self.assertIsInstance(context["form_english"], EducationGroupGeneralInformationsForm)

    def test_form_initialization(self):
        response = self.client.get(self.url)

        self.assertTemplateUsed(response, "education_group/tab_general_informations.html")

        context = response.context
        form_french = context["form_french"]
        form_english = context["form_english"]

        self.assertEqual(form_french.education_group_year, self.education_group_child)
        self.assertEqual(form_english.education_group_year, self.education_group_child)

        self.assertEqual(form_french.language, settings.LANGUAGES[0])
        self.assertEqual(form_english.language, settings.LANGUAGES[1])

        self.assertEqual(list(form_french.text_labels_name), [self.cms_label_for_child.text_label.label])
        self.assertEqual(list(form_english.text_labels_name), [self.cms_label_for_child.text_label.label])

    def test_user_has_link_to_edit_pedagogy(self):
        self.user.user_permissions.add(Permission.objects.get(codename='can_edit_educationgroup_pedagogy'))

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HttpResponse.status_code)
        self.assertTemplateUsed(response, "education_group/tab_general_informations.html")

        soup = bs4.BeautifulSoup(response.content, 'html.parser')
        self.assertEqual(len(soup.select('a.pedagogy-edit-btn')), 2)

    def test_user_has_not_link_to_edit_pedagogy(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HttpResponse.status_code)
        self.assertTemplateUsed(response, "education_group/tab_general_informations.html")

        soup = bs4.BeautifulSoup(response.content, 'html.parser')
        self.assertEqual(len(soup.select('a.pedagogy-edit-btn')), 0)


@override_flag('education_group_update', active=True)
class EducationGroupViewTestCase(TestCase):
    def setUp(self):
        today = datetime.date.today()
        self.academic_year = AcademicYearFactory(start_date=today,
                                                 end_date=today.replace(year=today.year + 1),
                                                 year=today.year)

        self.type_training = EducationGroupTypeFactory(category=education_group_categories.TRAINING)
        self.type_minitraining = EducationGroupTypeFactory(category=education_group_categories.MINI_TRAINING)
        self.type_group = EducationGroupTypeFactory(category=education_group_categories.GROUP)

    def test_education_administrative_data(self):
        an_education_group = EducationGroupYearFactory()
        self.initialize_session()
        url = reverse("education_group_administrative", args=[an_education_group.id, an_education_group.id])
        response = self.client.get(url)
        self.assertTemplateUsed(response, "education_group/tab_administrative_data.html")
        self.assertEqual(response.context['education_group_year'], an_education_group)
        self.assertEqual(response.context['parent'], an_education_group)

    def test_education_administrative_data_with_root_set(self):
        a_group_element_year = GroupElementYearFactory()
        self.initialize_session()
        url = reverse("education_group_administrative",
                      args=[a_group_element_year.parent.id, a_group_element_year.child_branch.id])
        response = self.client.get(url)
        self.assertTemplateUsed(response, "education_group/tab_administrative_data.html")
        self.assertEqual(response.context['education_group_year'], a_group_element_year.child_branch)
        self.assertEqual(response.context['parent'], a_group_element_year.parent)

    def test_get_sessions_dates(self):
        from base.views.education_groups.detail import get_sessions_dates
        from base.tests.factories.session_exam_calendar import SessionExamCalendarFactory
        from base.tests.factories.academic_calendar import AcademicCalendarFactory
        from base.tests.factories.education_group_year import EducationGroupYearFactory
        from base.tests.factories.offer_year_calendar import OfferYearCalendarFactory

        sessions_quantity = 3
        an_academic_year = AcademicYearFactory()
        academic_calendars = [
            AcademicCalendarFactory(academic_year=an_academic_year,
                                    reference=academic_calendar_type.DELIBERATION)
            for _ in range(sessions_quantity)
        ]
        education_group_year = EducationGroupYearFactory(academic_year=an_academic_year)

        for session, academic_calendar in enumerate(academic_calendars):
            SessionExamCalendarFactory(number_session=session + 1, academic_calendar=academic_calendar)

        offer_year_calendars = [OfferYearCalendarFactory(
            academic_calendar=academic_calendar,
            education_group_year=education_group_year)
        for academic_calendar in academic_calendars]

        self.assertEqual(
            get_sessions_dates(academic_calendars[0].reference, education_group_year),
            {
                'session{}'.format(s+1): offer_year_calendar
                for s, offer_year_calendar in enumerate(offer_year_calendars)
            }
        )

    @mock.patch('django.contrib.auth.decorators')
    @mock.patch('base.views.layout.render')
    @mock.patch('base.business.education_group.can_user_edit_administrative_data')
    def test_education_edit_administrative_data(self,
                                                mock_can_user_edit_administrative_data,
                                                mock_render,
                                                mock_decorators):
        mock_decorators.login_required = lambda x: x
        mock_decorators.permission_required = lambda *args, **kwargs: lambda func: func
        education_group_year = EducationGroupYearFactory(academic_year=self.academic_year)
        from base.views.education_group import education_group_edit_administrative_data

        request_factory = RequestFactory()
        request = request_factory.get(reverse(education_group_edit_administrative_data, kwargs={
            'root_id': education_group_year.id,
            'education_group_year_id': education_group_year.id
        }))
        request.user = mock.Mock()
        mock_can_user_edit_administrative_data.return_value = True

        education_group_edit_administrative_data(request, education_group_year.id, education_group_year.id)
        self.assertTrue(mock_render.called)
        request, template, context = mock_render.call_args[0]
        self.assertEqual(template, 'education_group/tab_edit_administrative_data.html')
        self.assertEqual(context['education_group_year'], education_group_year)
        self.assertEqual(context['course_enrollment_validity'], False)
        self.assertEqual(context['formset_session_validity'], False)

    def test_education_content(self):
        an_education_group = EducationGroupYearFactory()
        self.initialize_session()
        url = reverse("education_group_diplomas", args=[an_education_group.id, an_education_group.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "education_group/tab_diplomas.html")

    def initialize_session(self):
        person = PersonFactory()
        person.user.user_permissions.add(Permission.objects.get(codename="can_access_education_group"))
        self.client.force_login(person.user)


class EducationGroupAdministrativedata(TestCase):
    def setUp(self):
        self.person = PersonFactory()

        self.permission_access = Permission.objects.get(codename='can_access_education_group')
        self.person.user.user_permissions.add(self.permission_access)

        self.permission_edit = Permission.objects.get(codename='can_edit_education_group_administrative_data')
        self.person.user.user_permissions.add(self.permission_edit)

        self.education_group_year = EducationGroupYearFactory()
        self.program_manager = ProgramManagerFactory(person=self.person,
                                                     education_group=self.education_group_year.education_group)

        self.url = reverse('education_group_administrative', args=[
            self.education_group_year.id, self.education_group_year.id
        ])
        self.client.force_login(self.person.user)

    def test_when_not_logged(self):
        self.client.logout()
        response = self.client.get(self.url)

        self.assertRedirects(response, '/login/?next={}'.format(self.url))

    def test_user_has_not_permission(self):
        Group.objects.get(name="program_managers").permissions.remove(self.permission_access)
        self.person.user.user_permissions.remove(self.permission_access)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)
        self.assertTemplateUsed(response, "access_denied.html")

    def test_user_is_not_program_manager_of_education_group(self):
        self.program_manager.delete()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HttpResponse.status_code)
        self.assertTemplateUsed(response, "education_group/tab_administrative_data.html")

        self.assertFalse(response.context["can_edit_administrative_data"])

    def test_user_has_no_permission_to_edit_administrative_data(self):
        self.person.user.user_permissions.remove(self.permission_edit)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HttpResponse.status_code)
        self.assertTemplateUsed(response, "education_group/tab_administrative_data.html")

        self.assertFalse(response.context["can_edit_administrative_data"])

    def test_education_group_non_existent(self):
        self.education_group_year.delete()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HttpResponseNotFound.status_code)
        self.assertTemplateUsed(response, "page_not_found.html")

    def test_with_education_group_year_of_type_mini_training(self):
        mini_training_education_group_year = EducationGroupYearFactory()
        mini_training_education_group_year.education_group_type.category = education_group_categories.MINI_TRAINING
        mini_training_education_group_year.education_group_type.save()

        url = reverse("education_group_administrative",
                      args=[mini_training_education_group_year.id, mini_training_education_group_year.id])
        response = self.client.get(url)

        self.assertTemplateUsed(response, "access_denied.html")
        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)

    def test_with_education_group_year_of_type_group(self):
        group_education_group_year = EducationGroupYearFactory()
        group_education_group_year.education_group_type.category = education_group_categories.GROUP
        group_education_group_year.education_group_type.save()

        url = reverse("education_group_administrative",
                      args=[group_education_group_year.id, group_education_group_year.id])
        response = self.client.get(url)

        self.assertTemplateUsed(response, "access_denied.html")
        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)

    def test_user_can_edit_administrative_data(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HttpResponse.status_code)
        self.assertTemplateUsed(response, "education_group/tab_administrative_data.html")

        self.assertTrue(response.context["can_edit_administrative_data"])


@override_flag('education_group_update', active=True)
class EducationGroupYearEditPedagogy(TestCase):
    def setUp(self):
        self.person = PersonFactory()

        self.permission = Permission.objects.get(codename='can_edit_educationgroup_pedagogy')
        self.person.user.user_permissions.add(self.permission)

        self.education_group_year = EducationGroupYearFactory()

        self.url = reverse('education_group_pedagogy_edit',
                           args=[self.education_group_year.id, self.education_group_year.id])
        self.client.force_login(self.person.user)

    def test_when_not_logged(self):
        self.client.logout()

        response = self.client.get(self.url)
        self.assertRedirects(response, '/login/?next={}'.format(self.url))

    def test_user_has_not_permission(self):
        self.person.user.user_permissions.remove(self.permission)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)
        self.assertTemplateUsed(response, "access_denied.html")

    def test_user_has_permission(self):
        text_label = TextLabelFactory(entity=entity_name.OFFER_YEAR)

        url = "{}?label={}&language={}".format(self.url, text_label.label, self.person.language)
        response = self.client.get(url)

        self.assertEqual(response.status_code, HttpResponse.status_code)
        self.assertTemplateUsed(response, "education_group/pedagogy_edit.html")

        soup = bs4.BeautifulSoup(response.content, 'html.parser')
        self.assertEqual(soup.div.form['action'], self.url)


@override_flag('education_group_update', active=True)
class EducationGroupEditAdministrativeData(TestCase):
    def setUp(self):
        self.person = PersonFactory()

        self.permission = Permission.objects.get(codename='can_edit_education_group_administrative_data')
        self.person.user.user_permissions.add(self.permission)

        self.education_group_year = EducationGroupYearFactory()
        self.program_manager = ProgramManagerFactory(person=self.person,
                                                     education_group=self.education_group_year.education_group)
        self.url = reverse('education_group_edit_administrative',
                           args=[self.education_group_year.id, self.education_group_year.id])
        self.client.force_login(self.person.user)

    def test_when_not_logged(self):
        self.client.logout()
        response = self.client.get(self.url)

        self.assertRedirects(response, '/login/?next={}'.format(self.url))

    def test_user_has_not_permission(self):
        self.person.user.user_permissions.remove(self.permission)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)
        self.assertTemplateUsed(response, "access_denied.html")

    def test_user_is_not_program_manager_of_education_group(self):
        self.program_manager.delete()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)
        self.assertTemplateUsed(response, "access_denied.html")

    def test_education_group_non_existent(self):
        self.education_group_year.delete()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HttpResponseNotFound.status_code)
        self.assertTemplateUsed(response, "page_not_found.html")

    def test_with_education_group_year_of_type_mini_training(self):
        mini_training_education_group_year = EducationGroupYearFactory()
        mini_training_education_group_year.education_group_type.category = education_group_categories.MINI_TRAINING
        mini_training_education_group_year.education_group_type.save()

        url = reverse("education_group_edit_administrative",
                      args=[mini_training_education_group_year.id, mini_training_education_group_year.id])
        response = self.client.get(url)

        self.assertTemplateUsed(response, "access_denied.html")
        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)

    def test_with_education_group_year_of_type_group(self):
        group_education_group_year = EducationGroupYearFactory()
        group_education_group_year.education_group_type.category = education_group_categories.GROUP
        group_education_group_year.education_group_type.save()

        url = reverse("education_group_edit_administrative",
                      args=[group_education_group_year.id, group_education_group_year.id])
        response = self.client.get(url)

        self.assertTemplateUsed(response, "access_denied.html")
        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)


class WebServiceForManagementTermsEducationGroupYear(TestCase):
    def setUp(self):
        user = SuperUserFactory()

        self.client.force_login(user)

    def test_get_no_terms(self):
        kwargs = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        education_group_year = EducationGroupYearFactory()

        url = reverse('education_group_pedagogy_get_terms', kwargs={
            'root_id': education_group_year.pk,
            'education_group_year_id': education_group_year.id,
            'language': 'fr-be'
        })

        response = self.client.get(url, **kwargs)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertDictEqual(response_json, {'records': []})

    def test_get_terms(self):
        kwargs = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        education_group_year = EducationGroupYearFactory()

        text_label=TextLabelFactory(entity='offer_year')
        translated_text_label = TranslatedTextLabelFactory(text_label=text_label, language='fr-be')

        url = reverse('education_group_pedagogy_get_terms', kwargs={
            'root_id': education_group_year.pk,
            'education_group_year_id': education_group_year.id,
            'language': 'fr-be'
        })

        response = self.client.get(url, **kwargs)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertDictEqual(response_json, {'records': [
            {'id': translated_text_label.id,
             'language': translated_text_label.language,
             'label': translated_text_label.text_label.label,
             'translation': translated_text_label.label}
        ]})

    def test_add_term(self):
        kwargs = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        education_group_year = EducationGroupYearFactory()

        text_label = TextLabelFactory(entity='offer_year', label='label')
        translated_text_label_fr = TranslatedTextLabelFactory(text_label=text_label, language='fr-be')
        translated_text_label_en = TranslatedTextLabelFactory(text_label=text_label, language='en')

        url = reverse('education_group_pedagogy_add_term', kwargs={
            'root_id': education_group_year.pk,
            'education_group_year_id': education_group_year.id,
        })

        translated_texts = TranslatedText.objects.filter(reference=str(education_group_year.id),
                                                         entity='offer_year',
                                                         text_label=text_label)

        self.assertEqual(translated_texts.count(), 0)

        response = self.client.post(url + "?label={}".format(text_label.label), **kwargs)

        self.assertEqual(response.status_code, 200)

        response_json = response.json()

        self.assertDictEqual(response_json, {
            'message': 'added',
            'translated_texts': {
                'label': text_label.label,
                'fr-be': {
                    'id': translated_text_label_fr.id,
                    'translation': translated_text_label_fr.label,
                },
                'en': {
                    'id': translated_text_label_en.id,
                    'translation': translated_text_label_en.label,
                }
            }
        })

        translated_texts = TranslatedText.objects.filter(reference=str(education_group_year.id),
                                                         entity='offer_year',
                                                         text_label=text_label)

        self.assertEqual(translated_texts.count(), 2)

    def test_remove_term(self):
        kwargs = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        education_group_year = EducationGroupYearFactory()

        text_label = TextLabelFactory(entity='offer_year', label='label')

        for language in ('fr-be', 'en'):
            TranslatedTextRandomFactory(text_label=text_label, language=language,
                                        reference=str(education_group_year.id), entity=text_label.entity)

        url = reverse('education_group_pedagogy_remove_term', kwargs={
            'root_id': education_group_year.id,
            'education_group_year_id': education_group_year.id,
        })

        response = self.client.delete(url + "?label={}".format(text_label.label), **kwargs)

        self.assertEqual(response.status_code, 200)

        response_json = response.json()

        self.assertDictEqual(response_json, {'education_group_year': education_group_year.id})


class EducationGroupAdmissionConditionWSTest(TestCase):
    def setUp(self):
        user = SuperUserFactory()

        self.client.force_login(user)

    def test_ws_add_line(self):
        kwargs = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        education_group_year = EducationGroupYearFactory(acronym='actu2m')

        url = reverse('education_group_year_admission_condition_add_line',
                      args=[education_group_year.pk, education_group_year.pk]
                      )
        data = {
            'language': 'fr',
            'section': 'ucl_bachelors',
            'diploma': 'Diplome',
            'conditions': '',
            'access': 'Access',
            'remarks': 'Remarks',
        }

        response = self.client.post(url, data=json.dumps(data), content_type='application/json',
                                    **kwargs)

        self.assertEqual(response.status_code, 200)

        response_json = response.json()

        self.assertEqual(response_json['message'], 'added')
        response_json['record'].pop('id')

        self.assertDictEqual(response_json['record'], {
            'section': data['section'],
            'diploma': data['diploma'],
            'conditions': data['conditions'],
            'access': data['access'],
            'remarks': data['remarks']
        })

    def test_ws_remove_line(self):
        kwargs = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        education_group_year = EducationGroupYearFactory(acronym='actu2m')
        admission_condition = AdmissionCondition.objects.create(education_group_year=education_group_year)
        self.assertEqual(AdmissionConditionLine.objects.filter(admission_condition=admission_condition).count(), 0)
        admission_condition_line = AdmissionConditionLine.objects.create(admission_condition=admission_condition,
                                                                         section='ucl_bachelors',
                                                                         diploma='Diploma',
                                                                         conditions='',
                                                                         access='Access',
                                                                         remarks='Remarks')
        self.assertEqual(AdmissionConditionLine.objects.filter(admission_condition=admission_condition).count(), 1)

        data = {
            'id': admission_condition_line.id,
        }

        url = reverse('education_group_year_admission_condition_remove_line', kwargs={
            'root_id': education_group_year.id,
            'education_group_year_id': education_group_year.id,
        })

        response = self.client.post(url, data=json.dumps(data), content_type='application/json', **kwargs)

        self.assertEqual(response.status_code, 200)

        response_json = response.json()

        self.assertEqual(response_json['message'], 'deleted')
        self.assertEqual(AdmissionConditionLine.objects.filter(admission_condition=admission_condition).count(), 0)

    def test_ws_update_line(self):
        kwargs = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        education_group_year = EducationGroupYearFactory(acronym='actu2m')
        admission_condition = AdmissionCondition.objects.create(education_group_year=education_group_year)
        self.assertEqual(AdmissionConditionLine.objects.filter(admission_condition=admission_condition).count(), 0)
        admission_condition_line = AdmissionConditionLine.objects.create(admission_condition=admission_condition,
                                                                         section='ucl_bachelors',
                                                                         diploma='Diploma',
                                                                         conditions='',
                                                                         access='Access',
                                                                         remarks='Remarks')
        self.assertEqual(AdmissionConditionLine.objects.filter(admission_condition=admission_condition).count(), 1)

        data = {
            'id': admission_condition_line.id,
            'language': 'fr',
            'section': admission_condition_line.section,
            'diploma': 'New Diploma',
            'conditions': 'New Conditions',
            'access': 'New Access',
            'remarks': 'New Remarques',
        }

        url = reverse('education_group_year_admission_condition_update_line', kwargs={
            'root_id': education_group_year.id,
            'education_group_year_id': education_group_year.id,
        })

        response = self.client.post(url, data=json.dumps(data), content_type='application/json', **kwargs)

        self.assertEqual(response.status_code, 200)

        response_json = response.json()

        self.assertEqual(response_json['message'], 'updated')
        self.assertEqual(AdmissionConditionLine.objects.filter(admission_condition=admission_condition).count(), 1)

        checked_response = dict(data, message='updated')
        checked_response.pop('language')

        self.assertDictEqual(response_json, checked_response)

    def test_ws_get_text(self):
        kwargs = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        education_group_year = EducationGroupYearFactory(acronym='actu2m')
        admission_condition = AdmissionCondition.objects.create(
            education_group_year=education_group_year,
            text_bachelor='ceci est un test',
            text_bachelor_en='this is a test',
        )

        url = reverse('education_group_year_admission_condition_get_text', kwargs={
            'root_id': education_group_year.id,
            'education_group_year_id': education_group_year.id,
        })

        data = {
            'section': 'bachelor',
            'language': 'fr',
        }
        response = self.client.post(url, data=json.dumps(data), content_type='application/json', **kwargs)

        self.assertEqual(response.status_code, 200)

        response_json = response.json()

        self.assertDictEqual(response_json, {
            'message': 'read',
            'section': 'bachelor',
            'text': admission_condition.text_bachelor,
        })

        data = {
            'section': 'bachelor',
            'language': 'en',
        }
        response = self.client.post(url, data=json.dumps(data), content_type='application/json', **kwargs)

        self.assertEqual(response.status_code, 200)

        response_json = response.json()

        self.assertDictEqual(response_json, {
            'message': 'read',
            'section': 'bachelor',
            'text': admission_condition.text_bachelor_en,
        })

    def test_ws_modify_text(self):
        kwargs = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        education_group_year = EducationGroupYearFactory(acronym='actu2m')
        admission_condition = AdmissionCondition.objects.create(
            education_group_year=education_group_year,
            text_bachelor='ceci est un test',
            text_bachelor_en='this is a test',
        )

        url = reverse('education_group_year_admission_condition_modify_text', kwargs={
            'root_id': education_group_year.id,
            'education_group_year_id': education_group_year.id,
        })

        data = {
            'section': 'bachelor',
            'language': 'fr',
            'text': 'ceci est un second test'
        }
        response = self.client.post(url, data=json.dumps(data), content_type='application/json', **kwargs)

        self.assertEqual(response.status_code, 200)

        response_json = response.json()

        self.assertDictEqual(response_json, {
            'message': 'updated',
            'text': data['text'],
        })

        admission_condition.refresh_from_db()

        self.assertEqual(admission_condition.text_bachelor, data['text'])

        data = {
            'section': 'bachelor',
            'language': 'en',
            'text': 'this is a second test'
        }
        response = self.client.post(url, data=json.dumps(data), content_type='application/json', **kwargs)

        self.assertEqual(response.status_code, 200)

        response_json = response.json()

        self.assertDictEqual(response_json, {
            'message': 'updated',
            'text': data['text'],
        })

        admission_condition.refresh_from_db()

        self.assertEqual(admission_condition.text_bachelor_en, data['text'])

    def test_ws_get_line(self):
        kwargs = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        education_group_year = EducationGroupYearFactory(acronym='actu2m')

        admission_condition = AdmissionCondition.objects.create(education_group_year=education_group_year)
        admission_condition_line = AdmissionConditionLine.objects.create(admission_condition=admission_condition,
                                                                         section='ucl_bachelors',
                                                                         diploma='Diplome',
                                                                         conditions='Conditions',
                                                                         access='Acces',
                                                                         remarks='Remarks'
                                                                         )

        url = reverse('education_group_year_admission_condition_get_line', kwargs={
            'root_id': education_group_year.id,
            'education_group_year_id': education_group_year.id,
        })

        data = {
            'id': admission_condition_line.id,
            'language': 'fr',
            'section': admission_condition_line.section,
        }

        response = self.client.post(url, data=json.dumps(data), content_type='application/json', **kwargs)

        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertDictEqual(response_json, {
            'message': 'read',
            'section': admission_condition_line.section,
            'id': admission_condition_line.id,
            'diploma': admission_condition_line.diploma,
            'conditions': admission_condition_line.conditions,
            'access': admission_condition_line.access,
            'remarks': admission_condition_line.remarks
        })
