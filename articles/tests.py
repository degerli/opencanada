from django.test import TestCase
from wagtail.wagtailimages.models import Image

from people.models import ContributorPage

from .models import (ArticleListPage, ArticlePage, ArticleTopicLink,
                     InDepthListPage, InDepthPage, Topic)


class InDepthPageTestCase(TestCase):
    fixtures = ["articlestest.json", ]

    def test_has_right_number_of_authors(self):
        indepth = InDepthPage.objects.all().first()
        self.assertEqual(len(indepth.authors), 2)

    def test_has_right_authors_from_articles(self):
        indepth = InDepthPage.objects.all().first()
        bob = ContributorPage.objects.get(email="bobsmith@example.com")
        joe = ContributorPage.objects.get(email="joesampson@example.com")

        self.assertIn(bob, indepth.authors)
        self.assertIn(joe, indepth.authors)

    def test_authors_in_alphabetical_order(self):
        indepth = InDepthPage.objects.all().first()
        bob = ContributorPage.objects.get(email="bobsmith@example.com")
        joe = ContributorPage.objects.get(email="joesampson@example.com")

        self.assertEqual(joe, indepth.authors[0])
        self.assertEqual(bob, indepth.authors[1])

        bob.last_name = "Achange"

        revision = bob.save_revision(
            user=None,
            submitted_for_moderation=False,
        )
        revision.publish()

        self.assertEqual(bob, indepth.authors[0])
        self.assertEqual(joe, indepth.authors[1])

    def test_in_depth_articles(self):
        indepth = InDepthPage.objects.all().first()

        a6 = ArticlePage.objects.get(pk=7)
        a7 = ArticlePage.objects.get(pk=8)

        self.assertEqual(2, len(indepth.articles))

        self.assertIn(a6, indepth.articles)
        self.assertIn(a7, indepth.articles)

    def test_in_depth_articles_order(self):
        indepth = InDepthPage.objects.all().first()

        a6 = ArticlePage.objects.get(pk=7)
        a7 = ArticlePage.objects.get(pk=8)

        self.assertEqual(a7, indepth.articles[0])
        self.assertEqual(a6, indepth.articles[1])

    def test_article_has_override_text(self):
        indepth = InDepthPage.objects.all().first()

        override = indepth.articles[0].override_text

        self.assertEqual("<p>This is overridden text.</p>", override)

    def test_article_has_override_image(self):
        indepth = InDepthPage.objects.all().first()

        image = Image.objects.get(pk=1)
        override = indepth.articles[0].override_image

        self.assertEqual(image, override)

    def test_topics_includes_allprimary_and_secondary_topics(self):
        indepth = InDepthPage.objects.all().first()
        topics = indepth.topics

        t1 = Topic.objects.get(pk=1)
        t2 = Topic.objects.get(pk=2)
        t4 = Topic.objects.get(pk=4)
        self.assertIn(t1, topics)
        self.assertIn(t2, topics)
        self.assertIn(t4, topics)

    def test_topics_sorted_alphabetically(self):
        indepth = InDepthPage.objects.all().first()
        topics = indepth.topics
        self.assertEqual("Topic 1", topics[0].name)
        self.assertEqual("Topic 2", topics[1].name)
        self.assertEqual("Topic 4", topics[2].name)

    def test_topics_removes_duplicates(self):
        indepth = InDepthPage.objects.all().first()
        self.assertEqual(len(indepth.topics), 3)

#   TODO: verify related articles

    def test_related_articles_returns_the_number_requested(self):
        indepth = InDepthPage.objects.all().first()
        related_articles = indepth.related_articles(number=2)
        self.assertEqual(2, len(related_articles))


class ArticlePageTestCase(TestCase):
    fixtures = ["articlestest.json", ]

    def test_single_author_has_one_author(self):
        article = ArticlePage.objects.get(slug="test-article-1")
        self.assertEqual(len(article.authors), 1)

    def test_single_author_has_expected_author(self):
        article = ArticlePage.objects.get(slug="test-article-1")
        bob = ContributorPage.objects.get(email="bobsmith@example.com")
        self.assertEqual(article.authors[0], bob)

    def test_multiple_authors(self):
        article = ArticlePage.objects.get(slug="test-article-4")
        self.assertEqual(len(article.authors), 2)

    def test_single_author_has_expected_author_in_order(self):
        article = ArticlePage.objects.get(slug="test-article-4")
        mary = ContributorPage.objects.get(email="marysue@example.com")
        joe = ContributorPage.objects.get(email="joesampson@example.com")

        self.assertEqual(article.authors[0], mary)
        self.assertEqual(article.authors[1], joe)

#   TODO: verify related articles

    def test_related_articles_returns_the_number_requested(self):
        article = ArticlePage.objects.get(id=9)
        related_articles = article.related_articles(number=2)
        self.assertEqual(2, len(related_articles))

    def test_related_articles_excludes_self(self):
        article = ArticlePage.objects.get(id=9)
        related_articles = article.related_articles(number=10)
        self.assertNotIn(article, related_articles)

    # TODO: Includes primary topic as filter
    # TODO: Includes secondary topics as filter
    # TODO: Includes authors as filter

    def test_in_depth_contains_in_depth(self):
        article = ArticlePage.objects.get(pk=7)
        indepth = InDepthPage.objects.all().first()
        actual = article.series_articles
        self.assertEqual(1, len(actual))
        self.assertEqual(indepth, actual[0][0])

    def test_other_articles_in_in_depth(self):
        article = ArticlePage.objects.get(pk=7)
        other_article = ArticlePage.objects.get(pk=8)
        actual = article.series_articles
        self.assertIn(other_article, actual[0][1])

    def test_in_depth_artcles_does_not_contain_self(self):
        article = ArticlePage.objects.get(pk=7)
        actual = article.series_articles
        self.assertNotIn(article, actual[0][1])

    def test_article_has_override_text_for_in_depth_related(self):
        article = ArticlePage.objects.get(pk=7)
        override = article.series_articles[0][1][0].override_text
        self.assertEqual("<p>This is overridden text.</p>", override)

    def test_article_has_override_image_for_in_depth_related(self):
        article = ArticlePage.objects.get(pk=7)
        image = Image.objects.get(pk=1)
        override = article.series_articles[0][1][0].override_image
        self.assertEqual(image, override)

    def test_topics_includes_allprimary_and_secondary_topics(self):
        article = ArticlePage.objects.get(slug="test-article-4")
        self.assertEqual(len(article.topics), 3)

        t1 = Topic.objects.get(pk=1)
        t2 = Topic.objects.get(pk=2)
        t3 = Topic.objects.get(pk=3)
        self.assertIn(t1, article.topics)
        self.assertIn(t2, article.topics)
        self.assertIn(t3, article.topics)

    def test_topics_sorted_alphabetically(self):
        article = ArticlePage.objects.get(slug="test-article-4")
        topics = article.topics
        self.assertEqual("Topic 1", topics[0].name)
        self.assertEqual("Topic 2", topics[1].name)
        self.assertEqual("Topic 3", topics[2].name)

    def test_topics_removes_duplicates(self):
        article = ArticlePage.objects.get(slug="test-article-3")
        self.assertEqual(len(article.topics), 1)


class ArticleListPageTestCase(TestCase):
    fixtures = ["articlestest.json", ]

    def test_get_list_of_articles(self):
        features = ArticleListPage.objects.get(slug='features')
        articles = features.subpages
        self.assertEqual(len(articles), 4)


class InDepthListPageTestCase(TestCase):
    fixtures = ["articlestest.json", ]

    def test_get_list_of_indepths(self):
        indepth = InDepthListPage.objects.get(slug='indepth')
        indepth_pages = indepth.subpages
        self.assertEqual(len(indepth_pages), 1)


class ArticleTopicLinkTestCase(TestCase):
    fixtures = ["articlestest.json", ]

    def test_str(self):
        link = ArticleTopicLink.objects.get(pk=1)
        self.assertEqual("Test Article 4 - Topic 2", str(link))
