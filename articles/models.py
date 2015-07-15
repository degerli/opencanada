from __future__ import absolute_import, unicode_literals

from operator import attrgetter

from basic_site.models import UniquelySlugable
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.shortcuts import get_object_or_404, render
from django.utils.encoding import python_2_unicode_compatible
from modelcluster.fields import ParentalKey
from wagtail.contrib.wagtailroutablepage.models import RoutablePageMixin, route
from wagtail.wagtailadmin.edit_handlers import (FieldPanel, InlinePanel,
                                                MultiFieldPanel,
                                                PageChooserPanel,
                                                StreamFieldPanel)
from wagtail.wagtailcore.fields import RichTextField
from wagtail.wagtailcore.models import Orderable, Page
from wagtail.wagtailimages.edit_handlers import ImageChooserPanel
from wagtail.wagtailsnippets.edit_handlers import SnippetChooserPanel
from wagtail.wagtailsnippets.models import register_snippet

from . import fields as article_fields


@python_2_unicode_compatible
class Colour(models.Model):
    name = models.CharField(max_length=100)
    rgb_value = models.CharField(max_length=7)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.rgb_value.startswith("#"):
            self.rgb_value = "#{}".format(self.rgb_value)


register_snippet(Colour)


@python_2_unicode_compatible
class FontStyle(models.Model):
    name = models.CharField(max_length=1024)
    font_size = models.FloatField(default=1, help_text="The size of the fonts in ems.")
    line_size = models.FloatField(default=100, help_text="The line height as a percentage.")
    text_colour = models.ForeignKey(
        Colour,
        default=1,
        null=True,
        on_delete=models.SET_NULL
    )

    panels = [
        FieldPanel('name'),
        FieldPanel('font_size'),
        FieldPanel('line_size'),
        FieldPanel('text_colour'),
    ]

    def __str__(self):
        return self.name


register_snippet(FontStyle)


@python_2_unicode_compatible
class ArticleListPage(Page):
    subpage_types = ['ArticlePage']

    @property
    def subpages(self):
        # Get list of live event pages that are descendants of this page
        subpages = ArticlePage.objects.live().descendant_of(self).order_by('-first_published_at')

        return subpages

    def __str__(self):
        return self.title


@python_2_unicode_compatible
class Topic(UniquelySlugable):
    name = models.CharField(max_length=1024)

    def __str__(self):
        return self.name


register_snippet(Topic)


Topic.panels = [
    FieldPanel("name"),
]


class TopicListPage(RoutablePageMixin, Page):

    @property
    def topics(self):
        return Topic.objects.all().order_by("name")

    @route(r'^$', name="topic_list")
    def topics_list(self, request):
        context = {
            "self": self,
        }
        return render(request, "articles/topic_list_page.html", context)

    @route(r'^([\w-]+)/$', name="topic")
    def topic_view(self, request, topic_slug):
        topic = get_object_or_404(Topic, slug=topic_slug)

        articles = ArticlePage.objects.live().filter(primary_topic=topic).order_by('-first_published_at')
        context = {
            "self": self,
            "topic": topic,
            "articles": articles,
        }
        return render(request, "articles/topic_page.html", context)


class ArticleCategoryManager(models.Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


@python_2_unicode_compatible
class ArticleCategory(UniquelySlugable):
    objects = ArticleCategoryManager()

    name = models.CharField(max_length=1024)

    class Meta:
        verbose_name_plural = "Article Categories"

    def natural_key(self):
        return (self.slug, )

    def __str__(self):
        return self.name


register_snippet(ArticleCategory)


class Sticky(models.Model):
    sticky = models.BooleanField(default=False)

    class Meta:
        abstract = True


class FeatureStyleFields(models.Model):
    feature_style = models.CharField(
        max_length=20,
        choices=[
            ("simple", "Single Column - Text Only"),
            ("simpleimage", "Single Column - Text and Image"),
            ("coverimage", "Full Width - Text overlayed on image"),
            ("tallcoverimage", "Full Width - Double Height - Text overlayed on image"),
        ],
        default="simple")

    image_overlay_color = models.ForeignKey(
        Colour,
        default=1,
        null=True,
        on_delete=models.SET_NULL
    )

    image_overlay_opacity = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=50,
        help_text="Set the value from 0 (Solid overlay, original image not visible) to 100 (No overlay, original image completely visible)"
    )

    font_style = models.ForeignKey(
        'articles.FontStyle',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    class Meta:
        abstract = True


@python_2_unicode_compatible
class ArticlePage(Page, FeatureStyleFields, Sticky):
    excerpt = RichTextField(blank=True, default="")
    body = article_fields.BodyField()
    main_image = models.ForeignKey(
        'images.AttributedImage',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    primary_topic = models.ForeignKey(
        'articles.Topic',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    category = models.ForeignKey(
        'articles.ArticleCategory',
        related_name='articles',
        on_delete=models.SET_NULL,
        null=True
    )

    def __str__(self):
        return self.title

    @property
    def authors(self):
        return [link.author for link in self.author_links.all()]

    @property
    def series_articles(self):
        related_series_data = []
        for link in self.in_depth_links.all():
            indepth_page = link.in_depth
            indepth_articles = indepth_page.articles
            indepth_articles.remove(self)
            related_series_data.append((indepth_page, indepth_articles))
        return related_series_data

    @property
    def topics(self):
        primary_topic = self.primary_topic
        all_topics = [link.topic for link in self.topic_links.all()]
        if primary_topic:
            all_topics.append(primary_topic)
        all_topics = list(set(all_topics))
        if len(all_topics) > 0:
            all_topics.sort(key=attrgetter('name'))
        return all_topics

    def related_articles(self, number):
        articles = ArticlePage.objects.live().all().exclude(id=self.id)[:number]
        # TODO: pick actual related articles based on primary topic, secondary topics, authors
        return articles

ArticlePage.content_panels = Page.content_panels + [
    FieldPanel('excerpt'),
    InlinePanel('author_links', label="Authors"),
    StreamFieldPanel('body'),
    ImageChooserPanel('main_image'),
    SnippetChooserPanel('primary_topic', Topic),
    InlinePanel('topic_links', label="Secondary Topics"),
    SnippetChooserPanel('category', ArticleCategory),
]

ArticlePage.promote_panels = Page.promote_panels + [
    MultiFieldPanel(
        [
            FieldPanel('sticky'),
            FieldPanel('feature_style'),
            MultiFieldPanel(
                [
                    FieldPanel('image_overlay_opacity'),
                    SnippetChooserPanel('image_overlay_color', Colour),
                    SnippetChooserPanel("font_style", FontStyle),
                ],
                heading="Image Overlay Settings"
            )
        ],
        heading="Featuring Settings"
    )
]


@python_2_unicode_compatible
class ArticleTopicLink(models.Model):
    topic = models.ForeignKey(
        "Topic",
        related_name='article_links'
    )
    article = ParentalKey(
        "ArticlePage",
        related_name='topic_links'
    )

    def __str__(self):
        return "{} - {}".format(
            self.article.title,
            self.topic.name
        )

    panels = [
        SnippetChooserPanel('topic', Topic),
    ]


@python_2_unicode_compatible
class ArticleAuthorLink(Orderable, models.Model):
    author = models.ForeignKey(
        "people.ContributorPage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='article_links'
    )
    article = ParentalKey(
        "ArticlePage",
        related_name='author_links'
    )

    def __str__(self):
        return "{} - {}".format(self.article.title, self.author.full_name)

    panels = [
        PageChooserPanel('author', 'people.ContributorPage'),
    ]


@python_2_unicode_compatible
class InDepthListPage(Page):
    subpage_types = ['InDepthPage']

    @property
    def subpages(self):
        # Get list of live event pages that are descendants of this page
        subpages = InDepthPage.objects.live().descendant_of(self).order_by('-first_published_at')

        return subpages

    def __str__(self):
        return self.title


class InDepthArticleLink(Orderable, models.Model):
    override_image = models.ForeignKey(
        'images.AttributedImage',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="This field is optional. If not provided, the image will be "
                  "pulled from the article page automatically. This field "
                  "allows you to override the automatic image."
    )
    override_text = RichTextField(
        blank=True,
        default="",
        help_text="This field is optional. If not provided, the text will be "
                  "pulled from the article page automatically. This field "
                  "allows you to override the automatic text."
    )
    article = models.ForeignKey(
        "ArticlePage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='in_depth_links'
    )
    in_depth = ParentalKey(
        "InDepthPage",
        related_name='related_article_links'
    )

    panels = [
        PageChooserPanel("article", 'articles.ArticlePage'),
        FieldPanel("override_text"),
        ImageChooserPanel("override_image"),

    ]


class InDepthPage(Page, Sticky):
    subtitle = RichTextField(blank=True, default="")
    body = article_fields.BodyField(blank=True, default="")
    main_image = models.ForeignKey(
        'images.AttributedImage',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    primary_topic = models.ForeignKey(
        'articles.Topic',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    @property
    def articles(self):
        article_list = []
        for article_link in self.related_article_links.all():
            article_link.article.override_text = article_link.override_text
            article_link.article.override_image = article_link.override_image
            article_list.append(article_link.article)
        return article_list

    @property
    def authors(self):
        author_list = []
        for article_link in self.related_article_links.all():
            for author_link in article_link.article.author_links.all():
                author_list.append(author_link.author)
        author_list.sort(key=attrgetter('last_name'))
        return author_list

    @property
    def topics(self):
        all_topics = []
        if self.primary_topic:
            all_topics.append(self.primary_topic)
        for article_link in self.related_article_links.all():
            all_topics.extend(article_link.article.topics)

        all_topics = list(set(all_topics))
        if all_topics:
            all_topics.sort(key=attrgetter('name'))
        return all_topics

    def related_articles(self, number):
        articles = ArticlePage.objects.live().all()[:number]
        # TODO: pick actual related articles based on primary topic, secondary topics, authors
        return articles

InDepthPage.content_panels = Page.content_panels + [
    FieldPanel('subtitle'),
    StreamFieldPanel('body'),
    ImageChooserPanel('main_image'),
    InlinePanel('related_article_links', label="Articles")
]

InDepthPage.promote_panels = Page.promote_panels + [
    MultiFieldPanel(
        [
            FieldPanel('sticky'),
        ],
        heading="Featuring Settings"
    )
]


@python_2_unicode_compatible
class Headline(FeatureStyleFields):
    containing_page = models.ForeignKey(
        'wagtailcore.Page',
        related_name='historic_headlines'
    )

    featured_item = models.ForeignKey(
        'wagtailcore.Page',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True)

    def __str__(self):
        return "{}".format(self.id)
