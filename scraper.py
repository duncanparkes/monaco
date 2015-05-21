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
        member = {'party': party}
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

        data.append(member)

# This is a template for a Python scraper on morph.io (https://morph.io)
# including some code snippets below that you should find helpful

# import scraperwiki
# import lxml.html
#
# # Read in a page
# html = scraperwiki.scrape("http://foo.com")
#
# # Find something on the page using css selectors
# root = lxml.html.fromstring(html)
# root.cssselect("div[align='left']")
#
# # Write out to the sqlite database using scraperwiki library
# scraperwiki.sqlite.save(unique_keys=['name'], data={"name": "susan", "occupation": "software developer"})
#
# # An arbitrary query against the database
# scraperwiki.sql.select("* from data where 'name'='peter'")

# You don't have to do things with the ScraperWiki and lxml libraries.
# You can use whatever libraries you want: https://morph.io/documentation/python
# All that matters is that your final data is written to an SQLite database
# called "data.sqlite" in the current working directory which has at least a table
# called "data".


############################

import scraperwiki
scraperwiki.sqlite.save(unique_keys=['name'], data=data)
