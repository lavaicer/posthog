import json
from unittest.mock import MagicMock, patch
from rest_framework import status

from ee.api.test.base import APILicensedTest
from ee.models.rbac.role import Role, RoleMembership
from posthog.constants import AvailableFeature
from posthog.models.notebook.notebook import Notebook
from posthog.models.organization import OrganizationMembership
from posthog.models.team.team import Team
from posthog.utils import render_template


class BaseAccessControlTest(APILicensedTest):
    def setUp(self):
        super().setUp()
        self.organization.available_features = [
            AvailableFeature.PROJECT_BASED_PERMISSIONING,
            AvailableFeature.ROLE_BASED_ACCESS,
        ]
        self.organization.save()

        self.default_resource_id = self.team.id

    def _put_project_access_control(self, data={}):
        payload = {"access_level": "admin"}

        payload.update(data)

        return self.client.put(
            "/api/projects/@current/access_controls",
            payload,
        )

    def _org_membership(self, level: OrganizationMembership.Level = OrganizationMembership.Level.ADMIN):
        self.organization_membership.level = level
        self.organization_membership.save()


class TestAccessControlProjectLevelAPI(BaseAccessControlTest):
    def test_project_change_rejected_if_not_org_admin(self):
        self._org_membership(OrganizationMembership.Level.MEMBER)
        res = self._put_project_access_control()
        assert res.status_code == status.HTTP_403_FORBIDDEN, res.json()

    def test_project_change_accepted_if_org_admin(self):
        self._org_membership(OrganizationMembership.Level.ADMIN)
        res = self._put_project_access_control()
        assert res.status_code == status.HTTP_200_OK, res.json()

    def test_project_change_accepted_if_org_owner(self):
        self._org_membership(OrganizationMembership.Level.OWNER)
        res = self._put_project_access_control()
        assert res.status_code == status.HTTP_200_OK, res.json()

    def test_project_removed_with_null(self):
        self._org_membership(OrganizationMembership.Level.OWNER)
        res = self._put_project_access_control()
        res = self._put_project_access_control({"access_level": None})
        assert res.status_code == status.HTTP_204_NO_CONTENT

    def test_project_change_if_in_access_control(self):
        self._org_membership(OrganizationMembership.Level.ADMIN)
        # Add ourselves to access
        res = self._put_project_access_control(
            {"organization_member": str(self.organization_membership.id), "access_level": "admin"}
        )
        assert res.status_code == status.HTTP_200_OK, res.json()

        self._org_membership(OrganizationMembership.Level.MEMBER)

        # Now change ourselves to a member
        res = self._put_project_access_control(
            {"organization_member": str(self.organization_membership.id), "access_level": "member"}
        )
        assert res.status_code == status.HTTP_200_OK, res.json()
        assert res.json()["access_level"] == "member"

        # Now try and change our own membership and fail!
        res = self._put_project_access_control(
            {"organization_member": str(self.organization_membership.id), "access_level": "admin"}
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN
        assert res.json()["detail"] == "Must be admin to modify project permissions."

    def test_project_change_rejected_if_not_in_organization(self):
        self.organization_membership.delete()
        res = self._put_project_access_control(
            {"organization_member": str(self.organization_membership.id), "access_level": "admin"}
        )
        assert res.status_code == status.HTTP_404_NOT_FOUND, res.json()

    def test_project_change_rejected_if_bad_access_level(self):
        self._org_membership(OrganizationMembership.Level.ADMIN)
        res = self._put_project_access_control({"access_level": "bad"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST, res.json()
        assert res.json()["detail"] == "Invalid access level. Must be one of: none, member, admin", res.json()


class TestAccessControlResourceLevelAPI(BaseAccessControlTest):
    def setUp(self):
        super().setUp()

        self.notebook = Notebook.objects.create(
            team=self.team, created_by=self.user, short_id="0", title="first notebook"
        )

        self.other_user = self._create_user("other_user")
        self.other_user_notebook = Notebook.objects.create(
            team=self.team, created_by=self.other_user, short_id="1", title="first notebook"
        )

    def _get_access_controls(self, data={}):
        return self.client.get(f"/api/projects/@current/notebooks/{self.notebook.short_id}/access_controls")

    def _put_access_control(self, data={}, notebook_id=None):
        payload = {
            "access_level": "editor",
        }

        payload.update(data)
        return self.client.put(
            f"/api/projects/@current/notebooks/{notebook_id or self.notebook.short_id}/access_controls",
            payload,
        )

    def test_get_access_controls(self):
        self._org_membership(OrganizationMembership.Level.MEMBER)
        res = self._get_access_controls()
        assert res.status_code == status.HTTP_200_OK, res.json()
        assert res.json() == {
            "access_controls": [],
            "available_access_levels": ["none", "viewer", "editor"],
            "user_access_level": "editor",
            "default_access_level": "editor",
            "user_can_edit_access_levels": True,
        }

    def test_change_rejected_if_not_org_admin(self):
        self._org_membership(OrganizationMembership.Level.MEMBER)
        res = self._put_access_control(notebook_id=self.other_user_notebook.short_id)
        assert res.status_code == status.HTTP_403_FORBIDDEN, res.json()

    def test_change_accepted_if_org_admin(self):
        self._org_membership(OrganizationMembership.Level.ADMIN)
        res = self._put_access_control(notebook_id=self.other_user_notebook.short_id)
        assert res.status_code == status.HTTP_200_OK, res.json()

    def test_change_accepted_if_creator_of_the_resource(self):
        self._org_membership(OrganizationMembership.Level.MEMBER)
        res = self._put_access_control(notebook_id=self.notebook.short_id)
        assert res.status_code == status.HTTP_200_OK, res.json()


class TestRoleBasedAccessControls(BaseAccessControlTest):
    def setUp(self):
        super().setUp()

        self.role = Role.objects.create(name="Engineers", organization=self.organization)
        self.role_membership = RoleMembership.objects.create(user=self.user, role=self.role)

    def _put_rbac(self, data={}):
        payload = {"access_level": "editor"}
        payload.update(data)

        return self.client.put(
            "/api/projects/@current/role_based_access_controls",
            payload,
        )

    def test_admin_can_always_access(self):
        self._org_membership(OrganizationMembership.Level.ADMIN)
        assert self._put_rbac({"resource": "feature_flag", "access_level": "none"}).status_code == status.HTTP_200_OK
        assert self.client.get("/api/projects/@current/feature_flags").status_code == status.HTTP_200_OK

    def test_forbidden_access_if_resource_wide_control_in_place(self):
        self._org_membership(OrganizationMembership.Level.ADMIN)
        assert self._put_rbac({"resource": "feature_flag", "access_level": "none"}).status_code == status.HTTP_200_OK
        self._org_membership(OrganizationMembership.Level.MEMBER)

        assert self.client.get("/api/projects/@current/feature_flags").status_code == status.HTTP_403_FORBIDDEN
        assert self.client.post("/api/projects/@current/feature_flags").status_code == status.HTTP_403_FORBIDDEN

    def test_forbidden_write_access_if_resource_wide_control_in_place(self):
        self._org_membership(OrganizationMembership.Level.ADMIN)
        assert self._put_rbac({"resource": "feature_flag", "access_level": "viewer"}).status_code == status.HTTP_200_OK
        self._org_membership(OrganizationMembership.Level.MEMBER)

        assert self.client.get("/api/projects/@current/feature_flags").status_code == status.HTTP_200_OK
        assert self.client.post("/api/projects/@current/feature_flags").status_code == status.HTTP_403_FORBIDDEN

    def test_access_granted_with_granted_role(self):
        self._org_membership(OrganizationMembership.Level.ADMIN)
        assert self._put_rbac({"resource": "feature_flag", "access_level": "none"}).status_code == status.HTTP_200_OK
        assert (
            self._put_rbac({"resource": "feature_flag", "access_level": "viewer", "role": self.role.id}).status_code
            == status.HTTP_200_OK
        )
        self._org_membership(OrganizationMembership.Level.MEMBER)

        assert self.client.get("/api/projects/@current/feature_flags").status_code == status.HTTP_200_OK
        assert self.client.post("/api/projects/@current/feature_flags").status_code == status.HTTP_403_FORBIDDEN

        self.role_membership.delete()
        assert self.client.get("/api/projects/@current/feature_flags").status_code == status.HTTP_403_FORBIDDEN


class TestAccessControlPermissions(BaseAccessControlTest):
    """
    Test actual permissions being applied for a resource (notebooks as an example)
    """

    def setUp(self):
        super().setUp()
        self.other_user = self._create_user("other_user")

        self.other_user_notebook = Notebook.objects.create(
            team=self.team, created_by=self.other_user, title="not my notebook"
        )

        self.notebook = Notebook.objects.create(team=self.team, created_by=self.user, title="my notebook")

    def _post_notebook(self):
        return self.client.post("/api/projects/@current/notebooks/", {"title": "notebook"})

    def _patch_notebook(self, id: str):
        return self.client.patch(f"/api/projects/@current/notebooks/{id}", {"title": "new-title"})

    def _get_notebook(self, id: str):
        return self.client.get(f"/api/projects/@current/notebooks/{id}")

    def _put_notebook_access_control(self, notebook_id: str, data={}):
        payload = {
            "access_level": "editor",
        }

        payload.update(data)
        return self.client.put(
            f"/api/projects/@current/notebooks/{notebook_id}/access_controls",
            payload,
        )

    def test_default_allows_all_access(self):
        self._org_membership(OrganizationMembership.Level.MEMBER)
        assert self._get_notebook(self.other_user_notebook.short_id).status_code == status.HTTP_200_OK
        assert self._patch_notebook(id=self.other_user_notebook.short_id).status_code == status.HTTP_200_OK
        res = self._post_notebook()
        assert res.status_code == status.HTTP_201_CREATED
        assert self._patch_notebook(id=res.json()["short_id"]).status_code == status.HTTP_200_OK

    def test_rejects_all_access_without_project_access(self):
        self._org_membership(OrganizationMembership.Level.ADMIN)
        assert self._put_project_access_control({"access_level": "none"}).status_code == status.HTTP_200_OK
        self._org_membership(OrganizationMembership.Level.MEMBER)

        assert self._get_notebook(self.other_user_notebook.short_id).status_code == status.HTTP_403_FORBIDDEN
        assert self._patch_notebook(id=self.other_user_notebook.short_id).status_code == status.HTTP_403_FORBIDDEN
        assert self._post_notebook().status_code == status.HTTP_403_FORBIDDEN

    def test_permits_access_with_member_control(self):
        self._org_membership(OrganizationMembership.Level.ADMIN)
        assert self._put_project_access_control({"access_level": "none"}).status_code == status.HTTP_200_OK
        assert (
            self._put_project_access_control(
                {"access_level": "member", "organization_member": str(self.organization_membership.id)}
            ).status_code
            == status.HTTP_200_OK
        )
        self._org_membership(OrganizationMembership.Level.MEMBER)

        assert self._get_notebook(self.other_user_notebook.short_id).status_code == status.HTTP_200_OK
        assert self._patch_notebook(id=self.other_user_notebook.short_id).status_code == status.HTTP_200_OK
        assert self._post_notebook().status_code == status.HTTP_201_CREATED

    def test_rejects_edit_access_with_resource_control(self):
        self._org_membership(OrganizationMembership.Level.ADMIN)
        # Set other notebook to only allow view access by default
        assert (
            self._put_notebook_access_control(self.other_user_notebook.short_id, {"access_level": "viewer"}).status_code
            == status.HTTP_200_OK
        )
        self._org_membership(OrganizationMembership.Level.MEMBER)

        assert self._get_notebook(self.other_user_notebook.short_id).status_code == status.HTTP_200_OK
        assert self._patch_notebook(id=self.other_user_notebook.short_id).status_code == status.HTTP_403_FORBIDDEN
        assert self._post_notebook().status_code == status.HTTP_201_CREATED

    def test_rejects_view_access_if_not_creator(self):
        self._org_membership(OrganizationMembership.Level.ADMIN)
        # Set other notebook to only allow view access by default
        assert (
            self._put_notebook_access_control(self.other_user_notebook.short_id, {"access_level": "none"}).status_code
            == status.HTTP_200_OK
        )
        assert (
            self._put_notebook_access_control(self.notebook.short_id, {"access_level": "none"}).status_code
            == status.HTTP_200_OK
        )
        self._org_membership(OrganizationMembership.Level.MEMBER)

        # Access to other notebook is denied
        assert self._get_notebook(self.other_user_notebook.short_id).status_code == status.HTTP_403_FORBIDDEN
        assert self._patch_notebook(id=self.other_user_notebook.short_id).status_code == status.HTTP_403_FORBIDDEN
        # As creator, access to my notebook is still permitted
        assert self._get_notebook(self.notebook.short_id).status_code == status.HTTP_200_OK
        assert self._patch_notebook(id=self.notebook.short_id).status_code == status.HTTP_200_OK


class TestAccessControlFiltering(BaseAccessControlTest):
    def setUp(self):
        super().setUp()
        self.other_user = self._create_user("other_user")

        self.other_user_notebook = Notebook.objects.create(
            team=self.team, created_by=self.other_user, title="not my notebook"
        )

        self.notebook = Notebook.objects.create(team=self.team, created_by=self.user, title="my notebook")

    def _put_notebook_access_control(self, notebook_id: str, data={}):
        payload = {
            "access_level": "editor",
        }

        payload.update(data)
        return self.client.put(
            f"/api/projects/@current/notebooks/{notebook_id}/access_controls",
            payload,
        )

    def _get_notebooks(self):
        return self.client.get("/api/projects/@current/notebooks/")

    def test_default_allows_all_access(self):
        self._org_membership(OrganizationMembership.Level.MEMBER)
        assert len(self._get_notebooks().json()["results"]) == 2

    def test_does_not_list_notebooks_without_access(self):
        self._org_membership(OrganizationMembership.Level.ADMIN)
        assert (
            self._put_notebook_access_control(self.other_user_notebook.short_id, {"access_level": "none"}).status_code
            == status.HTTP_200_OK
        )
        assert (
            self._put_notebook_access_control(self.notebook.short_id, {"access_level": "none"}).status_code
            == status.HTTP_200_OK
        )
        self._org_membership(OrganizationMembership.Level.MEMBER)

        res = self._get_notebooks()
        assert len(res.json()["results"]) == 1
        assert res.json()["results"][0]["id"] == str(self.notebook.id)

    def test_list_notebooks_with_explicit_access(self):
        self._org_membership(OrganizationMembership.Level.ADMIN)
        assert (
            self._put_notebook_access_control(self.other_user_notebook.short_id, {"access_level": "none"}).status_code
            == status.HTTP_200_OK
        )
        assert (
            self._put_notebook_access_control(
                self.other_user_notebook.short_id,
                {"organization_member": str(self.organization_membership.id), "access_level": "viewer"},
            ).status_code
            == status.HTTP_200_OK
        )
        self._org_membership(OrganizationMembership.Level.MEMBER)

        res = self._get_notebooks()
        assert len(res.json()["results"]) == 2


class TestAccessControlProjectFiltering(BaseAccessControlTest):
    """
    Projects are listed in multiple places and ways so we need to test all of them here
    """

    def setUp(self):
        super().setUp()
        self.other_team = Team.objects.create(organization=self.organization, name="other team")
        self.other_team_2 = Team.objects.create(organization=self.organization, name="other team 2")

    def _put_project_access_control(self, team_id: str, data={}):
        self._org_membership(OrganizationMembership.Level.ADMIN)
        payload = {
            "access_level": "editor",
        }

        payload.update(data)
        res = self.client.put(
            f"/api/projects/{team_id}/access_controls",
            payload,
        )

        self._org_membership(OrganizationMembership.Level.MEMBER)

        assert res.status_code == status.HTTP_200_OK, res.json()
        return res

    def _get_posthog_app_context(self):
        mock_template = MagicMock()
        with patch("posthog.utils.get_template", return_value=mock_template):
            mock_request = MagicMock()
            mock_request.user = self.user
            mock_request.GET = {}
            render_template("index.html", request=mock_request, context={})

            # Get the context passed to the template
            return json.loads(mock_template.render.call_args[0][0]["posthog_app_context"])

    def test_default_lists_all_projects(self):
        assert len(self.client.get("/api/projects").json()["results"]) == 3
        me_response = self.client.get("/api/users/@me").json()
        assert len(me_response["organization"]["teams"]) == 3

    def test_does_not_list_projects_without_access(self):
        self._put_project_access_control(self.other_team.id, {"access_level": "none"})
        assert len(self.client.get("/api/projects").json()["results"]) == 2
        me_response = self.client.get("/api/users/@me").json()
        assert len(me_response["organization"]["teams"]) == 2

    def test_template_render_filters_teams(self):
        app_context = self._get_posthog_app_context()
        assert len(app_context["current_user"]["organization"]["teams"]) == 3
        assert app_context["current_team"]["id"] == self.team.id
        assert app_context["current_team"]["user_access_level"] == "member"

        self._put_project_access_control(self.team.id, {"access_level": "none"})
        app_context = self._get_posthog_app_context()
        assert len(app_context["current_user"]["organization"]["teams"]) == 2
        assert app_context["current_team"]["id"] == self.team.id
        assert app_context["current_team"]["user_access_level"] == "none"

    # def test_does_not_list_notebooks_without_access(self):
    #     self._org_membership(OrganizationMembership.Level.ADMIN)
    #     assert (
    #         self._put_notebook_access_control(self.other_user_notebook.short_id, {"access_level": "none"}).status_code
    #         == status.HTTP_200_OK
    #     )
    #     assert (
    #         self._put_notebook_access_control(self.notebook.short_id, {"access_level": "none"}).status_code
    #         == status.HTTP_200_OK
    #     )
    #     self._org_membership(OrganizationMembership.Level.MEMBER)

    #     res = self._get_notebooks()
    #     assert len(res.json()["results"]) == 1
    #     assert res.json()["results"][0]["id"] == str(self.notebook.id)

    # def test_list_notebooks_with_explicit_access(self):
    #     self._org_membership(OrganizationMembership.Level.ADMIN)
    #     assert (
    #         self._put_notebook_access_control(self.other_user_notebook.short_id, {"access_level": "none"}).status_code
    #         == status.HTTP_200_OK
    #     )
    #     assert (
    #         self._put_notebook_access_control(
    #             self.other_user_notebook.short_id,
    #             {"organization_member": str(self.organization_membership.id), "access_level": "viewer"},
    #         ).status_code
    #         == status.HTTP_200_OK
    #     )
    #     self._org_membership(OrganizationMembership.Level.MEMBER)

    #     res = self._get_notebooks()
    #     assert len(res.json()["results"]) == 2


# TODO: Add tests to check only project admins can edit the project
# TODO: Add tests to check that a dashboard can't be edited if the user doesn't have access
