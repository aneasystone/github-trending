# coding:utf-8

import os
import datetime
import requests
import urllib.parse
from pyquery import PyQuery as pq

def scrape_url(url):
    ''' Scrape github trending url
    '''
    HEADERS = {
        'User-Agent'		: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:11.0) Gecko/20100101 Firefox/11.0',
        'Accept'			: 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding'	: 'gzip,deflate,sdch',
        'Accept-Language'	: 'zh-CN,zh;q=0.8'
    }

    print(url)
    r = requests.get(url, headers=HEADERS)
    assert r.status_code == 200
    
    d = pq(r.content)
    items = d('div.Box article.Box-row')

    results = {}
    # codecs to solve the problem utf-8 codec like chinese
    for item in items:
        i = pq(item)
        title = i(".lh-condensed a").text()
        description = i("p.col-9").text()
        url = i(".lh-condensed a").attr("href")
        url = "https://github.com" + url
        results[title] = { 'title': title, 'url': url, 'description': description }
    return results

def scrape_lang(language):
    ''' Scrape github trending with lang parameters
    '''
    url = 'https://github.com/trending/{language}'.format(language=urllib.parse.quote_plus(language))
    r1 = scrape_url(url)
    url = 'https://github.com/trending/{language}?spoken_language_code=zh'.format(language=urllib.parse.quote_plus(language))
    r2 = scrape_url(url)
    return { **r1, **r2 }

def write_markdown(lang, results, archived_contents):
    ''' Write the results to markdown file
    '''
    content = ''
    with open('README.md', mode='r', encoding='utf-8') as f:
        content = f.read()
    content = convert_file_contenet(content, lang, results, archived_contents)
    with open('README.md', mode='w', encoding='utf-8') as f:
        f.write(content)

def is_title_exist(title, content, archived_contents):
    if '[' + title + ']' in content:
        return True
    for archived_content in archived_contents:
        if '[' + title + ']' in archived_content:
            return True
    return False

def convert_file_contenet(content, lang, results, archived_contents):
    ''' Add distinct results to content
    '''
    distinct_results = []
    for title, result in results.items():
        if not is_title_exist(title, content, archived_contents):
            distinct_results.append(result)
    
    if not distinct_results:
        print('There is no distinct results')
        return content

    lang_title = convert_lang_title(lang)
    if lang_title not in content:
        content = content + lang_title + '\n\n'
    
    return content.replace(lang_title + '\n\n', lang_title + '\n\n' + convert_result_content(distinct_results))

def convert_result_content(results):
    ''' Format all results to a string
    '''
    strdate = datetime.datetime.now().strftime('%Y-%m-%d')
    content = ''
    for result in results:
        content = content + u"* 【{strdate}】[{title}]({url}) - {description}\n".format(
            strdate=strdate, title=result['title'], url=result['url'],
            description=format_description(result['description']))
    return content

def format_description(description):
    ''' Remove new line characters
    '''
    if not description:
        return ''
    return description.replace('\r', '').replace('\n', '')

def convert_lang_title(lang):
    ''' Lang title
    '''
    if lang == '':
        return '## All language'
    return '## ' + lang.capitalize()

def get_archived_contents():
    archived_contents = []
    archived_files = os.listdir('./archived')
    for file in archived_files:
        content = ''
        with open('./archived/' + file, mode='r', encoding='utf-8') as f:
            content = f.read()
        archived_contents.append(content)
    return archived_contents

def job():
    ''' Get archived contents
    '''
    archived_contents = get_archived_contents()

    ''' Start the scrape job
    '''
    languages = ['', 'java', 'python', 'javascript', 'go', 'c', 'c++', 'c#', 'html', 'css', 'unknown']
    for lang in languages:
        results = scrape_lang(lang)
        write_markdown(lang, results, archived_contents)

if __name__ == '__main__':
    job()