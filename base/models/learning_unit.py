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
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.db.models import Max
from django.utils.translation import ugettext_lazy as _

from base.models.academic_year import current_academic_year, AcademicYear
from base.models.enums.learning_unit_year_subtypes import PARTIM, FULL
from osis_common.models.serializable_model import SerializableModelAdmin, SerializableModel

LEARNING_UNIT_ACRONYM_REGEX_BASE = "^[BLMWX][A-Z]{2,4}\d{4}"
LETTER_OR_DIGIT = "[A-Z0-9]"
STRING_END = "$"
LEARNING_UNIT_ACRONYM_REGEX_ALL = LEARNING_UNIT_ACRONYM_REGEX_BASE + LETTER_OR_DIGIT + "{0,1}" + STRING_END
LEARNING_UNIT_ACRONYM_REGEX_FULL = LEARNING_UNIT_ACRONYM_REGEX_BASE + STRING_END
LEARNING_UNIT_ACRONYM_REGEX_PARTIM = LEARNING_UNIT_ACRONYM_REGEX_BASE + LETTER_OR_DIGIT + STRING_END
LEARNING_UNIT_ACRONYM_REGEX_EXTERNAL = "^X[A-Z]{2,4}\d{4}$"

REGEX_BY_SUBTYPE = {
    PARTIM: LEARNING_UNIT_ACRONYM_REGEX_PARTIM,
    FULL: LEARNING_UNIT_ACRONYM_REGEX_FULL
}


class LearningUnitAdmin(SerializableModelAdmin):
    list_display = ('learning_container', 'acronym', 'title', 'start_year', 'end_year', 'changed')
    search_fields = ['learningunityear__acronym', 'learningunityear__specific_title', 'learning_container__external_id']
    list_filter = ('start_year',)


class LearningUnit(SerializableModel):
    existing_proposal_in_epc = models.BooleanField(default=False)
    external_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    learning_container = models.ForeignKey('LearningContainer', blank=True, null=True)
    changed = models.DateTimeField(null=True, auto_now=True)
    start_year = models.IntegerField(_('start_year'))
    end_year = models.IntegerField(blank=True, null=True, verbose_name=_('end_year_title'))
    # TODO is it useful?
    progress = None

    faculty_remark = models.TextField(blank=True, null=True, verbose_name=_('faculty_remark'))
    other_remark = models.TextField(blank=True, null=True, verbose_name=_('other_remark'))

    def __str__(self):
        return "{}".format(self.id)

    def save(self, *args, **kwargs):
        if self.end_year and self.end_year < self.start_year:
            raise AttributeError("Start date should be before the end date")
        super(LearningUnit, self).save(*args, **kwargs)

    @property
    def acronym(self):
        return self.most_recent_learning_unit_year().acronym

    @property
    def title(self):
        return self.most_recent_learning_unit_year().specific_title

    def delete(self, *args, **kwargs):
        if self.start_year < 2015:
            raise IntegrityError(_('Prohibition to delete a learning unit before 2015.'))
        return super().delete(*args, **kwargs)

    def is_past(self):
        return self.end_year and current_academic_year().year > self.end_year

    def most_recent_learning_unit_year(self):
        return self.learningunityear_set.filter(learning_unit_id=self.id).latest('academic_year__year')

    class Meta:
        permissions = (
            ("can_access_learningunit", "Can access learning unit"),
            ("can_edit_learningunit_date", "Can edit learning unit date"),
            ("can_edit_learningunit", "Can edit learning unit"),
            ("can_edit_learningunit_pedagogy", "Can edit learning unit pedagogy"),
            ("can_edit_learningunit_specification", "Can edit learning unit specification"),
            ("can_delete_learningunit", "Can delete learning unit"),
            ("can_propose_learningunit", "Can propose learning unit "),
            ("can_create_learningunit", "Can create learning unit"),
            ("can_consolidate_learningunit_proposal", "Can consolidate learning unit proposal"),
        )

    @property
    def parent(self):
        # TODO :: rename "parent" into "learning_unit_full"
        # TODO The subtype must move in learning_unit model !
        luy = self.learningunityear_set.last()
        if luy and luy.subtype == PARTIM:
            return LearningUnit.objects.filter(
                learningunityear__subtype=FULL, learning_container=self.learning_container
            ).last()
        return None

    @property
    def children(self):
        # TODO :: rename "children" into "partims"
        # TODO The subtype must move in learning_unit model !
        luy = self.learningunityear_set.last()
        if luy and luy.subtype == FULL:
            return LearningUnit.objects.filter(
                learningunityear__subtype=PARTIM, learning_container=self.learning_container
            )
        return []

    @property
    def max_end_year(self):
        """ Compute the maximal possible end_year value when the end_year is None """
        if self.end_year:
            return self.end_year

        return AcademicYear.objects.filter(learningunityear__learning_unit=self).aggregate(Max('year'))['year__max']


def find_by_id(learning_unit_id):
    return LearningUnit.objects.get(pk=learning_unit_id)


def find_by_ids(learning_unit_ids):
    return LearningUnit.objects.filter(pk__in=learning_unit_ids)
