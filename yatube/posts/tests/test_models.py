from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая группа',
        )

    def test_models_have_correct_object_names(self):
        """Проверка, что у моделей корректно работает __str__."""
        post = PostModelTest
        self.assertEqual(str(post.post), 'Тестовая группа')
        self.assertEqual(str(post.group), 'Тестовая группа')

    def test_verbose_name(self):
        """Проверка, что verbose_name коррекстно отображается."""
        post = PostModelTest.post
        verbose_fields = {
            'text': 'Текст',
            'group': 'Группа',
        }
        for field, expected_value in verbose_fields.items():
            with self.subTest(field=field):
                self.assertEqual(
                    post._meta.get_field(field).verbose_name, expected_value)

    def test_help_text(self):
        """Проверка, что help_text коррекстно отображается."""
        post = PostModelTest.post
        help_text_fields = {
            'text': 'Введите текст поста',
            'group': 'Выберите группу',
        }
        for field, expected_value in help_text_fields.items():
            with self.subTest(field=field):
                self.assertEqual(
                    post._meta.get_field(field).help_text, expected_value)
