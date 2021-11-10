import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm
from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаем запись в базе данных
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
        cls.image = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает новую запись с картинкой."""
        posts_count = Post.objects.count()
        uploaded = SimpleUploadedFile(
            name='mypic.jpg',
            content=self.image,
            content_type='image/gif',
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': PostFormTests.group.pk,
            'author': PostFormTests.user,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, reverse('posts:profile',
                             kwargs={'username': 'test_user'}))
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.first()
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, form_data['author'])
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(uploaded, form_data['image'])

    def test_post_edit(self):
        """Проверяем что форма редактирует запись поста."""
        post_id = PostFormTests.post.pk
        form_data = {
            'text': 'Тестовый текст',
            'group': PostFormTests.group.pk,
            'author': PostFormTests.user
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': f'{PostFormTests.post.pk}'}),
            data=form_data,
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, reverse('posts:post_detail',
                             kwargs={'post_id': f'{PostFormTests.post.pk}'}))
        self.assertEqual(PostFormTests.post.pk, post_id)

    def test_guests_unable_to_create_post(self):
        """Неавторизированый пользователь не может создать пост."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Пост',
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(
            response,
            reverse('users:login') + '?next=' + reverse('posts:post_create'),
        )
        self.assertFalse(
            Post.objects.filter(text=form_data['text'],).exists()
        )

    def test_comments_only_authorized_client(self):
        """Проверка: комментарии может оставить только авториз. клиент"""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Комментарий'
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(
            Comment.objects.filter(text=form_data['text'],
                                   author=self.user).exists())
        self.assertRedirects(response,
                             reverse('users:login') + '?next=' + reverse(
                                 'posts:add_comment',
                                 kwargs={'post_id': self.post.id}))

    def test_new_comment_creates(self):
        """Проверка: комментарий появляется на стр.поста"""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Комментарий'
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(
            Comment.objects.filter(text=form_data['text'],
                                   author=self.user).exists())
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))
