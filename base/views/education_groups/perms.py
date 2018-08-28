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
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from base.business.education_groups import perms as business_perms
from base.models import person
from base.models.education_group_year import EducationGroupYear


def can_create_education_group(view_func):
    def f_can_create_education_group(request, *args, **kwargs):
        pers = get_object_or_404(person.Person, user=request.user)

        parent_id = kwargs.get("parent_id")
        parent = get_object_or_404(EducationGroupYear, pk=parent_id) if parent_id else None

        if not business_perms.is_eligible_to_add_education_group(pers, parent, raise_exception=True):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return f_can_create_education_group


def can_change_education_group(user, education_group):
    pers = get_object_or_404(person.Person, user=user)
    if not business_perms.is_eligible_to_change_education_group(pers, education_group, raise_exception=True):
        raise PermissionDenied
    return True


def can_delete_education_group(user, education_group):
    pers = get_object_or_404(person.Person, user=user)
    if not business_perms.is_eligible_to_delete_education_group(pers, education_group, raise_exception=True):
        raise PermissionDenied
    return True
