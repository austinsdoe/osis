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
from datetime import timedelta

from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, pgettext

from base.models.enums.academic_calendar_type import EDUCATION_GROUP_EDITION
from base.models.enums.education_group_categories import TRAINING, MINI_TRAINING, GROUP
from base.templatetags.education_group import li_with_deletion_perm, button_with_permission, BUTTON_TEMPLATE, \
    button_order_with_permission, BUTTON_ORDER_TEMPLATE, li_with_create_perm_training, \
    li_with_create_perm_mini_training, li_with_create_perm_group, link_detach_education_group, \
    link_pdf_content_education_group, button_edit_administrative_data
from base.tests.factories.academic_calendar import AcademicCalendarFactory
from base.tests.factories.academic_year import create_current_academic_year, AcademicYearFactory
from base.tests.factories.authorized_relationship import AuthorizedRelationshipFactory
from base.tests.factories.education_group_year import TrainingFactory, MiniTrainingFactory
from base.tests.factories.person import FacultyManagerFactory, CentralManagerFactory
from base.tests.factories.person_entity import PersonEntityFactory

DELETE_MSG = _("delete education group")
PERMISSION_DENIED_MSG = _("The education group edition period is not open.")
UNAUTHORIZED_TYPE_MSG = "No type of %(child_category)s can be created as child of %(category)s of type %(type)s"

DISABLED_LI = """
<li class="disabled" id="{}">
    <a href="#" data-toggle="tooltip" title="{}">{}</a>
</li>
"""

ENABLED_LI = """
<li class="" id="{}">
    <a href="{}" data-toggle="tooltip" title="">{}</a>
</li>
"""

CUSTOM_LI_TEMPLATE = """
    <li {li_attributes}>
        <a {a_attributes} data-toggle="tooltip">{text}</a>
    </li>
"""


class TestEducationGroupAsCentralManagerTag(TestCase):
    """ This class will test the tag as central manager """
    def setUp(self):
        self.education_group_year = TrainingFactory()
        self.person = CentralManagerFactory("delete_educationgroup", "change_educationgroup", "add_educationgroup")
        PersonEntityFactory(person=self.person, entity=self.education_group_year.management_entity)

        self.url = reverse('delete_education_group', args=[self.education_group_year.id, self.education_group_year.id])
        self.client.force_login(user=self.person.user)
        self.context = {
            "person": self.person,
            "education_group_year": self.education_group_year,
            "request": RequestFactory().get("")
        }

    def test_li_with_deletion_perm(self):
        result = li_with_deletion_perm(self.context, self.url, DELETE_MSG)
        self.assertEqual(result, ENABLED_LI.format("link_delete", self.url, DELETE_MSG))

    def test_button_with_permission(self):
        result = button_with_permission(self.context, "title", "id", "edit")
        self.assertEqual(result, BUTTON_TEMPLATE.format("title", "id", "", "fa-edit"))

    def test_button_order_with_permission(self):
        result = button_order_with_permission(self.context, "title", "id", "edit")
        self.assertEqual(result, BUTTON_ORDER_TEMPLATE.format("title", "id", "edit", "", "fa-edit"))

    def test_li_with_create_perm_training(self):
        relation = AuthorizedRelationshipFactory(parent_type=self.education_group_year.education_group_type)
        relation.child_type.category = TRAINING
        relation.child_type.save()

        result = li_with_create_perm_training(self.context, self.url, "")
        self.assertHTMLEqual(result, ENABLED_LI.format("link_create_training", self.url, ""))

    def test_li_with_create_perm_mini_training(self):
        relation = AuthorizedRelationshipFactory(parent_type=self.education_group_year.education_group_type)
        relation.child_type.category = MINI_TRAINING
        relation.child_type.save()

        result = li_with_create_perm_mini_training(self.context, self.url, "")
        self.assertHTMLEqual(result, ENABLED_LI.format("link_create_mini_training", self.url, ""))

    def test_li_with_create_perm_group(self):
        relation = AuthorizedRelationshipFactory(parent_type=self.education_group_year.education_group_type)
        relation.child_type.category = GROUP
        relation.child_type.save()

        result = li_with_create_perm_group(self.context, self.url, "")
        self.assertHTMLEqual(result, ENABLED_LI.format("link_create_group", self.url, ""))

    def test_li_with_create_perm_training_disabled(self):
        result = li_with_create_perm_training(self.context, self.url, "")

        msg = pgettext("female", UNAUTHORIZED_TYPE_MSG) % {
            "child_category": _(TRAINING),
            "category": _(self.education_group_year.education_group_type.category),
            "type": self.education_group_year.education_group_type.name
        }
        msg = msg.capitalize()
        self.assertHTMLEqual(result, DISABLED_LI.format("link_create_training", msg, ""))

    def test_li_with_create_perm_mini_training_disabled(self):
        result = li_with_create_perm_mini_training(self.context, self.url, "")
        msg = pgettext("female", UNAUTHORIZED_TYPE_MSG) % {
            "child_category": _(MINI_TRAINING),
            "category": _(self.education_group_year.education_group_type.category),
            "type": self.education_group_year.education_group_type.name
        }
        msg = msg.capitalize()
        self.assertHTMLEqual(result, DISABLED_LI.format("link_create_mini_training", msg, ""))

    def test_li_with_create_perm_group_disabled(self):
        result = li_with_create_perm_group(self.context, self.url, "")
        msg = pgettext("female", UNAUTHORIZED_TYPE_MSG) % {
            "child_category": _(GROUP),
            "category": _(self.education_group_year.education_group_type.category),
            "type": self.education_group_year.education_group_type.name
        }
        msg = msg.capitalize()
        self.assertHTMLEqual(result, DISABLED_LI.format("link_create_group", msg, ""))

    def test_tag_detach_education_group_permitted_and_possible(self):
        self.context['can_change_education_group'] = True
        self.context['group_to_parent'] = '1'
        result = link_detach_education_group(self.context)
        expected_result = CUSTOM_LI_TEMPLATE.format(
            li_attributes="""id="btn_operation_detach_1" """,
            a_attributes=""" href="#" title="{}" onclick="select()" """.format(_('Detach')),
            text=_('Detach'),
        )
        self.assertHTMLEqual(result, expected_result)

    def test_tag_detach_education_group_not_permitted(self):
        self.context['can_change_education_group'] = False
        self.context['group_to_parent'] = '1'
        result = link_detach_education_group(self.context)
        expected_result = CUSTOM_LI_TEMPLATE.format(
            li_attributes=""" class="disabled" """,
            a_attributes=""" title="{}" """.format(_("The user has not permission to change education groups.")),
            text=_('Detach'),
        )
        self.assertHTMLEqual(result, expected_result)

    def test_tag_detach_education_group_not_possible(self):
        self.context['can_change_education_group'] = True
        self.context['group_to_parent'] = '0'
        result = link_detach_education_group(self.context)
        expected_result = CUSTOM_LI_TEMPLATE.format(
            li_attributes=""" class="disabled" """,
            a_attributes=""" title=" {}" """.format(_("It is not possible to detach the root element.")),
            text=_('Detach'),
        )
        self.assertHTMLEqual(result, expected_result)

    def test_tag_detach_education_group_not_permitted_nor_possible(self):
        self.context['can_change_education_group'] = False
        self.context['group_to_parent'] = '0'
        result = link_detach_education_group(self.context)
        expected_result = CUSTOM_LI_TEMPLATE.format(
            li_attributes=""" class="disabled" """,
            a_attributes=""" title="{} {}" """.format(
                _("The user has not permission to change education groups."),
                _("It is not possible to detach the root element."),
            ),
            text=_('Detach'),
        )
        self.assertHTMLEqual(result, expected_result)

    def test_tag_link_pdf_content_education_group_not_permitted(self):
        result = link_pdf_content_education_group(self.context)
        expected_result = CUSTOM_LI_TEMPLATE.format(
            li_attributes=""" id="btn_operation_pdf_content" """,
            a_attributes=""" href="#" title="{}" {} """.format(
                _("Generate pdf"),
                _(""), ),
            text=_('Generate pdf'),
        )
        self.assertHTMLEqual(result, expected_result)


class TestEducationGroupAsFacultyManagerTag(TestCase):
    """ This class will test the tag as faculty manager """
    def setUp(self):
        self.education_group_year = TrainingFactory()
        self.person = FacultyManagerFactory("delete_educationgroup", "change_educationgroup", "add_educationgroup")
        PersonEntityFactory(person=self.person, entity=self.education_group_year.management_entity)

        current_ac = create_current_academic_year()

        # Create an academic calendar in order to check permission [Faculty can modify when period is opened]
        self.academic_calendar = AcademicCalendarFactory(
            reference=EDUCATION_GROUP_EDITION,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=+1),
            academic_year=current_ac,
        )

        self.next_ac = AcademicYearFactory(year=current_ac.year + 1)

        self.client.force_login(user=self.person.user)
        self.url = reverse('delete_education_group', args=[self.education_group_year.id, self.education_group_year.id])
        self.context = {
            "person": self.person,
            "root": self.education_group_year,
            "education_group_year": self.education_group_year,
            "request": RequestFactory().get("")
        }

    def test_button_tag_case_not_in_education_group_edition_period(self):
        """ This test ensure that as faculty manager, the button tag is disabled when outside of encoding period"""
        self.academic_calendar.delete()

        result = button_with_permission(self.context, "title", "id", "edit")
        self.assertEqual(result, BUTTON_TEMPLATE.format(PERMISSION_DENIED_MSG, "id", "disabled", "fa-edit"))

    def test_button_tag_case_inside_education_group_edition_period(self):
        self.education_group_year.academic_year = self.next_ac

        result = button_with_permission(self.context, "title", "id", "edit")
        self.assertEqual(result, BUTTON_TEMPLATE.format("title", "id", "", "fa-edit"))

    def test_li_tag_case_not_in_education_group_edition_period(self):
        """ This test ensure that as faculty manager, the li tag is disabled when outside of encoding period"""
        self.academic_calendar.delete()

        result = li_with_deletion_perm(self.context, self.url, DELETE_MSG)
        self.assertEqual(result, DISABLED_LI.format("link_delete", PERMISSION_DENIED_MSG, DELETE_MSG))

    def test_li_tag_case_inside_education_group_edition_period(self):
        self.education_group_year.academic_year = self.next_ac

        result = li_with_deletion_perm(self.context, self.url, DELETE_MSG)
        self.assertEqual(result, ENABLED_LI.format("link_delete", self.url, DELETE_MSG))

    def test_li_tag_case_mini_training_disabled(self):
        """
        This test ensure that as faculty manager, the li tag is disabled for mini training
        Faculty manager must enter in proposition mode for mini training
        """
        self.context['education_group_year'] = MiniTrainingFactory()
        result = li_with_create_perm_mini_training(self.context, self.url, "")
        msg = _("The user has not permission to create a %(category)s.") % {"category": _(MINI_TRAINING)}
        msg = msg.capitalize()
        self.assertHTMLEqual(result, DISABLED_LI.format("link_create_mini_training", msg, ""))

    def test_li_tag_case_training_disabled(self):
        """
        This test ensure that as faculty manager, the li tag is disabled for training
        Faculty manager must enter in proposition mode for training
        """
        self.context['education_group_year'] = TrainingFactory()
        result = li_with_create_perm_training(self.context, self.url, "")
        msg = _("The user has not permission to create a %(category)s.") % {"category": _(TRAINING)}
        msg = msg.capitalize()
        self.assertHTMLEqual(result, DISABLED_LI.format("link_create_training", msg, ""))

    def test_button_edit_administrative_data(self):
        result = button_edit_administrative_data(self.context)

        self.assertEqual(
            result["url"],
            reverse('education_group_edit_administrative', args=[
                self.education_group_year.pk,
                self.education_group_year.pk
            ])
        )

        self.assertEqual(
            result["message"],
            _('Only program managers of the education group OR central manager linked to entity can edit.')
        )

        self.assertEqual(result["is_disabled"], "disabled")
        self.assertEqual(result["text"], _("edit"))

