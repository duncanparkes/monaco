import re
from urlparse import urljoin

import requests
import lxml.html
import execjs
from slugify import slugify

from HTMLParser import HTMLParser
unescape = HTMLParser().unescape

source_url = 'http://www.conseil-national.mc/index.php/les-elus/les-groupes-politiques'

resp = requests.get(source_url)
root = lxml.html.fromstring(resp.text)

alire = root.get_element_by_id('alire')

data = []

for heading in alire.cssselect('h4'):
    party = heading.text_content().strip()

    for li in heading.getnext().cssselect('li'):
        member = {
            'party': party,
            'area': '',  # There are no areas here.
            'term_id': 2013,  # Let's use the year it starts as there doesn't seem to be a name.
            }
        member_a = li.find('a')

        details_url = member['details_url'] = urljoin(source_url, member_a.get('href'))

        member_resp = requests.get(details_url)
        member_root = lxml.html.fromstring(member_resp.text)

        name = member['name'] = member_root.cssselect('.itemTitle')[0].text_content().strip()
        member['id'] = slugify(name)
        mailto_script = member_root.xpath("//h4[contains(., 'Contact Mail')]")[0].getnext().getchildren()[0].text_content()

        # Get hold of the lines of javascript which aren't fiddling with the DOM
        jslines = [x.strip() for x in re.search(r'<!--(.*)//-->', mailto_script, re.M | re.S).group(1).strip().splitlines() if not x.strip().startswith('document')]

        # The name of the variable containing the variable containing the email address
        # varies, so find it by regex.
        varname = re.search(r'var (addy\d+)', mailto_script).group(1)
        jslines.append('return {}'.format(varname))

        js = '(function() {{{}}})()'.format(' '.join(jslines))
        member['email'] = unescape(execjs.eval(js))

        img = member_root.cssselect('.itemFullText')[0].cssselect('img')[0]

        member['image'] = urljoin(member['details_url'], img.get('src'))

        data.append(member)


legislatures_data = [
    {'id': 2013, 'name': '2013', 'start_date': '2013-02-21', 'end_date': 2018},
    ]


# Get some historic data too.
old_legislatures = (
    'http://www.conseil-national.mc/index.php/histoire-du-conseil-national/les-elus-de-la-legislature-2008-2013',
    'http://www.conseil-national.mc/index.php/histoire-du-conseil-national/les-elus-de-la-legislature-2003-2008',
    )

for legislature_url in old_legislatures:
    start_date, end_date = legislature_url.rsplit('-', 2)[1:]

    legislatures_data.append({
            'id': start_date,
            'start_date': start_date,
            'end_date': end_date,
            'name': '{}-{}'.format(start_date, end_date),
    })

    resp = requests.get(legislature_url)
    root = lxml.html.fromstring(resp.text)

    for tr in root.cssselect('table')[0].cssselect('tr'):
        member = {}

        member['image'] = urljoin(legislature_url, tr.cssselect('img')[0].get('src'))
        name = member['name'] = tr[1].getchildren()[0].text_content().strip()
        member['id'] = slugify(name)
        member['term_id'] = start_date

        try:
            member['party'] = tr[1][1].getchildren()[0].text_content().split(u'Membre du groupe politique ')[1]
        except:
            print repr(u"No party for {} in {}".format(member['name'], member['term_id']))

        if member.get('party') == u"UNAM (Union Nationale pour l'Avenir de Monaco), UpM (Union pour Monaco)":
            member['party'] = u"UNAM Union Nationale pour l'Avenir de Monaco UpM (Union pour Monaco)"

        if member.get('party') == u"UP Union pour la PrincipautéUpM (Union pour Monaco)":
            member['party'] = u"UP Union pour la Principauté UpM (Union pour Monaco)"


        data.append(member)


##########################################################################################
# Actually saving the data is down here to help me add and remove it repeatedly with Git #
##########################################################################################

import scraperwiki
scraperwiki.sqlite.save(unique_keys=['name', 'term_id'], data=data)
scraperwiki.sqlite.save(unique_keys=['id'], data=legislatures_data, table_name='terms')
