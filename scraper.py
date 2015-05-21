import re
from urlparse import urljoin

import requests
import lxml.html
import execjs

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
            }
        member_a = li.find('a')

        member['name'] = member_a.text.strip()
        details_url = member['details_url'] = urljoin(source_url, member_a.get('href'))

        member_resp = requests.get(details_url)
        member_root = lxml.html.fromstring(member_resp.text)

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

        # There's something which looks like a numerical ID in the details_url
        member['id'] = details_url.rsplit('/', 1)[-1].split('-', 1)[0]

        data.append(member)


##########################################################################################
# Actually saving the data is down here to help me add and remove it repeatedly with Git #
##########################################################################################

import scraperwiki
scraperwiki.sqlite.save(unique_keys=['name'], data=data)
