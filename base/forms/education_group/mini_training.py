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

from base.forms.education_group.common import CommonBaseForm, EducationGroupModelForm, EducationGroupYearModelForm
from base.models.education_group_year import EducationGroupYear
from base.models.enums import education_group_categories


class MiniTrainingModelForm(EducationGroupYearModelForm):
    category = education_group_categories.MINI_TRAINING

    class Meta(EducationGroupYearModelForm.Meta):
        model = EducationGroupYear
        fields = ("acronym", "partial_acronym", "education_group_type", "title", "title_english", "credits", "active",
                  "main_teaching_campus", "academic_year", "remark", "remark_english", "min_credits", "max_credits",
                  "schedule_type", "management_entity", "keywords")


class MiniTrainingForm(CommonBaseForm):

    def __init__(self, data, instance=None, parent=None):
        education_group_year_form = MiniTrainingModelForm(data, instance=instance, parent=parent)
        education_group = instance.education_group if instance else None
        education_group_form = EducationGroupModelForm(data, instance=education_group)
        super(MiniTrainingForm, self).__init__(education_group_year_form, education_group_form)
