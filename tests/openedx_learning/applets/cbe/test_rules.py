"""
Tests for the CBE permission predicates and their registration.

Fixtures live in this directory's conftest.py.
"""
import pytest
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.models import User as UserType  # pylint: disable=imported-auth-user

from openedx_learning.applets.cbe.rules import can_view_competency_rule_profile
from openedx_learning.models import CompetencyRuleProfile, CompetencyTaxonomy, RuleType

pytestmark = pytest.mark.django_db

VIEW_RULE_PROFILE = "openedx_learning.view_competencyruleprofile"

# A valid payload for the rows these tests create themselves.
GRADE_PAYLOAD = {"op": "gte", "value": 0.6, "scale": "percent"}


def test_staff_may_view_rule_profiles(staff_user: UserType) -> None:
    """A user who may administer taxonomies may read rule profiles."""
    assert can_view_competency_rule_profile(staff_user) is True


def test_non_staff_may_view_rule_profiles(user: UserType) -> None:
    """The Competency Management page is a course author's, so reading profiles is not staff-only."""
    assert can_view_competency_rule_profile(user) is True


def test_anonymous_is_refused_by_the_endpoint_rather_than_by_this_predicate() -> None:
    """
    With no taxonomy to withhold, ``view_taxonomy`` says yes to any caller, and the predicate
    repeats that answer rather than inventing a second rule. Authentication is what turns an
    anonymous request away, so test_views.py asserts that against the endpoint.
    """
    assert can_view_competency_rule_profile(AnonymousUser()) is True


def test_staff_and_non_staff_alike_may_view_the_instance_wide_default(
    staff_user: UserType,
    user: UserType,
    default_rule_profile: CompetencyRuleProfile,
) -> None:
    """The default carries no taxonomy, so there is nothing for ``view_taxonomy`` to withhold."""
    assert can_view_competency_rule_profile(staff_user, default_rule_profile) is True
    assert can_view_competency_rule_profile(user, default_rule_profile) is True


def test_a_profile_on_a_disabled_taxonomy_stays_administrator_only(
    staff_user: UserType,
    user: UserType,
) -> None:
    """
    A disabled taxonomy is where ``view_taxonomy`` and "everyone" part company, so a profile
    scoped to one is what shows the delegation is real: the same non-staff user who may read
    the instance-wide default is refused this profile.
    """
    disabled_taxonomy = CompetencyTaxonomy.objects.create(name="Retired", export_id="retired-v1", enabled=False)
    profile = CompetencyRuleProfile.objects.create(
        competency_taxonomy=disabled_taxonomy,
        rule_type=RuleType.GRADE,
        rule_payload=dict(GRADE_PAYLOAD),
    )

    assert can_view_competency_rule_profile(user, profile) is False
    assert can_view_competency_rule_profile(staff_user, profile) is True


def test_permission_is_registered_for_the_django_permission_check(staff_user: UserType, user: UserType) -> None:
    """
    The predicate answers has_perm() under the name DRF's perms_map builds, which is what
    proves src/openedx_learning/rules.py reached the registry: an unregistered name is refused
    to everyone, so a single True here could not happen without it.
    """
    assert staff_user.has_perm(VIEW_RULE_PROFILE) is True
    assert user.has_perm(VIEW_RULE_PROFILE) is True
