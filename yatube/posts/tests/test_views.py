from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.core.cache import cache

from posts.models import Follow, Group, Post

User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД:тестового юзера, группу и пост
        cls.user = User.objects.create_user(username='test_author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            description='Тестовое описание',
            slug='test_slug'
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая группа_2',
            description='Тестовое описание_2',
            slug='test_slug_2'
        )

        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

# Проверяем, что при обращении к name вызывается соответствующий HTML-шаблон
    def test_post_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "reverse(name): имя_html_шаблона"
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
            'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user}):
            'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
            'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/post_create.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}):
            'posts/post_create.html',
        }
        for reverse_name, template in templates_pages_names.items():
            cache.clear()
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def check_context(self, post):
        """Метод, для проверки ожидаемых значений словаря context."""
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group.id, self.group.id)
        self.assertEqual(post.image, self.post.image)

    def test_index_show_correct_context(self):
        """Проверка, что гл.стр. с ожидаемым контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.check_context(response.context['page_obj'][0])

    def test_group_list_show_correct_context(self):
        """Проверка:страница группы с ожидаемым контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        self.check_context(response.context['page_obj'][0])

    def test_new_post_not_in_uncorrect_group(self):
        """Проверка: пост не в группе, для которой не предназначен."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group_2.slug}))
        posts_object = response.context['posts']
        self.assertNotIn(self.post, posts_object)

    def test_profile_show_correct_context(self):
        """Проверка: стр.профиля сформирована с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user}),
        )
        self.check_context(response.context['page_obj'][0])
        user_object = response.context['author'].username
        self.assertEqual(user_object, self.user.username)

    def test_post_detail_show_correct_context(self):
        """Проверка: страница поста сформирована с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        self.check_context(response.context['post'])


class PaginatorViewsTest(TestCase):
    # Здесь создаются фикстуры: клиент и 13 тестовых записей.
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test_slug'
        )
        cls.amount_of_posts = 15
        cls.posts = []
        for i in range(cls.amount_of_posts):
            post = Post(
                author=cls.user,
                text='Тестовый пост',
                group=cls.group,
            )
            cls.posts.append(post)
        Post.objects.bulk_create(cls.posts)

        cls.guest_client = Client()

        cls.pages_uses_paginator = [
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': cls.user.username}),
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}),
        ]

    def test_first_page_contains_ten_records(self):
        paginate_by = int(settings.PAGINATE_BY)
        for reverse_page in self.pages_uses_paginator:
            with self.subTest(reverse_page=reverse_page):
                response = self.client.get(reverse_page)
        # Проверка: количество постов на первой странице равно 10.
                self.assertEqual(len(
                    response.context['page_obj']), paginate_by)

    def test_second_page_contains_three_records(self):
        paginate_by_five = self.amount_of_posts - int(settings.PAGINATE_BY)
        for reverse_page in self.pages_uses_paginator:
            with self.subTest(reverse_page=reverse_page):
                response = self.client.get(reverse_page + '?page=2')
        # Проверка: на второй странице должно быть 5 постов.
                self.assertEqual(
                    len(response.context['page_obj']), paginate_by_five,)


class CacheTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.guest_client = Client()
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
        )
        cache.clear()

    def test_cache(self):
        """Проверка кеширования гл.стр."""
        cache.clear()
        response = self.guest_client.get(reverse('posts:index'))
        content_len_before = len(response.content)

        self.post.delete()

        response = self.guest_client.get(reverse('posts:index'))
        content_len_after = len(response.content)
        self.assertEqual(content_len_before, content_len_after)

        cache.clear()
        response = self.guest_client.get(reverse('posts:index'))
        content_len_after = len(response.content)
        self.assertNotEqual(content_len_after, content_len_before)


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_author')
        cls.follower = User.objects.create_user(username='test_follower')
        cls.authorized_author = Client()
        cls.authorized_author.force_login(cls.author)
        cls.authorized_follower = Client()
        cls.authorized_follower.force_login(cls.follower)

    def test_follow(self):
        """Авторизированный user может подписываться на author."""
        counts_follower = Follow.objects.count()
        self.authorized_follower.get(reverse('posts:profile_follow',
                                     args={self.author.username}))
        follow = Follow.objects.first()
        self.assertEqual(Follow.objects.count(), counts_follower + 1)
        self.assertEqual(follow.user, self.follower)
        self.assertEqual(follow.author, self.author)

    def test_unfollow(self):
        """Авторизированный user может отписаться от author."""
        Follow.objects.create(user=self.follower, author=self.author)
        self.assertEqual(Follow.objects.count(), 1)
        self.authorized_follower.get(reverse('posts:profile_unfollow',
                                             args={self.author.username}))
        self.assertEqual(Follow.objects.count(), 0)

    def test_post_for_follower(self):
        """Новый пост появляется в ленте подписчика."""
        post = Post.objects.create(text='Тестовый текст', author=self.author)
        Follow.objects.create(user=self.follower, author=self.author)
        response = self.authorized_follower.get(reverse('posts:follow_index'))
        first_post = response.context['posts'][0]
        self.assertEqual(first_post, post)

    def test_post_not_appears_for_unfollower(self):
        """Новый пост не повяляется в ленте тех, кто НЕ подписан."""
        post = Post.objects.create(text='Тестовый текст', author=self.author)
        Follow.objects.create(user=self.follower, author=self.author)
        user = User.objects.create_user(username='user2')
        authorized_user = Client()
        authorized_user.force_login(user)
        response = authorized_user.get(reverse('posts:follow_index'))
        posts = response.context['posts']
        self.assertNotIn(post, posts)
