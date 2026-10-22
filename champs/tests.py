from django.test import TestCase

from champs.models import Championship
from champs.views import get_champ_list_context


class ChampionshipPublicationListTests(TestCase):
    def setUp(self):
        self.published = Championship.objects.create(name='Campeonato publicado', publish=True)
        self.unpublished = Championship.objects.create(name='Campeonato sin publicar', publish=False)

    def test_context_can_filter_published_championships(self):
        context = get_champ_list_context('true')

        self.assertEqual(context['publish_filter'], 'true')
        self.assertEqual([champ.id for champ in context['champ_list']], [self.published.id])

    def test_context_can_filter_unpublished_championships(self):
        context = get_champ_list_context('false')

        self.assertEqual(context['publish_filter'], 'false')
        self.assertEqual([champ.id for champ in context['champ_list']], [self.unpublished.id])
