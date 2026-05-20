from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import ProjectPlace, TravelProject


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mock_fetch(external_id):
    catalogue = {
        '28560': {'name': 'The Bedroom', 'external_id': '28560'},
        '27992': {'name': 'A Sunday on La Grande Jatte', 'external_id': '27992'},
        '11723': {'name': 'American Gothic', 'external_id': '11723'},
    }
    return catalogue.get(str(external_id))


class BaseAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def make_project(self, name='Test Project', **kwargs):
        return TravelProject.objects.create(name=name, **kwargs)

    def make_place(self, project, ext_id='1', visited=False):
        return ProjectPlace.objects.create(
            project=project, external_id=ext_id, name=f'Place {ext_id}', is_visited=visited,
        )

    def post(self, url, data, **kwargs):
        return self.client.post(url, data, format='json', **kwargs)

    def patch(self, url, data, **kwargs):
        return self.client.patch(url, data, format='json', **kwargs)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TravelProjectModelTest(TestCase):
    def setUp(self):
        self.project = TravelProject.objects.create(name='Model Test Project')

    def _place(self, ext_id, visited=False):
        return ProjectPlace.objects.create(
            project=self.project, external_id=ext_id, name=f'Place {ext_id}', is_visited=visited,
        )

    def test_str(self):
        self.assertEqual(str(self.project), 'Model Test Project')

    def test_place_str(self):
        p = self._place('1')
        self.assertEqual(str(p), 'Place 1 (Model Test Project)')

    def test_completion_all_visited(self):
        p1 = self._place('1')
        p2 = self._place('2')
        p1.is_visited = True
        p1.save()
        p2.is_visited = True
        p2.save()
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_completed)

    def test_not_completed_partial_visited(self):
        p1 = self._place('1')
        self._place('2')
        p1.is_visited = True
        p1.save()
        self.project.refresh_from_db()
        self.assertFalse(self.project.is_completed)

    def test_not_completed_no_places(self):
        self.project.refresh_completion_status()
        self.assertFalse(self.project.is_completed)

    def test_unique_together_external_id(self):
        from django.db import IntegrityError
        self._place('42')
        with self.assertRaises(IntegrityError):
            self._place('42')


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

class AuthTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='authuser', password='authpass123')

    def test_obtain_token(self):
        res = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'authuser', 'password': 'authpass123'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)

    def test_refresh_token(self):
        refresh = RefreshToken.for_user(self.user)
        res = self.client.post(
            reverse('token_refresh'),
            {'refresh': str(refresh)},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)

    def test_unauthenticated_returns_401(self):
        res = self.client.get(reverse('project-list'))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_token_returns_401(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer bad.token.here')
        res = self.client.get(reverse('project-list'))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# TravelProject list / create
# ---------------------------------------------------------------------------

class TravelProjectListCreateTest(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('project-list')

    def test_list_empty(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 0)

    def test_list_returns_all_projects(self):
        self.make_project('A')
        self.make_project('B')
        res = self.client.get(self.url)
        self.assertEqual(res.data['count'], 2)

    def test_create_project_minimal(self):
        res = self.post(self.url, {'name': 'My Trip'})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['name'], 'My Trip')
        self.assertFalse(res.data['is_completed'])

    def test_create_project_full_fields(self):
        res = self.post(self.url, {
            'name': 'Full Trip',
            'description': 'A nice journey',
            'start_date': '2026-07-01',
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['description'], 'A nice journey')
        self.assertEqual(res.data['start_date'], '2026-07-01')

    def test_create_project_missing_name_fails(self):
        res = self.post(self.url, {'description': 'No name'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', res.data)

    @patch('travel_planner.serializers.fetch_place_from_api', side_effect=mock_fetch)
    def test_create_project_with_places(self, _):
        res = self.post(self.url, {
            'name': 'Art Trip',
            'place_ids': [{'external_id': '28560'}, {'external_id': '27992'}],
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(res.data['places']), 2)
        names = {p['name'] for p in res.data['places']}
        self.assertIn('The Bedroom', names)

    @patch('travel_planner.serializers.fetch_place_from_api', side_effect=mock_fetch)
    def test_create_project_with_11_places_fails(self, _):
        place_ids = [{'external_id': str(i)} for i in range(11)]
        res = self.post(self.url, {'name': 'Big', 'place_ids': place_ids})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('travel_planner.serializers.fetch_place_from_api', side_effect=mock_fetch)
    def test_create_project_with_duplicate_place_ids_fails(self, _):
        res = self.post(self.url, {
            'name': 'Trip',
            'place_ids': [{'external_id': '28560'}, {'external_id': '28560'}],
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('travel_planner.serializers.fetch_place_from_api', return_value=None)
    def test_create_project_with_unknown_place_fails(self, _):
        res = self.post(self.url, {
            'name': 'Trip',
            'place_ids': [{'external_id': '00000'}],
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_is_completed_true(self):
        self.make_project('Active')
        self.make_project('Done', is_completed=True)
        res = self.client.get(self.url, {'is_completed': 'true'})
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['name'], 'Done')

    def test_filter_is_completed_false(self):
        self.make_project('Active')
        self.make_project('Done', is_completed=True)
        res = self.client.get(self.url, {'is_completed': 'false'})
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['name'], 'Active')

    def test_filter_start_date_after(self):
        self.make_project('Old', start_date='2025-01-01')
        self.make_project('New', start_date='2026-06-01')
        res = self.client.get(self.url, {'start_date_after': '2026-01-01'})
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['name'], 'New')

    def test_filter_start_date_before(self):
        self.make_project('Old', start_date='2025-01-01')
        self.make_project('New', start_date='2026-06-01')
        res = self.client.get(self.url, {'start_date_before': '2025-12-31'})
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['name'], 'Old')

    def test_search_by_name(self):
        self.make_project('Paris Trip')
        self.make_project('Tokyo Adventure')
        res = self.client.get(self.url, {'search': 'Paris'})
        self.assertEqual(res.data['count'], 1)

    def test_search_by_description(self):
        self.make_project('Trip A', description='Eiffel tower visit')
        self.make_project('Trip B', description='Cherry blossoms')
        res = self.client.get(self.url, {'search': 'Eiffel'})
        self.assertEqual(res.data['count'], 1)

    def test_ordering_by_name(self):
        self.make_project('Zebra')
        self.make_project('Alpha')
        res = self.client.get(self.url, {'ordering': 'name'})
        self.assertEqual(res.data['results'][0]['name'], 'Alpha')

    def test_pagination_page_size(self):
        for i in range(15):
            self.make_project(f'Project {i}')
        res = self.client.get(self.url)
        self.assertEqual(res.data['count'], 15)
        self.assertEqual(len(res.data['results']), 10)
        self.assertIsNotNone(res.data['next'])

    def test_pagination_second_page(self):
        for i in range(15):
            self.make_project(f'Project {i}')
        res = self.client.get(self.url, {'page': 2})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 5)


# ---------------------------------------------------------------------------
# TravelProject retrieve / update / delete
# ---------------------------------------------------------------------------

class TravelProjectDetailTest(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.project = self.make_project('Detail Project', description='Desc')
        self.url = reverse('project-detail', args=[self.project.id])

    def test_retrieve(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['name'], 'Detail Project')
        self.assertIn('places', res.data)

    def test_retrieve_includes_places(self):
        self.make_place(self.project, '1')
        res = self.client.get(self.url)
        self.assertEqual(len(res.data['places']), 1)

    def test_retrieve_404(self):
        res = self.client.get(reverse('project-detail', args=[99999]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_name(self):
        res = self.patch(self.url, {'name': 'Renamed'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['name'], 'Renamed')
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'Renamed')

    def test_update_description(self):
        res = self.patch(self.url, {'description': 'New desc'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.description, 'New desc')

    def test_update_start_date(self):
        res = self.patch(self.url, {'start_date': '2026-09-01'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(str(self.project.start_date), '2026-09-01')

    def test_update_returns_full_project_schema(self):
        res = self.patch(self.url, {'name': 'X'})
        self.assertIn('places', res.data)
        self.assertIn('is_completed', res.data)

    def test_delete_success(self):
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TravelProject.objects.filter(id=self.project.id).exists())

    def test_delete_with_visited_place_fails(self):
        self.make_place(self.project, '1', visited=True)
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(TravelProject.objects.filter(id=self.project.id).exists())

    def test_delete_with_only_unvisited_places_succeeds(self):
        self.make_place(self.project, '1', visited=False)
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_put_not_allowed(self):
        res = self.client.put(self.url, {'name': 'X'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ---------------------------------------------------------------------------
# ProjectPlace list / create
# ---------------------------------------------------------------------------

class ProjectPlaceListCreateTest(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.project = self.make_project('Place Project')
        self.url = reverse('project-place-list', args=[self.project.id])

    def test_list_empty(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_list_places(self):
        self.make_place(self.project, '1')
        self.make_place(self.project, '2')
        res = self.client.get(self.url)
        self.assertEqual(len(res.data['results']), 2)

    def test_list_scoped_to_project(self):
        other = self.make_project('Other')
        self.make_place(self.project, '1')
        self.make_place(other, '2')
        res = self.client.get(self.url)
        self.assertEqual(len(res.data['results']), 1)

    def test_list_nonexistent_project_returns_404(self):
        res = self.client.get(reverse('project-place-list', args=[99999]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_by_is_visited_true(self):
        self.make_place(self.project, '1', visited=True)
        self.make_place(self.project, '2', visited=False)
        res = self.client.get(self.url, {'is_visited': 'true'})
        self.assertEqual(len(res.data['results']), 1)
        self.assertTrue(res.data['results'][0]['is_visited'])

    def test_filter_by_is_visited_false(self):
        self.make_place(self.project, '1', visited=True)
        self.make_place(self.project, '2', visited=False)
        res = self.client.get(self.url, {'is_visited': 'false'})
        self.assertEqual(len(res.data['results']), 1)
        self.assertFalse(res.data['results'][0]['is_visited'])

    @patch('travel_planner.serializers.fetch_place_from_api', side_effect=mock_fetch)
    def test_add_place_success(self, _):
        res = self.post(self.url, {'external_id': '28560'})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['external_id'], '28560')
        self.assertEqual(res.data['name'], 'The Bedroom')
        self.assertFalse(res.data['is_visited'])

    @patch('travel_planner.serializers.fetch_place_from_api', return_value=None)
    def test_add_place_not_in_api_fails(self, _):
        res = self.post(self.url, {'external_id': '99999'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('travel_planner.serializers.fetch_place_from_api', side_effect=mock_fetch)
    def test_add_duplicate_place_fails(self, _):
        self.make_place(self.project, '28560')
        res = self.post(self.url, {'external_id': '28560'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('travel_planner.serializers.fetch_place_from_api', side_effect=mock_fetch)
    def test_add_place_at_limit_fails(self, _):
        for i in range(10):
            self.make_place(self.project, str(i))
        res = self.post(self.url, {'external_id': '28560'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_place_to_nonexistent_project_returns_404(self):
        res = self.post(reverse('project-place-list', args=[99999]), {'external_id': '1'})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_place_missing_external_id_fails(self):
        res = self.post(self.url, {})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# ProjectPlace retrieve / update
# ---------------------------------------------------------------------------

class ProjectPlaceDetailTest(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.project = self.make_project('Detail Place Project')
        self.place = ProjectPlace.objects.create(
            project=self.project, external_id='28560', name='The Bedroom',
        )
        self.url = reverse('project-place-detail', args=[self.project.id, self.place.id])

    def test_retrieve(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['external_id'], '28560')
        self.assertEqual(res.data['name'], 'The Bedroom')

    def test_retrieve_404_wrong_place(self):
        res = self.client.get(
            reverse('project-place-detail', args=[self.project.id, 99999])
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_404_wrong_project(self):
        other = self.make_project('Other')
        res = self.client.get(
            reverse('project-place-detail', args=[other.id, self.place.id])
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_notes(self):
        res = self.patch(self.url, {'notes': 'Beautiful painting'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['notes'], 'Beautiful painting')
        self.place.refresh_from_db()
        self.assertEqual(self.place.notes, 'Beautiful painting')

    def test_mark_as_visited(self):
        res = self.patch(self.url, {'is_visited': True})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['is_visited'])
        self.place.refresh_from_db()
        self.assertTrue(self.place.is_visited)

    def test_update_notes_and_visited_together(self):
        res = self.patch(self.url, {'notes': 'Great!', 'is_visited': True})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.place.refresh_from_db()
        self.assertEqual(self.place.notes, 'Great!')
        self.assertTrue(self.place.is_visited)

    def test_all_places_visited_completes_project(self):
        second = self.make_place(self.project, '27992')
        self.patch(self.url, {'is_visited': True})
        self.patch(
            reverse('project-place-detail', args=[self.project.id, second.id]),
            {'is_visited': True},
        )
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_completed)

    def test_partial_visited_does_not_complete_project(self):
        self.make_place(self.project, '27992')
        self.patch(self.url, {'is_visited': True})
        self.project.refresh_from_db()
        self.assertFalse(self.project.is_completed)

    def test_cannot_change_external_id(self):
        self.patch(self.url, {'external_id': '99999'})
        self.place.refresh_from_db()
        self.assertEqual(self.place.external_id, '28560')

    def test_cannot_change_name(self):
        self.patch(self.url, {'name': 'Hacked'})
        self.place.refresh_from_db()
        self.assertEqual(self.place.name, 'The Bedroom')
