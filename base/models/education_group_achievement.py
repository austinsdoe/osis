##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2017 Université catholique de Louvain (http://www.uclouvain.be)
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
from django.utils.translation import ugettext_lazy as _
from django.db import models

from base.models.abstracts.abstract_achievement import AbstractAchievement, AbstractAchievementAdmin


class EducationGroupAchievementAdmin(AbstractAchievementAdmin):
    raw_id_fields = ('education_group_year',)

    def get_list_display(self, request):
        return ('education_group_year',) + super().get_list_display(request)

    def get_search_fields(self, request):
        return ['education_group_year__acronym'] + super().get_search_fields(request)


class EducationGroupAchievement(AbstractAchievement):
    education_group_year = models.ForeignKey(
        'EducationGroupYear',
        verbose_name=_("education group year"),
        on_delete=models.CASCADE,
    )
    order_with_respect_to = ('education_group_year', 'language')

    class Meta:
        unique_together = ("code_name", "education_group_year", "language")
        verbose_name = _("education group achievement")

    def __str__(self):
        return u'{} - {} (order {})'.format(self.education_group_year, self.code_name, self.order)
