# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103
"""
Copyright 2012-2014 Olivier Cortès <oc@1flow.io>.

This file is part of the 1flow project.

1flow is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

1flow is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with 1flow.  If not, see http://www.gnu.org/licenses/
"""

import logging

# from django.conf import settings
from django.test import TestCase  # TransactionTestCase

from oneflow.base.utils.http import clean_google_url, clean_marketing_url

LOGGER = logging.getLogger(__file__)


class TestHttpUtilsCleanMarketingUrl(TestCase):

    """ Test the Marketing cleaner. """

    def test_utm_star(self):
        """ Test all UTM parameters. """

        good_url = u'http://test.com/mytest/'

        for bad_url in (
            u'http://test.com/mytest/?=',
            u'http://test.com/mytest/?#',
            u'http://test.com/mytest/#?=',
            u'http://test.com/mytest/?=rss',
            u'http://test.com/mytest/?=rss-450',
            u'http://test.com/mytest/?=rss-450&',
            u'http://test.com/mytest/?=rss-450&=rss',

            u'http://test.com/mytest/?utm_X',
            u'http://test.com/mytest/?utm_X&',
            u'http://test.com/mytest/?utm_X=',
            u'http://test.com/mytest/?utm_X=&',
            u'http://test.com/mytest/?utm_X=toto',
            u'http://test.com/mytest/?utm_X=toto&',

            u'http://test.com/mytest/?utm_source=toto&utm_Y',
            u'http://test.com/mytest/?utm_source=toto&utm_Y&',
            u'http://test.com/mytest/?utm_source=toto&utm_Y=',
            u'http://test.com/mytest/?utm_source=toto&utm_Y=&',
            u'http://test.com/mytest/?utm_source=toto&utm_Y=titi',
            u'http://test.com/mytest/?utm_source=toto&utm_Y=titi&',

            u'http://test.com/mytest/#xtor',
            u'http://test.com/mytest/#xtor=',
            u'http://test.com/mytest/#xtor=tata',
            u'http://test.com/mytest/#xtor&',
            u'http://test.com/mytest/#xtor=&',
            u'http://test.com/mytest/#xtor=tata&',

            u'http://test.com/mytest/?utm_X#xtor',
            u'http://test.com/mytest/?utm_X#xtor=',
            u'http://test.com/mytest/?utm_X#xtor=tata',

            u'http://test.com/mytest/?utm_campaign&#xtor',
            u'http://test.com/mytest/?utm_campaign&#xtor=',
            u'http://test.com/mytest/?utm_campaign&#xtor=tata',

            u'http://test.com/mytest/?utm_X=&#xtor',
            u'http://test.com/mytest/?utm_X=&#xtor=',
            u'http://test.com/mytest/?utm_X=&#xtor=tata',

            u'http://test.com/mytest/?utm_X=toto#xtor',
            u'http://test.com/mytest/?utm_X=toto#xtor=',
            u'http://test.com/mytest/?utm_X=toto#xtor=tata',

            u'http://test.com/mytest/?utm_X=toto&#xtor',
            u'http://test.com/mytest/?utm_X=toto&#xtor=',
            u'http://test.com/mytest/?utm_X=toto&#xtor=tata',

            u'http://test.com/mytest/?utm_X=toto&utm_Y#xtor',
            u'http://test.com/mytest/?utm_X=toto&utm_Y#xtor=',
            u'http://test.com/mytest/?utm_X=toto&utm_Y#xtor=tata',

            u'http://test.com/mytest/?utm_X=toto&utm_Y=#xtor',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=#xtor=',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=#xtor=tata',

            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi#xtor',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi#xtor=',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi#xtor=tata',

            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi&#xtor',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi&#xtor=',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi&#xtor=tata',

            u'http://test.com/mytest/?xtor',
            u'http://test.com/mytest/?xtor=',
            u'http://test.com/mytest/?xtor=tata',
            u'http://test.com/mytest/?xtor=tata&',

            u'http://test.com/mytest/?utm_X&xtor',
            u'http://test.com/mytest/?utm_X&xtor=',
            u'http://test.com/mytest/?utm_X&xtor=tata',
            u'http://test.com/mytest/?utm_X&xtor=tata&',

            u'http://test.com/mytest/?utm_X=&xtor',
            u'http://test.com/mytest/?utm_X=&xtor=',
            u'http://test.com/mytest/?utm_X=&xtor=tata',
            u'http://test.com/mytest/?utm_X=&xtor=tata&',

            u'http://test.com/mytest/?utm_X=toto&xtor',
            u'http://test.com/mytest/?utm_X=toto&xtor=',
            u'http://test.com/mytest/?utm_X=toto&xtor=tata',
            u'http://test.com/mytest/?utm_X=toto&xtor=tata&',

            u'http://test.com/mytest/?utm_X=toto&utm_Y&xtor',
            u'http://test.com/mytest/?utm_X=toto&utm_Y&xtor=',
            u'http://test.com/mytest/?utm_X=toto&utm_Y&xtor=tata',
            u'http://test.com/mytest/?utm_X=toto&utm_Y&xtor=tata&',

            u'http://test.com/mytest/?utm_X=toto&utm_Y=&xtor',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=&xtor=',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=&xtor=tata',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=&xtor=tata&',

            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi&xtor',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi&xtor=',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi&xtor=tata',
                u'http://test.com/mytest/?utm_X=toto&utm_Y=titi&xtor=tata&',
        ):

            self.assertEquals(clean_marketing_url(bad_url), good_url)

    def test_utm_with_other_things(self):
        """ Test other strange UTM parameters. """

        for bad_url, good_url in (
            (u'http://www.begeek.fr/visitez-le-tardis-de-doctor-who-sur-google-maps-101125?utm_source=Plus+d‘actu&utm_medium=cpc&utm_campaign=Plus+d‘actu',  # NOQA
             u'http://www.begeek.fr/visitez-le-tardis-de-doctor-who-sur-google-maps-101125'),  # NOQA
            (u'http://techcrunch.com/2013/05/18/hell-no-tumblr-users-wont-go-to-yahoo/?utm_source=feedburner&utm_medium=feed&utm_campaign=Feed%3A+francaistechcrunch+%28TechCrunch+en+Francais%29',  # NOQA
             u'http://techcrunch.com/2013/05/18/hell-no-tumblr-users-wont-go-to-yahoo/'),  # NOQA
            (u'http://www.liberation.fr/politiques/2013/09/24/la-niche-fiscale-pour-les-parents-d-enfants-scolarises-sera-conservee_934193?=rss-450',  # NOQA
             u'http://www.liberation.fr/politiques/2013/09/24/la-niche-fiscale-pour-les-parents-d-enfants-scolarises-sera-conservee_934193'),  # NOQA

            # This one must not be changed.
            (u'http://tctechcrunch2011.files.wordpress.com/2013/09/screen-shot-2013-09-24-at-5-57-35-am.png?w=1280&h=948',  # NOQA
             u'http://tctechcrunch2011.files.wordpress.com/2013/09/screen-shot-2013-09-24-at-5-57-35-am.png?w=1280&h=948'),  # NOQA
        ):
            self.assertEquals(clean_marketing_url(bad_url), good_url)


class TestHttpUtilsCleanGoogleUrl(TestCase):

    """ Test the google URL cleaner. """

    def test_google_cleaner_very_bad_to_good(self):
        """ Test bad to good conversions, with variations in “bad”. """

        for bad_url, good_url in (

            # The same good URL, but various bad ones, just in case.

            (u'https://www.google.com/url?rct=j&url=http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727&ct=ga&cd=CAIyGTA1MzgxZDdjMmUwODAwMzg6ZnI6ZnI6RlI&usg=AFQjCNEdfJhdBh1PdKxHgzCTVV9ULCYoFg',  # NOQA
             u'http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727', ),  # NOQA

            (u'https://www.google.com/url?&sa=t&url=http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727&ct=ga&cd=CAIyGTA1MzgxZDdjMmUwODAwMzg6ZnI6ZnI6RlI&usg=AFQjCNEdfJhdBh1PdKxHgzCTVV9ULCYoFg',  # NOQA
             u'http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727', ),  # NOQA

            (u'https://www.google.com/url?sa=t&url=http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727&ct=ga&cd=CAIyGTA1MzgxZDdjMmUwODAwMzg6ZnI6ZnI6RlI&usg=AFQjCNEdfJhdBh1PdKxHgzCTVV9ULCYoFg',  # NOQA
             u'http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727', ),  # NOQA

            (u'https://www.google.com/url?rct=j&url=http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727&ct=ga&cd=CAIyGTA1MzgxZDdjMmUwODAwMzg6ZnI6ZnI6RlI',  # NOQA
             u'http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727', ),  # NOQA

            (u'https://www.google.com/url?&sa=t&url=http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727&ct=ga',  # NOQA
             u'http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727', ),  # NOQA

            (u'https://www.google.com/url?sa=t&url=http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727&',  # NOQA
             u'http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727', ),  # NOQA

            (u'https://www.google.com/url?sa=t&url=http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727&usg=AFQjCNEdfJhdBh1PdKxHgzCTVV9ULCYoFg',  # NOQA
             u'http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727', ),  # NOQA

            (u'https://www.google.com/url?sa=t&url=http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727&usg=',  # NOQA
             u'http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727', ),  # NOQA

            (u'https://www.google.com/url?sa=t&url=http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727&usg',  # NOQA
             u'http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727', ),  # NOQA

            (u'https://www.google.com/url?sa=t&url=http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727&ct=',  # NOQA
             u'http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727', ),  # NOQA
        ):

            self.assertEquals(clean_google_url(bad_url), good_url)

    def test_google_cleaner_bad_to_good(self):
        """ Test bad to good conversions. """

        for bad_url, good_url in (

            # Different good URLs, taken from real life google alert feeds.

            (u'https://www.google.com/url?rct=j&sa=t&url=http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727&ct=ga&cd=CAIyGTA1MzgxZDdjMmUwODAwMzg6ZnI6ZnI6RlI&usg=AFQjCNEdfJhdBh1PdKxHgzCTVV9ULCYoFg',  # NOQA
             u'http://www.begeek.fr/microsoft-equipe-android-wear-dune-solution-ecrire-les-montres-connectees-148727', ),  # NOQA

            (u'https://www.google.com/url?rct=j&sa=t&url=http://bfmbusiness.bfmtv.com/entreprise/l-iphone-6-fait-un-carton-en-chine-839814.html&ct=ga&cd=CAIyGTA1MzgxZDdjMmUwODAwMzg6ZnI6ZnI6RlI&usg=AFQjCNE-qcVTCLVueW-PLWxSVXuwy1HnGQ',  # NOQA
             u'http://bfmbusiness.bfmtv.com/entreprise/l-iphone-6-fait-un-carton-en-chine-839814.html', ),  # NOQA

            (u'https://www.google.com/url?rct=j&sa=t&url=http://www.reponseatout.com/reponse-conso/telephonie-internet/b-games-le-jeu-selon-bouygues-telecom-a1013749&ct=ga&cd=CAIyGTA1MzgxZDdjMmUwODAwMzg6ZnI6ZnI6RlI&usg=AFQjCNF8Z0A4jHB47l1Xhj95u2i90bqJyw',  # NOQA
             u'http://www.reponseatout.com/reponse-conso/telephonie-internet/b-games-le-jeu-selon-bouygues-telecom-a1013749', ),  # NOQA

            (u'https://www.google.com/url?rct=j&sa=t&url=http://www.clubic.com/mobilite-et-telephonie/objets-connectes/montre-connectee/actualite-732445-analog-keyboard-clavier-android-wear-microsoft-research.html&ct=ga&cd=CAIyGTA1MzgxZDdjMmUwODAwMzg6ZnI6ZnI6RlI&usg=AFQjCNEEzo2fTynX5TPTyi1YCAPgZtkMbQ',  # NOQA
             u'http://www.clubic.com/mobilite-et-telephonie/objets-connectes/montre-connectee/actualite-732445-analog-keyboard-clavier-android-wear-microsoft-research.html', ),  # NOQA

            (u'https://www.google.com/url?rct=j&sa=t&url=http://www.itespresso.fr/vol-donnees-snapchat-photos-risquent-moins-ephemeres-80092.html&ct=ga&cd=CAIyGTA1MzgxZDdjMmUwODAwMzg6ZnI6ZnI6RlI&usg=AFQjCNFmgi1QDa9hrhebnWDc2ALehLPNGA',  # NOQA
             u'http://www.itespresso.fr/vol-donnees-snapchat-photos-risquent-moins-ephemeres-80092.html', ),  # NOQA

            (u'https://www.google.com/url?rct=j&sa=t&url=http://www.01net.com/editorial/628552/google-et-motorola-s-allient-pour-un-nexus-6-de-5-9-pouces/&ct=ga&cd=CAIyGTA1MzgxZDdjMmUwODAwMzg6ZnI6ZnI6RlI&usg=AFQjCNFZZ-Z1hC9-K4e4WVdmKNe4Dnmagw',  # NOQA
             u'http://www.01net.com/editorial/628552/google-et-motorola-s-allient-pour-un-nexus-6-de-5-9-pouces/', ),  # NOQA

            (u'https://www.google.com/url?rct=j&sa=t&url=http://www.infos-mobiles.com/microsoft/microsoft-mettre-fin-gamme-surface-apres-faible-vente-surface-pro-3/80507&ct=ga&cd=CAIyGTA1MzgxZDdjMmUwODAwMzg6ZnI6ZnI6RlI&usg=AFQjCNFKdDME0tSHAbuCmCUA4uS9e17Jcw',  # NOQA
             u'http://www.infos-mobiles.com/microsoft/microsoft-mettre-fin-gamme-surface-apres-faible-vente-surface-pro-3/80507', ),  # NOQA

            (u'https://www.google.com/url?rct=j&sa=t&url=http://www.europe1.fr/faits-divers/stupefiants-un-proces-sous-haute-surveillance-2257951&ct=ga&cd=CAIyGTA1MzgxZDdjMmUwODAwMzg6ZnI6ZnI6RlI&usg=AFQjCNEGaIhvL71NADe71a6r7qPbTFS7ZA',  # NOQA
             u'http://www.europe1.fr/faits-divers/stupefiants-un-proces-sous-haute-surveillance-2257951', ),  # NOQA

        ):

            self.assertEquals(clean_google_url(bad_url), good_url)

    def test_google_cleaner_already_good(self):
        """ Test already good conversions → they should not change. """

        for bad_url, good_url in (

            (u'http://test.com/mytest/?=',
             u'http://test.com/mytest/?=', ),

            (u'http://test.com/mytest/?#',
             u'http://test.com/mytest/?#', ),

            (u'http://test.com/mytest/#?=',
             u'http://test.com/mytest/#?=', ),

            (u'http://test.com/mytest/?=rss',
             u'http://test.com/mytest/?=rss', ),

            (u'http://test.com/mytest/?=rss-450',
             u'http://test.com/mytest/?=rss-450', ),

            (u'http://test.com/mytest/?=rss-450&',
             u'http://test.com/mytest/?=rss-450&', ),

            (u'http://test.com/mytest/?=rss-450&=rss',
             u'http://test.com/mytest/?=rss-450&=rss', ),

            (u'http://test.com/mytest/?utm_source=toto&utm_Y',
             u'http://test.com/mytest/?utm_source=toto&utm_Y', ),

            (u'http://test.com/mytest/?utm_source=toto&utm_Y&',
             u'http://test.com/mytest/?utm_source=toto&utm_Y&', ),

            (u'http://test.com/mytest/?utm_source=toto&utm_Y=',
             u'http://test.com/mytest/?utm_source=toto&utm_Y=', ),

            (u'http://test.com/mytest/?utm_source=toto&utm_Y=&',
             u'http://test.com/mytest/?utm_source=toto&utm_Y=&', ),

            (u'http://test.com/mytest/?utm_source=toto&utm_Y=titi',
             u'http://test.com/mytest/?utm_source=toto&utm_Y=titi', ),

            (u'http://test.com/mytest/?utm_source=toto&utm_Y=titi&',
             u'http://test.com/mytest/?utm_source=toto&utm_Y=titi&', ),
        ):

            self.assertEquals(clean_google_url(bad_url), good_url)
