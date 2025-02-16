from django.contrib.syndication.views import Feed
from django.template.defaultfilters import truncatewords
from django.utils.feedgenerator import Atom1Feed
from django.urls import reverse
from .models import Post


class BlogFeed(Feed):
    # Basic feed settings
    title = "Your Blog Name"  # You can customize this
    link = "/blog/"
    description = "Latest blog posts from Your Blog Name"

    def items(self):
        # Returns only published posts, ordered by publication date
        return Post.objects.filter(status="published").order_by("-published_date")[
            :10
        ]  # Limiting to latest 10 posts

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        # Returns first 50 words of the post content
        return truncatewords(item.content, 50)

    def item_link(self, item):
        # Uses the post's get_absolute_url method
        return item.get_absolute_url()

    def item_pubdate(self, item):
        # Publication date for the post
        return item.published_date

    def item_updateddate(self, item):
        # Last updated date for the post
        return item.updated_date

    def item_author_name(self, item):
        return "Blog Author"  

# Atom feed inherits from the RSS feed
class AtomBlogFeed(BlogFeed):
    feed_type = Atom1Feed
    subtitle = BlogFeed.description

    def item_subtitle(self, item):
        return truncatewords(item.content, 50)
