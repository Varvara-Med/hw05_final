from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class StaticURLTests(TestCase):

    def setUp(self):
        self.guest_client = Client()

    def test_homepage(self):
        response = self.guest_client.get('/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_author(self):
        response = self.guest_client.get('/about/author/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_tech(self):
        response = self.guest_client.get('/about/tech/')
        self.assertEqual(response.status_code, HTTPStatus.OK)


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД для проверки доступности:
        # создадим тестового юзера, тестовую запись группы,
        # тестовую запись поста
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test_slug'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

        cls.public_pages = (
            '/',
            f'/profile/{cls.user.username}/',
            f'/posts/{str(cls.post.pk)}/',
        )

        cls.private_pages = (
            '/create/',
            f'/posts/{str(cls.post.pk)}/edit/',
            f'/posts/{str(cls.post.pk)}/comment/',
            f'/profile/{cls.user.username}/follow/',
            f'/profile/{cls.user.username}/unfollow/',
        )

        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    def test_public_urls_exists_at_desired_location(self):
        """Публичные страницы доступны любому пользователю."""
        for page in self.public_pages:
            with self.subTest(page=page):
                response = self.guest_client.get(page)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_pub_urls_for_authorized_client_exists_at_desired_location(self):
        """Публичные страницы доступны авторизированному пользователю."""
        for page in self.public_pages:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_private_urls_unavailable_to_not_authorized_client(self):
        """Приватные страницы не доступны неавторизированному клиенту."""
        for page in self.private_pages:
            with self.subTest(page=page):
                response = self.guest_client.get(page)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_unexisting_page_404(self):
        """Несуществующая страница возвращает ошибку 404."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
