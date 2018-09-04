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
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect
from django.urls import reverse

from base.forms.search.search_tutor import TutorSearchForm
from base.models.tutor import Tutor
from base.views import layout
from base.views.common import paginate_queryset
from base.utils.cache import delete_filter_from_cache


@login_required
@permission_required('base.can_access_learningunit', raise_exception=True)
def search_tutors(request):
    tutors_qs = Tutor.objects.none()
    form = TutorSearchForm(data=request.GET)

    if form.is_valid():
        tutors_qs = form.search()

    tutors = paginate_queryset(tutors_qs, request.GET)

    return layout.render(request, "search/search.html", {
        "form": form,
        "tutors": tutors
    })


@login_required
@permission_required('base.can_access_learningunit', raise_exception=True)
@delete_filter_from_cache()
def reset_filter_by_activity(request):
    return redirect(reverse("learning_units"))


@login_required
@permission_required('base.can_access_learningunit', raise_exception=True)
@delete_filter_from_cache()
def reset_filter_by_service_course(request):
    return redirect(reverse("learning_units_service_course"))


@login_required
@permission_required('base.can_access_learningunit', raise_exception=True)
@delete_filter_from_cache()
def reset_filter_by_proposal(request):
    return redirect(reverse("learning_units_proposal"))


@login_required
@permission_required('base.can_access_learningunit', raise_exception=True)
@delete_filter_from_cache()
def reset_filter_by_borrowed_course(request):
    return redirect(reverse("learning_units_borrowed_course"))


@login_required
@permission_required('base.can_access_learningunit', raise_exception=True)
@delete_filter_from_cache()
def reset_filter_by_external(request):
    return redirect(reverse("learning_units_external"))


@login_required
@permission_required('base.can_access_learningunit', raise_exception=True)
@delete_filter_from_cache()
def reset_filter_by_summary(request):
    return redirect(reverse("learning_units_summary"))


@login_required
@permission_required('base.can_access_education_group', raise_exception=True)
@delete_filter_from_cache()
def reset_education_group_filter(request):
    return redirect(reverse("education_groups"))
